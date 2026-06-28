#!/usr/bin/env python3
"""Decode Yaesu FT-891 SFL firmware file to binary.

SFL format: Motorola S-records scrambled with a stream cipher.
  - Lines starting with "VS" are encoded S0 header records:
      skip "VS" prefix, prepend "S0", decode remaining chars
  - All other data lines after the first "VS" line: decode all chars
  - Stream cipher: decoded_char = (encoded_char - table[counter]) & 0xFF
  - Counter increments per decoded char, cycles through 43 entries (0..42)

Motorola S-record format (https://en.wikipedia.org/wiki/SREC_(file_format)):
  Each line is a record: S<type><count><address><data><checksum>
  - S0: header/comment (file name, version)
  - S1: 16-bit address + data
  - S2: 24-bit address + data
  - S3: 32-bit address + data
  - S7/S8/S9: end-of-file
  All fields are ASCII hex (2 chars per byte). <count> is the number of
  remaining bytes (address + data + checksum). <checksum> is the one's
  complement of the least significant byte of the sum of all bytes from
  <count> through the last data byte.
"""

import sys

# Stream cipher key table (43 bytes, indices 0-42)
DECODE_TABLE = [
    0x1e, 0x27, 0x1b, 0x12, 0x11, 0x16, 0x19, 0x17,
    0x24, 0x25, 0x29, 0x1c, 0x0d, 0x0b, 0x06, 0x04,
    0x03, 0x01, 0x02, 0x05, 0x07, 0x0c, 0x0e, 0x0f,
    0x18, 0x1d, 0x20, 0x22, 0x2a, 0x2b, 0x08, 0x09,
    0x0a, 0x10, 0x13, 0x14, 0x15, 0x1a, 0x1f, 0x21,
    0x28, 0x23, 0x26,
]
assert len(DECODE_TABLE) == 43


def decode_line(encoded_bytes, counter):
    """Decode bytes using the stream cipher, returning (decoded_str, new_counter)."""
    result = []
    for b in encoded_bytes:
        key = DECODE_TABLE[counter]
        result.append(chr((b - key) & 0xFF))
        counter = (counter + 1) % len(DECODE_TABLE)
    return ''.join(result), counter


def parse_srec_data(rec):
    """Parse a Motorola S-record, return (address, data_bytes) or None."""
    rtype = rec[1]
    count = int(rec[2:4], 16)

    if rtype == '0':
        return None  # header, skip
    elif rtype in ('7', '8', '9'):
        return 'END'
    elif rtype == '1':
        addr = int(rec[4:8], 16)
        data_len = count - 3  # subtract 2-byte addr + 1-byte cksum
        data_hex = rec[8:8 + data_len * 2]
    elif rtype == '2':
        addr = int(rec[4:10], 16)
        data_len = count - 4
        data_hex = rec[10:10 + data_len * 2]
    elif rtype == '3':
        addr = int(rec[4:12], 16)
        data_len = count - 5
        data_hex = rec[12:12 + data_len * 2]
    else:
        return None

    data = bytes(int(data_hex[i*2:i*2+2], 16) for i in range(data_len))
    return (addr, data)


def decode_sfl(sfl_path, output_path):
    with open(sfl_path, 'rb') as f:
        content = f.read()

    lines = content.split(b'\r\n')

    # Extract expected checksum from header comment
    import re
    expected = None
    for line in lines:
        m = re.search(rb'CHECK SUM\]\s+([0-9A-Fa-f]+)\(', line)
        if m:
            expected = int(m.group(1), 16)
            break

    counter = 0
    vs_seen = False
    firmware = bytearray(b'\xff' * 0x60000)  # 384KB, 0xFF = erased flash
    records = 0
    bytes_written = 0

    for raw_line in lines:
        if not raw_line or raw_line.startswith(b';'):
            continue

        if raw_line.startswith(b'VS'):
            vs_seen = True
            prefix = 'S0'
            encoded = raw_line[2:]  # skip "VS"
        elif vs_seen:
            prefix = ''
            encoded = raw_line
        else:
            continue

        decoded_tail, counter = decode_line(encoded, counter)
        decoded = prefix + decoded_tail

        result = parse_srec_data(decoded)
        if result is None:
            continue
        if result == 'END':
            break

        addr, data = result
        for i, byte in enumerate(data):
            pos = addr + i
            if 0 <= pos < len(firmware):
                firmware[pos] = byte
                bytes_written += 1
        records += 1

    # The SFL header checksum is sum(all 384KB bytes); the EXE adds 0x01FE0000
    # to display in the GUI, but the file header records the raw sum.
    fw_sum = sum(firmware) & 0xFFFFFFFF
    if expected is not None:
        status = "OK" if fw_sum == expected else "MISMATCH"
        exp_str = f"expected {expected:08X}"
    else:
        status = "no expected value in header"
        exp_str = "expected N/A"
    print(f"Records processed: {records}")
    print(f"Bytes written: {bytes_written}")
    print(f"Firmware checksum: {fw_sum:08X} ({exp_str}) [{status}]")

    with open(output_path, 'wb') as f:
        f.write(firmware)
    print(f"Firmware written to {output_path}")


if __name__ == '__main__':
    sfl = sys.argv[1] if len(sys.argv) > 1 else 'AH065_M_V0110.SFL'
    out = sys.argv[2] if len(sys.argv) > 2 else 'AH065_M_V0110.bin'
    decode_sfl(sfl, out)
