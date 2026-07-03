# FT-891 Internals

Firmware analysis notes and tools for the Yaesu FT-891 HF/50 MHz transceiver.
The radio contains three separate processors, each with its own firmware image:

| Processor | Firmware file | Role |
|-----------|--------------|------|
| Renesas H8S/2655 (main board) | `AH065_M_V0110.bin` | Radio control, CAT, display commands, DSP bridge |
| TMS320C6746 (DSP board) | `AH065_V0205.dat` (inside the SFL container) | Audio signal chain, demodulation, filters |
| Renesas H8S/2655 (panel board) | `AH065_P_V0101.bin` | Front-panel LCD, keypad/encoder, SSI bridge to main board |

Firmware images are not included; extract them from the official Yaesu update package
(`FT-891_Firmware_Update_2022_12.zip`) using `decode_sfl.py`.

---

## Files

### `decode_sfl.py`

Decodes the Yaesu SFL firmware container to raw binary.

Yaesu distributes firmware as `.SFL` files — Motorola S-records (SREC) scrambled with
a stream cipher. Lines starting with `VS` are the encoded payload; each character is
shifted by a cycling 43-byte key table. After decoding, the script parses the S1/S2/S3
records and writes a flat 384 KB binary (0xFF-padded for erased flash regions).

The script verifies the firmware checksum stored in the SFL header comment.

```
python3 decode_sfl.py AH065_M_V0110.SFL AH065_M_V0110.bin
```

The same script works for the panel firmware (`AH065_P_V0101.SFL`). The DSP firmware
(`AH065_V0205.dat`) is embedded inside the main SFL file and extracted separately as a
TI COFF1 binary by the Yaesu updater.

### `ft891_flash.py`

Linux implementation of the FT-891 PGM SW (Program Switch) firmware update protocol.

The radio must be powered with the PGM SW jumper set before running this tool.
The protocol sequence:

1. Auto-baud sync at 9600 / 4800 / 2400 baud (0x00 probe → 0x55 → expect 0xE6)
2. Model identification (`0x20` → 18 bytes; expects ASCII `"4C03"` = FT-891)
3. Readiness check (`0x27`)
4. Model echo, segment select, memory/baud config packets
5. Switch to 57600 baud
6. Flash erase (`0x40`, up to 5 s)
7. Sector write + page finalise + status polls
8. Firmware transfer: 384 KB in 128-byte blocks, each ACK'd with `0x06`
9. Completion poll

**Requires**: `pyserial` (`pip install pyserial`)

**Warning**: Experimental — has not been tested against real hardware. Keep a
known-good firmware backup available before flashing.

```
python3 ft891_flash.py /dev/ttyUSB0 AH065_M_V0110.bin
```

### `CAT_codes.md`

Full reference table for all 121 CAT commands in the FT-891 firmware dispatch table.

Each entry records: command index, whether it appears in the official CAT reference manual, firmware
status (active or dead stub), Set/Read/Auto-Information flags, the actual wire format as confirmed by
disassembly, and notes on internal implementation.

Key findings documented here that are not in the official manual:
- 7 active undocumented commands (PE, SP, VE, JP, ZZ, E0, E8) with full format descriptions
- 25 dead stubs (registered in the dispatch table but always return error)
- Hidden extended forms: `MT P1[38];` (combined channel-write-with-name, undocumented) and
  `ID 0891;` (returns firmware version instead of model code)
- Format discrepancies: IS uses 7-param wire format vs PDF's 4; several commands have a mandatory
  leading `'0'` VFO-selector byte omitted from PDF parameter counts (BC, CN, IS)
- EX menu internal structure (18 sections, 159 parameters, ROM tables at 0x100DA/0x100EC)
- FA uses 9-digit frequency format (not 11 as the PDF states)

### `MAIN_FIRMWARE_ANALYSIS.md`

Firmware analysis of the main board H8S/2655 firmware (`AH065_M_V0110.bin`).

Covers the full 384 KB image: memory map, cold-reset boot sequence (all 9 init calls
identified), 16-task cooperative scheduler, interrupt vector table (26 active vectors
including SSI0 panel comms and SSI1 CW/RTTY decoder), CAT interface (122 commands),
RF/VCO/audio subsystems, calibration table, and the `computed_goto` dispatcher at
`0x2A6AA` (called 143 times — a Codewarrior inline jump-table pattern that Ghidra
cannot decompile directly).

Toolchain: `h8300-linux-gnu-objdump`, Ghidra 12.1.2 with a patched H8S SLEIGH spec
(`carllom/sleigh-h8` + local extensions for 32-bit absolute BSET/BCLR/BTST and `#2`
shift-count variants).

### `DSP_FIRMWARE_ANALYSIS.md`

Firmware analysis of the TMS320C6746 DSP firmware.

The DSP runs a single continuous audio processing loop (~15 KB of C674x VLIW code per
audio frame) with a 24-entry mode dispatch table selecting the demodulation path. Three
clusters: SSB/CW/AM demodulation (Cluster 1), FM/RTTY/Data modes via A8-register
runtime dispatch (Cluster 2), and FFT/spectral processing (Cluster 3). Includes FIR
filter bank (Section 5), IIR filters (Sections 6–7), FFT twiddle factors, and the
host↔DSP communication protocol (mode index written to `0x1182DB8C` in shared EMIF
SRAM).

Toolchain: TI `dis6x v7.3.4` from `github.com/superna9999/ti-cgt6x`. Ghidra and
radare2 have no C6000/C674x support; capstone's `CS_ARCH_TMS320C64X` stalls on C674x
FP instructions.

### `PANEL_FIRMWARE_ANALYSIS.md`

Firmware analysis of the panel board H8S/2655 firmware (`AH065_P_V0101.bin`).

The panel firmware is radically simpler than main (~145 functions vs 1254). It runs a
3-task superloop: display renderer, SSI RX handler (main→panel packets), and SSI TX
handler (key/encoder events panel→main). The LCD pipeline goes from SSI receive buffer
through a display descriptor dispatch to a 5-path font renderer (5-column × 6-bit
glyphs). Inter-board protocol: full-duplex SSI, main board is master; command bytes
`0xE0`/`0xE1` are display updates, `0xF0` is ACK request, `0x06` and `0x15` are key
and encoder events from the panel. Includes complete memory map, all 6 active interrupt
vectors, and identified utility functions (memcpy, bargraph renderer, icon-width
decoder).

Same toolchain as the main board; note that `jump_table_dispatch()` at `0x8E00`
triggers a Ghidra assertion error — define the function manually before running
auto-analysis.

---

## Hardware context

The FT-891 is a 100 W HF/50 MHz SDR-based transceiver. Main ↔ DSP communication uses
EMIF shared SRAM on the C6746. Main ↔ panel communication uses a full-duplex SSI bus
with the main board as clock master. The panel board enters H8S SLEEP mode when idle
and wakes on a keypad interrupt (Vec 64).
