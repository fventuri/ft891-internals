#!/usr/bin/env python3
"""
Yaesu FT-891 firmware writer — Linux, PGM SW mode.

Usage:
    python3 ft891_flash.py /dev/ttyUSB0 AH065_M_V0110.bin

Requirements:
    pip install pyserial

WARNING: Experimental. Not tested against real hardware.
         Use at your own risk and keep a known-good firmware backup available.
"""

import sys
import time
import argparse
import serial

FIRMWARE_SIZE  = 0x60000   # 384 KB
BLOCK_SIZE     = 128       # bytes per data block
BAUD_INITIAL   = [9600, 4800, 2400]
BAUD_PROGRAM   = 57600

# Expected model ID bytes in response to 0x20 (ASCII "4C03" = FT-891)
MODEL_ID = bytes([0x34, 0x43, 0x30, 0x33])

# Step 3: 7-byte model-echo packet  [cmd] [len] ["4C03"] [cksum]
PACKET_ECHO_MODEL   = bytes([0x10, 0x04, 0x34, 0x43, 0x30, 0x33, 0x12])

# Step 4: 4-byte segment-select packet  [cmd] [0x01] [0x00] [cksum]
PACKET_SEGMENT_SEL  = bytes([0x11, 0x01, 0x00, 0xEE])

# Step 5: 10-byte memory/baud config (PGM SW mode)
PACKET_CONFIG       = bytes([0x3F, 0x07, 0x02, 0x40, 0x04, 0x56, 0x02, 0x04, 0x02, 0x16])


# ---------------------------------------------------------------------------
# Low-level serial helpers
# ---------------------------------------------------------------------------

def send(port, data):
    if isinstance(data, int):
        data = bytes([data])
    port.write(data)
    port.flush()


def recv(port, n, timeout_ms):
    """Read exactly n bytes within timeout_ms. Returns bytes or None on timeout."""
    port.timeout = timeout_ms / 1000.0
    data = port.read(n)
    return data if len(data) == n else None


def expect_ack(port, context, timeout_ms=500):
    resp = recv(port, 1, timeout_ms)
    if not resp:
        raise RuntimeError(f"{context}: timeout waiting for ACK")
    if resp[0] != 0x06:
        raise RuntimeError(f"{context}: expected 0x06, got 0x{resp[0]:02X}")


# ---------------------------------------------------------------------------
# Protocol steps
# ---------------------------------------------------------------------------

def step0_autobaud(port_name):
    """Try 9600/4800/2400 baud. Send 0x00 probes, then 0x55; expect 0xE6."""
    for baud in BAUD_INITIAL:
        print(f"  Trying {baud} baud ... ", end='', flush=True)
        port = serial.Serial(port_name, baud, timeout=0.02)
        port.reset_input_buffer()

        got = False
        for _ in range(20):
            send(port, 0x00)
            time.sleep(0.001)
            if port.in_waiting:
                port.reset_input_buffer()
                got = True
                break
            # also collect anything that dribbles in after 20 ms
            time.sleep(0.019)
            if port.in_waiting:
                port.reset_input_buffer()
                got = True
                break

        if not got:
            print("no response")
            port.close()
            continue

        time.sleep(0.100)
        send(port, 0x55)
        resp = recv(port, 1, 1000)
        if resp and resp[0] == 0xE6:
            print("OK (0xE6)")
            return port

        got = f"0x{resp[0]:02X}" if resp else "timeout"
        print(f"unexpected: {got}")
        port.close()

    raise RuntimeError("Auto-baud sync failed at all baud rates")


def step1_model_id(port):
    """0x20 → 18 bytes; first 4 must be '4C03'."""
    time.sleep(0.010)
    send(port, 0x20)
    time.sleep(0.002)
    resp = recv(port, 18, 500)
    if not resp:
        raise RuntimeError("Model ID query: timeout")
    if resp[0:4] != MODEL_ID:
        raise RuntimeError(
            f"Model ID mismatch: got {resp[0:4].hex()} expected {MODEL_ID.hex()}"
        )
    print(f"  Model: {''.join(chr(b) for b in resp[0:4])}  (FT-891 confirmed)")


def step2_readiness(port):
    """0x27 → 5 bytes; byte[2]=0x00, byte[3]=0x80."""
    time.sleep(0.010)
    send(port, 0x27)
    time.sleep(0.002)
    resp = recv(port, 5, 500)
    if not resp:
        raise RuntimeError("Readiness query: timeout")
    if resp[2] != 0x00 or resp[3] != 0x80:
        raise RuntimeError(f"Readiness check failed: {resp.hex()}")
    print("  Ready")


def step3_echo_model(port):
    """Send 7-byte model-echo packet; expect 0x06."""
    time.sleep(0.010)
    send(port, PACKET_ECHO_MODEL)
    time.sleep(0.002)
    expect_ack(port, "Echo model")
    print("  ACK")


def step4_segment_select(port):
    """Send 4-byte segment-select packet; expect 0x06."""
    time.sleep(0.010)
    send(port, PACKET_SEGMENT_SEL)
    time.sleep(0.002)
    expect_ack(port, "Segment select")
    print("  ACK")


def step5_config(port):
    """Send 10-byte config packet; expect 0x06."""
    time.sleep(0.010)
    send(port, PACKET_CONFIG)
    time.sleep(0.002)
    expect_ack(port, "Config")
    print("  ACK")


def step6_baud_switch(port, port_name):
    """Close, reopen at 57600, send 0x06, expect 0x06 echo."""
    port.close()
    time.sleep(0.050)
    port = serial.Serial(port_name, BAUD_PROGRAM, timeout=0.5)
    time.sleep(0.050)
    send(port, 0x06)
    time.sleep(0.002)
    expect_ack(port, "Baud-rate echo")
    print(f"  Now at {BAUD_PROGRAM} baud")
    return port


def step7_erase(port):
    """0x40 → 0x06; allow up to 5 s for flash erase."""
    print("  Erasing flash (up to 5 s) ... ", end='', flush=True)
    send(port, 0x40)
    time.sleep(0.002)
    expect_ack(port, "Erase trigger", timeout_ms=5000)
    print("OK")


def step_poll_status(port, label):
    """0x4F → 5 bytes; byte[3] must be 0x00 (write status OK)."""
    time.sleep(0.010)
    send(port, 0x4F)
    time.sleep(0.002)
    resp = recv(port, 5, 500)
    if not resp:
        raise RuntimeError(f"Status poll {label}: timeout")
    if resp[3] != 0x00:
        raise RuntimeError(f"Status poll {label}: error code 0x{resp[3]:02X}")
    print(f"  OK ({resp.hex()})")


def step_sector_write(port):
    """0x4C → 0x06 (or 0xCC + redirect byte)."""
    time.sleep(0.010)
    send(port, 0x4C)
    time.sleep(0.002)
    resp = recv(port, 1, 500)
    if not resp:
        raise RuntimeError("Sector write: timeout")
    if resp[0] == 0xCC:
        sub = recv(port, 1, 100)
        sub_str = f"{sub[0]:02X}" if sub else "??"
        raise RuntimeError(f"Sector write: redirect 0xCC n=0x{sub_str}")
    if resp[0] != 0x06:
        raise RuntimeError(f"Sector write: unexpected 0x{resp[0]:02X}")
    print("  ACK")


def step_page_finalise(port):
    """0x4D → 0x06 (or 0xCD + redirect byte)."""
    time.sleep(0.010)
    send(port, 0x4D)
    time.sleep(0.002)
    resp = recv(port, 1, 500)
    if not resp:
        raise RuntimeError("Page finalise: timeout")
    if resp[0] == 0xCD:
        sub = recv(port, 1, 100)
        sub_str = f"{sub[0]:02X}" if sub else "??"
        raise RuntimeError(f"Page finalise: redirect 0xCD n=0x{sub_str}")
    if resp[0] != 0x06:
        raise RuntimeError(f"Page finalise: unexpected 0x{resp[0]:02X}")
    print("  ACK")


def step_write_confirm(port):
    """0x43 → 0x06."""
    time.sleep(0.010)
    send(port, 0x43)
    time.sleep(0.002)
    expect_ack(port, "Write confirm")
    print("  ACK")


def step_transfer(port, firmware):
    """Send firmware in 128-byte blocks + 0x50 terminator; expect 0x06 per block."""
    total = len(firmware) // BLOCK_SIZE
    print(f"  Sending {total} × {BLOCK_SIZE} B blocks:", flush=True)
    for i in range(total):
        block = firmware[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE]
        send(port, block)
        send(port, 0x50)       # block terminator / ACK request ('P')
        resp = recv(port, 1, 5000)
        if not resp or resp[0] != 0x06:
            got = f"0x{resp[0]:02X}" if resp else "timeout"
            raise RuntimeError(f"Block {i+1}/{total}: no ACK ({got})")
        if (i + 1) % 256 == 0 or i == total - 1:
            pct = (i + 1) * 100 // total
            print(f"    {pct:3d}%  addr 0x{(i+1)*BLOCK_SIZE:05X}", flush=True)


def step_completion(port):
    """0x4B → 7 bytes containing the final write address."""
    time.sleep(0.010)
    send(port, 0x4B)
    time.sleep(0.002)
    resp = recv(port, 7, 500)
    if not resp:
        raise RuntimeError("Completion poll: timeout")
    addr = int.from_bytes(resp[2:6], 'big')
    print(f"  Radio reports write address: 0x{addr:08X}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def write_firmware(port_name, firmware_path):
    with open(firmware_path, 'rb') as f:
        firmware = f.read()
    if len(firmware) != FIRMWARE_SIZE:
        raise ValueError(
            f"Expected {FIRMWARE_SIZE} bytes ({FIRMWARE_SIZE//1024} KB), "
            f"got {len(firmware)}"
        )

    print(f"FT-891 firmware writer  —  PGM SW mode")
    print(f"Port: {port_name}   Firmware: {firmware_path}  ({len(firmware)//1024} KB)")
    print()

    port = None
    try:
        print("Step 0: Auto-baud sync")
        port = step0_autobaud(port_name)

        print("Step 1: Model identification")
        step1_model_id(port)

        print("Step 2: Readiness query")
        step2_readiness(port)

        print("Step 3: Echo model code")
        step3_echo_model(port)

        print("Step 4: Segment select")
        step4_segment_select(port)

        print("Step 5: Memory/baud config")
        step5_config(port)

        print("Step 6: Switch to 57600 baud")
        port = step6_baud_switch(port, port_name)

        print("Step 7: Trigger flash erase")
        step7_erase(port)

        print("Step 8a: Status poll #1")
        step_poll_status(port, "#1")

        print("Step 8b: Status poll #2")
        step_poll_status(port, "#2")

        print("Step 9: Sector write command")
        step_sector_write(port)

        print("Step 10: Page finalise")
        step_page_finalise(port)

        print("Step 8c: Status poll #3")
        step_poll_status(port, "#3")

        print("Step 11: Write confirmation")
        step_write_confirm(port)

        print("Step 12: Firmware data transfer")
        step_transfer(port, firmware)
        print("  Transfer complete")

        print("Step 13: Completion poll")
        step_completion(port)

        print()
        print("=" * 50)
        print("Firmware written successfully.")
        print()
        print("Next steps:")
        print("  1. Disconnect the DC cable.")
        print("  2. Turn PGM SW off.")
        print("  3. Disconnect the USB cable from the radio.")

    except (RuntimeError, ValueError, serial.SerialException) as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if port and port.is_open:
            port.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Write FT-891 firmware via serial (PGM SW mode)',
        epilog='Decode SFL file first with decode_sfl.py'
    )
    parser.add_argument('port',     help='Serial port, e.g. /dev/ttyUSB0')
    parser.add_argument('firmware', help='Decoded firmware binary (.bin)')
    args = parser.parse_args()
    write_firmware(args.port, args.firmware)
