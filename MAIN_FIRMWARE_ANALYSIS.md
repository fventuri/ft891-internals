# FT-891 Firmware Analysis — AH065_M_V0110.bin

## Overview — Renesas H8S/2655 (R5F61653RN50FPV)

- **Architecture**: H8S/2600 series, 24-bit address space, **big-endian**, CISC-like with 16/32-bit instructions
- **Clock**: Unknown externally, but DMA init suggests ~10–20 MHz
- **Flash**: 384 KB at 0x000000–0x05FFFF (file offset = address directly)
- **Internal RAM**: ~32 KB at approx 0xFFB000–0xFFFFFF (stack initialized to 0xFFC000)
- **SFRs**: 0xFF2000–0xFF20FF (GPIO/SCI) and 0xFFFD00–0xFFFFFF (DMA, WDT, SYSCR)

---

## Memory Map

```
Address Range      Size    Content
─────────────────────────────────────────────────────────────────────
0x000000–0x0003FF  1 KB    Exception vector table (256 × 4-byte entries)
0x000400–0x000403  4 B     Default IRQ stub: BRA → 0x7C8 (soft reset on unhandled IRQ)
0x000404–0x0010CE  ~3 KB   FIRMWARE UPDATE / FACTORY BOOT MODE handler
0x0005F8–0x0007BD  ~500 B  Boot mode 2 (alternate hardware init path, joins main init)
0x0007BE–0x0007C7  10 B    CMIB1 handler: watchdog kick (writes 0xA500 to WDTCNT)
0x0007C8–0x001565  ~3.4 KB COLD START / Hardware initialization sequence
0x0015B6–0x0015F6  64 B    MAIN LOOP — 16-task round-robin scheduler
0x0015F7–0x05BFFF  ~376 KB Application code (tasks, subsystems, ISRs)
0x05C000–0x05FFFF  16 KB   Erased (0xFF fill)
```

---

## Boot Sequence (Cold Reset — vector 0 → 0x7C8)

```
0x7C8   ER7 (SP) ← 0x00FFC000          ; stack at top of internal RAM
0x7CE   CCR ← 0x80 (I=1)              ; disable all interrupts
0x7D0   EXR ← 0x7 (mask all ext IRQ)
0x7D4   VBR ← 0x000000                 ; vector table at flash base
0x7DC   SBR ← 0xFFFFFF00               ; SFR base address
0x7E4   DMA control init:
          WDTCNT/DMA @ 0xFFFDC2 ← 0xD102
          0xFFFF32 ← 0x20
          0xFFFDC4 ← 0x0010
          0xFFFDC6 ← 0xC8
0x808   GPIO PORT2000: clear bits 7,4,3,2  (output/enable lines)
0x828   JSR 0x09E4                      ; clock/PLL init (SYSCR, bus config)
0x82C   GPIO PORT2000: clear bits 5,6
0x834   JSR 0x0B86                      ; peripheral init (SCI, Timer, ADC)
0x840   EXR ← 0 (unmask interrupts)
0x844   BTST bit2, @0xFFFF40            ; check boot-mode flag (EEPROM/config)
        BEQ → 0x10DC (alternative boot path)
0x850   BTST bit7, @0xFF2000            ; check hardware mode pin
        BNE → 0x860
0x85A   JSR 0x0928                      ; startup path A (normal power-up)
0x860   JSR 0x096C                      ; startup path B (power-up from standby?)
...
0x894   JSR 0x2834E                     ; PLL/VCO init subsystem 1
0x898   JSR 0x28366                     ; PLL/VCO init subsystem 2
0x89C   JSR 0x28416                     ; RF frontend init
0x8A0   JSR 0x284E8                     ; RF frontend init 2
0x8A4   JSR 0x27F3E                     ; GPIO/SCI init: set port 0xFFFF59 bits 3,4; bit-bang 3×0x00 to PA/band-decoder IC via 0x292EE
0x8B0   JSR 0x2B1CE                     ; audio codec / DSP chain init
0x8B4   JSR 0x2B05C                     ; audio path init
0x8B8   JSR 0x2AB68                     ; audio output init
0x8C4   JSR 0x01366                     ; display system init
0x8D0   JSR 0x2C7A6                     ; SPI encoder interface init (clears counters)
0x8F4   JSR 0x2F058                     ; SCI4 enable: set MPBT (bit 0) of SSR4 @ 0xFFFBA4
0x8F8   JSR 0x03656                     ; scan limit init: load saved scan-edge freq pair from channels 0x62-0x74 → 0xFF2366/236A (min/max)
0x8FC   JSR 0x1F158                     ; CTCSS/tone init: read saved tone params via 0x1F1FE; set 0xFF2D3B/3C/3F/48 = 0xFF (no tone active)
0x900   JSR 0x2D6F6                     ; CAT / serial interface init
0x904   JSR 0x1D9EE                     ; VFO / frequency synthesis init
0x908   JSR 0x26484                     ; key/encoder scan (first call)
0x90C   JSR 0x2A62C                     ; state snapshot: copy 0xFF23A2→0xFF8A46 (VFO freq backup); set 0xFF204D bit 5
0x910   JSR 0x17C54                     ; display buffer init: build 3 display line bufs at 0xFF2070/20CA/2124; → 0x26952 (no return here — continues init chain)
0x914   JSR 0x2C7A6                     ; SPI encoder reset (second call)
0x918   JSR 0x2C8D2                     ; mode restore: call 0x29776; test 0xFF2011.7; dispatch to 0x2D3FE/0x3EEA; restore mode via 0xFF2073 bits 4-5 → jump table 0x2A6AA
0x91C   JSR 0x060C2                     ; NB level init: load 0xFF8E2F (saved NB level) → 0xFF8E35 (clamped 0-based); pack into 0xFF8CE5 upper nibble
0x920   JSR 0x2AFD8                     ; DSP/NR init: read 0xFF8D8A lower nibble (0-15 = DSP mode); index table @ 0x2B02C → 0xFF23EE; clear 0xFF2025 bits 6,7
0x924   JMP 0x015B6                     ; → ENTER MAIN LOOP
```

---

## Main Loop — Cooperative Scheduler (0x15B6–0x15F6)

A simple round-robin superloop — no RTOS, no preemption. All tasks share the CPU.

```asm
15B6:   JSR  task_squelch_power   @ 0x00FC2    ; power/squelch state machine
15BA:   JSR  task_audio_dsp       @ 0x2A86C    ; audio / DSP control
15BE:   JSR  task_rx_process      @ 0x1EF38    ; RX signal processing
15C2:   JSR  task_meter           @ 0x2E64E    ; S/power/SWR meter updates
15C6:   JSR  task_key_encoder     @ 0x26484    ; front panel keys + VFO encoder
15CA:   JSR  task_panel_comm       @ 0x295E0    ; front panel serial/SCI handler
15CE:   JSR  task_state_dispatch   @ 0x2A0B2    ; periodic dispatch via jump table (0xFF8A57 index)
15D2:   JSR  task_encoder_rate     @ 0x21F64    ; VFO tuning rate / CW keyer timing (0xFF23C6 encoder, mod-50)
15D6:   JSR  task_cw_rtty_dispatch @ 0x2D7DC    ; conditional dispatch via 0xFF8944 index
15DA:   JSR  task_vfo             @ 0x1DF40    ; VFO / frequency display update
15DE:   JSR  task_key_debounce     @ 0x29AFC    ; key/button debounce + repeat timer (state machine)
15E2:   JSR  task_action_dispatch  @ 0x29B86    ; conditional action dispatch via 0xFF2406 index
15E6:   JSR  task_display         @ 0x0B51E    ; LCD / display refresh
15EA:   JSR  task_memory          @ 0x0CE82    ; memory / settings management
15EE:   JSR  task_mode_change      @ 0x2935A    ; mode/band change completion: clear flags, reset state
15F2:   JSR  task_freq_tx_update   @ 0x17BBA    ; frequency/TX state update (0x273b constant)
15F6:   BRA  0x15B6               ; loop forever
```

---

## Interrupt Service Routines

| Vec | Handler   | Function |
|-----|-----------|----------|
| 0   | 0x0007C8  | **COLD RESET** — full hardware initialization |
| *default* | 0x000400 | 4-byte stub: `BRA 0x7C8` — unhandled IRQ = soft reset |
| 66  | 0x001102  | **TCI4V** (Timer 4 Overflow) — checks boot flag, calls display/audio inits, then does CPU re-init (suspected: display sync or audio frame interrupt that also serves as watchdog fallback) |
| 67  | 0x0005F8  | **TCI4U** (Timer 4 Underflow) — alternate boot path 2; sets PORT2000.7 HIGH, calls 0xB34, loops 25× calling 0xA2C (PLL lock wait?), then joins cold-start at 0x828 |
| 73  | 0x000404  | **CMI0B** (8-bit timer compare B) — **FIRMWARE UPDATE / FACTORY MODE** handler (see below) |
| 81  | 0x0007BE  | **CMIB1** — watchdog kick: writes 0xA500 to WDTCNT @ 0xFFFFA4 |
| 88  | 0x002C77C | **IRQ_88** — encoder/SPI IRQ: increments two counters at 0xFF23C4/0xFF23CB, clears 0xFFFFC5.0 |
| 101 | 0x001E58C | **RXI2** (SCI2 receive) — reads byte, applies scaling (multiply/divide by 0x2D=45), runs through lookup table @ 0x1E6D0; likely **S-meter ADC** or panel-to-main data |
| 106 | 0x002C97C | **TXI3** (SCI3 transmit) — checks two status flags, calls 0x2CA18 or 0x2C9DC; **CAT command TX** response path |
| 152–154 | 0x202B2/FC/31E | **LCD controller SPI** — 4-state sequencer: reads from table @0xFF2E86, writes to SCI data reg @0xFFFF63, manages busy flag @0xFFFF64 |
| 160–162 | 0x1DAA2/AC8/EEC | **Front panel communication** — reads data byte from 0xFFFE95, clears 0xFFFE94 status bits; likely SSI/SPI to front panel DSP or display controller |
| 220 | 0x02605A | **SSI0 RX** — receives panel command byte from SFR 0xFFF605; dispatches on: 0x06=key press, 0x15=encoder data, 0xF0=ACK, 0xE0=display update, 0xE1=update+ACK; multi-state FSM via `computed_goto(0xFF2491)` |
| 221 | 0x02629C | **SSI0 TX** — transmits display commands to panel; drains buffer @ 0xFF2482 (head: 0xFF2488, tail: 0xFF2486) to SFR 0xFFF603; clears 0xFFF604.7 (TDE); on empty: signals TX done in 0xFF202F |
| 222 | 0x026038 | **SSI0 ERROR** — clears error flags (bits 3,4,5) of SSI0 status reg @ 0xFFF604 |
| 224 | 0x02E458 | **SSI1 RX** — receives data from sub-system (CW/RTTY decoder?) via SFR 0xFFF615; byte range 0xA0–0xB4 (21 values); circular buffer @ 0xFF894D (idx: 0xFF894C, timer: 0xFF894B=100); dispatches via function table @ 0x2E4EA |
| 225 | 0x02E5F6 | **SSI1 TX** — drains buffer @ 0xFF8948 (head: 0xFF8946, tail: 0xFF8947) to SFR 0xFFF613 |
| 226 | 0x02E42A | **SSI1 ERROR** — clears error flags (bits 3,4,5) of SSI1 status reg @ 0xFFF614; calls 0x2E3F2; sets 0xFF2027.3 |

### Watchdog Architecture

Two cooperating mechanisms:
- **CMIB1 (vec 81) @ 0x7BE**: Fires periodically on Compare Match B1; writes 0xA500 to WDTCNT — standard H8S watchdog kick
- **0x2C888 (kick_watchdog fn)**: Writes 0x5A00 to WDTCNT — used in blocking loops (firmware update protocol) to prevent WDT reset during long operations

---

## Firmware Update / Factory Boot Mode (0x404)

Triggered by CMI0B (vec 73). This is NOT a normal timer ISR — it's an entire alternate operating mode for the transceiver.

**Entry preamble** (identical structure to cold reset):
- Reinitializes SP, CCR, EXR, VBR, SBR, DMA
- Sets PORT2000 bits differently from normal boot (bits 7 and 2 HIGH vs. all low)
- Calls 0xB34 (abbreviated hardware init)
- Calls 0x1D9D2 (VFO/freq init subset)
- Sets EXR = 6 (enables interrupt priority ≤ 6)

**Protocol parser** (ASCII state machine, 0x492–0x5F4):

Implements a simple 3-state serial command parser:
```
State 0: if 'P' → State 1 ; else reset
State 1: if 'S' → State 2 ; else reset  
State 2: if ';' → execute "PS;" query
         if '1' → State 3
State 3: if ';' → execute "PS1;" command (power on)
```

Response to `PS;` query: transmits `PS0;` byte-by-byte through SPI/serial at 0xFFFE93/94

**Counters**:
- Outer loop (R1): counts to 0xBB8 = 3000 → 3-second timeout
- Inner loop (R2): counts to 0x1F4 = 500 → 500ms inner timeout

This is the **CAT-like ASCII protocol** used for firmware programming via a PC tool. The protocol extends to at least `PS0;`/`PS1;` (power status), with the full update data being sent via the SPI interface checked at 0xFFFFC5.

---

## Key Subsystems

### CAT Interface (Computer Aided Transceiver)

**Command table** @ 0x19598: 121 two-letter command codes, packed as a single string:
```
AB AC AG AI AM AN BA BC BD BG BI BM BP BS BU BY CF CH CN CO CS CT
DA DN DP DS DT ED EK EM EN EU EX FA FB FI FK FO FR FS FT GT HR HW
ID IF IS KC KM KP KR KS KY LK LM MA MB MC MD MG MK ML MR MS MT MW
MX NA NB NL NR OI OS PA PB PC PE PL PR PS QI QR QS RA RC RD RF RG
RI RL RM RO RS RT RU SC SD SF SH SM SQ ST SV TS TX UL UP VD VF VG
VM VS VX XT ZI SP VE JP ZZ E0 E8
```
*(Note: the original analysis had "HI" at position 43 — the binary has **HW**; and **ID** at position 44 was previously recorded as missing but is present.)*

**Dispatch mechanism**: The CAT handler at 0x192A0 scans the command string to find the matching 2-char code, saves the index to R0L, then calls the `computed_goto` dispatcher:
```
193AE:  JSR @0x2A6AA      ; computed_goto
193B2:  .word 0x0078      ; N = 120 (indices 0–120, i.e. 121 handlers)
193B4:  .long 0x19902     ; handler[0]  = AB
193B8:  .long 0x1990E     ; handler[1]  = AC
        ...
19594:  .long 0x1D912     ; handler[120] = E8
```
Full 121-entry pointer table: **0x193B4–0x19597** (484 bytes, 4 bytes per entry).  
*(The range 0x19540–0x19597 that the earlier analysis called the "dispatch table" is actually handlers 99–120 = SM through E8, the tail of this inline table.)*

Selected handler addresses:
```
[  0] AB → 0x19902    [ 33] FA → 0x1A5FE    [ 67] NA → 0x1BAA4
[ 44] ID → 0x1A8A2    [ 58] MD → 0x1B228    [ 99] SM → 0x1CDB6
[ 99] SM → 0x1CDB6    [100] SQ → 0x1CE02    [113] XT → 0x1D204
[115] SP → 0x1D214    [116] VE → 0x1D642    [117] JP → 0x19728
[118] ZZ → 0x1968A    [119] E0 → 0x1D830    [120] E8 → 0x1D912
```

**TX path**: TXI3 ISR (vec 106 @ 0x2C97C) with dual-buffer state machine  
**RX path**: Likely SCI3 receive (not explicitly in vector table → may poll in main loop)

**CAT baud rates** (from menu strings): 4800 / 9600 / 19200 / 38400 bps

**Firmware version string** @ 0x2F11A: `V01-102021-09-27-01`  
(format: `V<major>-<minor><date YYYY-MM-DD>-<rev>`)  
Read by the undocumented VE and extended-ID commands.

#### Undocumented CAT Commands

Of the 121 command handlers, 32 are not in the official CAT reference manual: 7 are active (PE, SP, VE, JP, ZZ, E0, E8) and 25 are dead stubs.

**Dead stubs** — handler is a single `BRA 0x19358` (error/no-match exit), confirmed in binary:

| Cmd | Index | Handler | Cmd | Index | Handler |
|-----|-------|---------|-----|-------|---------|
| AN  |   5   | 0x19AB2 | MB  |  56   | 0x1B024 |
| BG  |   9   | 0x19B52 | MK  |  60   | 0x1B4D0 |
| BM  |  11   | 0x19BFA | RF  |  86   | 0x1C686 |
| DP  |  24   | 0x1A49A | RO  |  91   | 0x1C8C2 |
| DS  |  25   | 0x1A49E | RT  |  93   | 0x1C8EE |
| DT  |  26   | 0x1A4A2 | SF  |  97   | 0x1CAC8 |
| EM  |  29   | 0x1A53E | VF  | 108   | 0x1D0C8 |
| EN  |  30   | 0x1A542 | VS  | 111   | 0x1D19C |
| FI  |  35   | 0x1A770 | XT  | 113   | 0x1D204 |
| FK  |  36   | 0x1A774 |     |       |         |
| FO  |  37   | 0x1A778 |     |       |         |
| FR  |  38   | 0x1A77C |     |       |         |
| FT  |  40   | 0x1A7D8 |     |       |         |
| HR  |  42   | 0x1A89A |     |       |         |
| HW  |  43   | 0x1A89E |     |       |         |
| KC  |  47   | 0x1AC1C |     |       |         |

**Active undocumented commands:**

**`PE` (index 76, handler 0x1BF1E, 1178 bytes) — Parametric EQ band coefficient access**  
Format — Read:  `PE <CA><CB><CC>;` (3 param bytes)  
Format — Write: `PE <CA><CB><CC><D4><D5><D6>;` (6 param bytes)  
Read answer:    `PE <CA><CB><CC><sign><v1><v2>;` (9 bytes total; sign = `'0'`/`'+'`/`'-'`)

Address fields:
- **CA** (`'0'` or `'2'`): EQ channel — selects between two coefficient banks (likely TX EQ vs. P-EQ Mic)
- **CB** (`'0'`/`'1'`/`'2'`): EQ band (band 1 / 2 / 3)
- **CC** (`'0'`/`'1'`/`'2'`): parameter type within band:
  - `'0'` = center frequency index (unsigned; band-1: 0–7, band-2: 0–9, band-3: 0–18 — option counts match EX menus 1501/1504/1507 and 1510/1513/1516)
  - `'1'` = level/gain (signed byte, −20 to +10 dB — matches EX menus 1502/1505/1508 and 1511/1514/1517)
  - `'2'` = bandwidth/Q factor (unsigned, 1–10 — matches EX menus 1503/1506/1509 and 1512/1515/1518)

Frequency (CC=`'0'`) and bandwidth (CC=`'2'`) for the same band share one byte — freq in the lower nibble, bwth in the upper nibble. Level (CC=`'1'`) is a separate signed byte.

RAM coefficient table (CA=`'0'` bank; CA=`'2'` bank is +8 bytes offset):

| Band (CB) | Freq / Bwth byte | Level byte |
|-----------|-----------------|------------|
| 0 (band 1) | 0xFF8DB3 | 0xFF8DB8 |
| 1 (band 2) | 0xFF8DB4 | 0xFF8DB9 |
| 2 (band 3) | freq: 0xFF8DC3 (lower 5 bits), bwth: 0xFF8DB5 (upper nibble) | 0xFF8DBA |

Write path calls `jsr @0x37E2` (SPI driver, same as SP) immediately after updating RAM, pushing the coefficient to hardware. SPI index constants 0x233–0x244 identify the specific hardware register.  
Not in the official CAT reference manual. The coefficient RAM at 0xFF8DB3–0xFF8DC4 is a subset of the bulk calibration dataset exported by E0 and E8.

**`SP` (index 115, handler 0x1D214) — Service Parameter / SPI access**  
Multi-sub-command family, dispatched on the first parameter byte:
First parameter byte (0xFF81CA) selects the sub-command (dispatch at 0x1D214):
- `SPW<addr16><data16><cksum>;` (`'W'`, 6 params) — direct SPI write; two bytes sent via `jsr @0x37E2` (the main SPI driver)
- `SPR<addr16><cksum>;` (`'R'`, 4 params) — direct SPI read via `jsr @0x3762`; returns 2 bytes + checksum
- `SPw<idx16><byte>;` (`'w'`, 0x1D35C) — **write one** spectrum-scope noise-floor calibration entry (table at 0xFF8BA2, indices 0x000A–0x0137 = 302 entries); sets 0xFF2012.7
- `SPr<idx16>;` (`'r'`, 0x1D3BC) — **read one** scope noise-floor calibration entry; returns `SPr<idx><byte>;`
- `SPARD<cksum>;` (`'A''R''D'`, 0x1D4DC → 0x1D500, factory mode 0xFF2023.7 required) — **dump all 302** scope calibration bytes in one response (output 0xFF5849, length 0x135 = 309 bytes, running checksum + `;`)
- `SPAWE<cksum>;` (`'A''W''E'`, 0x1D4A4) — save the scope calibration table to EEPROM (`jsr @0x4F78`); factory mode
- `SPACL<cksum>;` (`'A''C''L'`, 0x1D556) — scope calibration clear/reset
- `SPMTR<data>;` (`'M'`) — reads the current meter/S-value via 0x2B5DE (uses the 0x2B5DE configurable-meter path); 12-byte (0xC) reply
- `SPN<val16>;` (`'N'`, write) / `SPN;` (read) — noise-reduction register 0xFF8D14 (range 0–0xE2); applied via 0xD5E4

Every scope sub-command touches only the noise-floor **calibration** table (0xFF8BA2), not live scope data — see the Spectrum Scope section below.

**`VE` (index 116, handler 0x1D642) — Version query (requires password)**  
Format: `VE RAH065H;`  
Response: `R M<main_ver> DSP<dsp_ver> LCD<lcd_ver>;`  
Reads main firmware version from 0x2F11A (`V01-10` = V01 minor-10); DSP and LCD version digits from 0xFF2004–0xFF2007 (hardware registers).

**`JP` (index 117, handler 0x19728) — GPIO port access (requires model code)**  
Format: `JP0891;` (read, returns 15 bytes)  
&emsp;&emsp;&emsp;&emsp;`JP0891<8 hex digits>;` (write, 12 params)  
Reads/writes output port registers 0xFF200A–0xFF200B (band decoder / GPIO lines).  
Write path validates a 1's-complement XOR checksum (nibble-pair1 XOR nibble-pair2 == 0xFF) before applying; calls 0x2502 to activate. "0891" is the FT-891 model number as verification.

**`ZZ` (index 118, handler 0x1968A) — Factory mode entry**  
Format: `ZZ PE0891<nn>;` (total 8 param bytes, where `nn` = 2 hex digit parameter)  
Validates password "PE0891"; decodes `nn` and range-checks (0–7); writes to 0xFF2001 (Port 1 Data Register); then `JMP 0x726` — unconditional jump into factory boot code. This is the master factory-mode entry command.

**`E0` (index 119, handler 0x1D830) — Calibration data read**  
No parameters. Builds an encoded response (~0xE3 bytes) from the calibration table at 0xFF8D66: 20 groups × 10 entries, each byte XOR-encoded with a key derived from the encoder counter (0xFF23CB) plus constants 0x08/0xF6. Returns a checksum-verified frame.

**`E8` (index 120, handler 0x1D912) — Bulk calibration dump**  
No parameters. Response size: 0x294A bytes (~10.6 KB) — the full calibration/alignment dataset. Built from 0xFF2ECC using the same encoding scheme as E0, then streamed via the standard CAT TX path.

#### Extended `ID` command (confirmed at index 44)

Standard read `ID;` → `ID0650;` (model identification = 0650 = FT-891, as per the official spec).

Extended form: `ID0891;` (4 param digits = BCD model number 0891 → decimal 891 = 0x37B)  
Validates the BCD model number via `jsr @0x27C62`; if correct, returns 4-byte firmware version from 0x2F11B–0x2F11F (e.g. `ID0110;` for main version "01-10").

#### EX handler (index 32, handler 0x1A558, ~166 bytes)

The EX handler decodes a 4-digit ASCII menu number and converts it to a global parameter index (0–158) via two ROM tables, then dispatches to read or write sub-functions.

**Decode pipeline:**
1. Validate 4 param bytes as ASCII hex digits (`jsr @0x19716` × 4)
2. Pack into BCD pairs: R0H = BCD(digits 1,2), R0L = BCD(digits 3,4)
3. Call `jsr @0x27C5E` (R1H=1, 1-byte decode) twice to extract:
   - Item within section (last 2 digits, 1-indexed)
   - Section number (first 2 digits, 1-indexed, range 1–18)
4. Range-check both against ROM tables

**Two ROM tables** (18 bytes each, one entry per section):

| Address | Content |
|---------|---------|
| 0x100DA | `max_items[section]` — item count for each section |
| 0x100EC | `base_offset[section]` — cumulative global index for section start |

Global parameter index = `base_offset[section-1] + (item-1)` (0-indexed, 0–158 total)

**Section map** (from ROM tables):
| Section | Items | EX range | Likely topic |
|---------|-------|----------|--------------|
| 01 | 3 | 0101–0103 | AGC delays |
| 02 | 7 | 0201–0207 | LCD / backlight |
| 03 | 2 | 0301–0302 | — |
| 04 | 11 | 0401–0411 | Mode / filter |
| 05 | 20 | 0501–0520 | CW/RTTY/CAT (0506–0508 = CAT baud/TOT/RTS) |
| 06 | 7 | 0601–0607 | TX / MIC |
| 07 | 13 | 0701–0713 | SSB |
| 08 | 12 | 0801–0812 | IF / filter |
| 09 | 6 | 0901–0906 | CW keyer |
| 10 | 11 | 1001–1011 | DVS / messages |
| 11 | 9 | 1101–1109 | Scan |
| 12 | 4 | 1201–1204 | ARS / general |
| 13 | 2 | 1301–1302 | SCP enable |
| 14 | 7 | 1401–1407 | SCP / dial steps |
| 15 | 18 | 1501–1518 | **EQ + P-EQ** (global idx 114–131) |
| 16 | 23 | 1601–1623 | TX power limits |
| 17 | 1 | 1701–1701 | APO |
| 18 | 3 | 1801–1803 | FW versions (read-only) |

**Dispatch** (R3L = number of param bytes before ';'):
- `EX NNNN;` (R3L=4) → read → `jsr @0x17036` with global index in R0L
- `EX NNNN VVV...;` (R3L>4) → write → `jsr @0x15A84` (value decode) + `jsr @0x2576` (apply), then `bset #0x7, @0xFF2012` and `bset #0x4, @0xFF202D` (same update flags as PE)

**EX / PE cross-confirmation:**  
Section 15 has exactly 18 items (global idx 114–131), matching the 18 PE parameter combinations (CA∈{`'0'`,`'2'`} × CB∈{`'0'`–`'2'`} × CC∈{`'0'`–`'2'`}):
- EX 1501–1509 (global 114–122) = SSB TX EQ bands 1–3 (freq/level/bwth) → **PE CA=`'0'`**
- EX 1510–1518 (global 123–131) = P-EQ Mic bands 1–3 (freq/level/bwth) → **PE CA=`'2'`**

Both PE and EX set the same flags (0xFF2012.7, 0xFF202D.4) when writing EQ parameters, confirming they access the same hardware path. `jsr @0x17036` (EX read) should read from the same RAM locations as PE read (0xFF8DB3–0xFF8DC4); not yet confirmed by tracing 0x17036 internals.

---

#### FA handler (index 33, handler 0x1A5FE, ~342 bytes)

**Firmware vs PDF discrepancy: FA uses 9-digit frequency, not 11**

The firmware validates and processes exactly 9 ASCII decimal digit parameters. The PDF states 11 digits — this may reflect a generic Yaesu format for higher-frequency models; the FT-891 implementation uses 9 (sufficient for 0–999,999,999 Hz).

**Write path** (`FA P1[9];`, R3L=9):
1. `jsr @0x3A74` — VFO mode setup (sets 0xFF2012.3, selects I/O register block 0xFF20CA or 0xFF2124)
2. `jsr @0x2C2C` — (high-call utility, function TBD; R3 preserved across call)
3. `jsr @0x2EEB4` — hardware-ready check: tests bits 0xFF2011.7, 0xFF2017.4, 0xFF2017.3; returns Z=0 if radio can accept a frequency change; branch to error if not
4. Validate 9 param bytes as ASCII decimal via `jsr @0x19716` × 9
5. Pack 9 ASCII digits into 5-byte packed-BCD at **0xFF8B8E–0xFF8B92**:
   - Byte 0: digit[0] & 0xF (lone nibble, always 0 for FT-891 ≤ 54 MHz)
   - Bytes 1–4: `(digit[N] << 4) | digit[N+1]` (BCD pairs for digits 1–8)
6. `jsr @0xB370` — apply frequency: transfers 0xFF8B8E staging buffer to primary VFO-A storage (0xFF2372–0xFF2376); returns carry SET on success
7. `bset #0x7, @0xFF8CD0` then `bclr #0x6..1, @0xFF8CD0` — set VFO-A updated flag (bit 7), clear band/mode bits
8. `jsr @0xB3A2` — PLL retune

**Read path** (`FA;`, R3L=0):
1. Reads 4 bytes from 0xFF2372 + 1 byte from 0xFF2376 → staging buffer 0xFF8B8E–0xFF8B92
2. Optional: if 0xFF2070.7 set and mode nibble=1 (CW), adds 1500 Hz (CW pitch offset) → stores TX frequency to **0xFF236E**
3. Formats 9 ASCII digits via `jsr @0x1A72C` (shared nibble-to-ASCII formatter)
4. Response: `FA<9digits>;` = 12 bytes total

**Key RAM locations identified:**
| Address | Content |
|---------|---------|
| 0xFF2372–0xFF2376 | VFO-A frequency (5-byte packed BCD, 9 digits) |
| 0xFF2376–0xFF237A | VFO-B frequency (5-byte packed BCD; shares byte[0] with VFO-A byte[4] — always 0x00 for FT-891 range) |
| 0xFF8B8E–0xFF8B92 | Frequency staging / working buffer |
| 0xFF8CD0 | VFO-A control register: bit 7 = frequency updated flag |
| 0xFF236E | CW TX frequency (VFO-A + 1500 Hz pitch offset, set during read path) |
| 0xFF2070 | Mode / state register (bit 7 = CW active, nibble = mode code) |

Functions discovered:
- `0xB370` — apply packed-BCD frequency from staging buffer to VFO-A storage and PLL
- `0xB3A2` — trigger PLL retune after frequency change
- `0x2EEB4` — hardware-ready check (tests 0xFF2011/0xFF2017 port bits)
- `0x1A72C` — nibble-to-ASCII frequency formatter (shared by FA response and FB response)

Note: 0xFF8CD0 was previously listed as "likely operating frequency (246 accesses)" — the FA analysis shows it is a **VFO control/status register** (bset/bclr on individual bits), not the frequency value itself. Actual VFO-A frequency is at 0xFF2372.

#### MT hidden 38-param write (index 64, handler 0x1B708)

The PDF documents MT as read-only (`MT P1[3];` = 3-digit memory channel recall). The firmware handler
dispatches on two parameter counts:

- **R3L=3 — read**: jumps to 0x1B5C4 inside the MR handler to read memory channel content back
- **R3L=38 (0x26) — undocumented write**: combined "write memory channel with name and TX flag"

The 38-byte write format packs three separate operations into one command:
```
MT <ch[3]> <MW-data[25]> <tx-flag[1]> <name[12]>;
      └──────────────────── 38 params total ────────────────────┘
```
- **params[0-2]** (3 bytes): memory channel number — decoded by `jsr @0x1DDC` (memory init function)
- **params[3-27]** (25 bytes): memory channel content in MW write format (same 25-byte block accepted by `MW P1[25];`)
- **param[28]** (1 byte): `'0'` or `'1'` — TX split flag; `'1'` sets bit 7 of 0xFF2076 (TX configuration register)
- **params[29-38]** (12 bytes): channel name — validated as printable ASCII (0x20–0x7E); stored to 0xFF20BE (12-byte name buffer)

After writing the name, control falls through to the MW handler's core write path at 0x1B788, which
completes the memory channel data write. In effect, `MT P1[38];` = `MW P1[25];` + name + TX flag in
a single transaction.

The `jsr @0x1DDC` function initialises internal memory buffers from ROM default tables at 0x1E9E and
0x1E50 before writes. This function is shared by both MT R3L=38 and MW R3L=25.

**Memory channel name buffer**: 0xFF20BE–0xFF20C9 (12 bytes, printable ASCII)  
**TX split flag**: 0xFF2076 bit 7

---

#### IS actual write format is 7 params (PDF states 4)

The PDF documents `IS P1[4];` (4-digit IF shift value). The firmware handler at 0x1AADA requires a
7-byte write format and 1-byte read format:

```
Read:  IS0;            (R3L=1 — just the VFO-A selector byte '0')
Write: IS0 <M> <S> <D0><D1><D2><D3>;  (R3L=7)
          │   │   └─ 4 hex digits (magnitude, 0x0000–0x04B0 = 0–1200 Hz)
          │   └─ '+' or '-' (sign)
          └─ '0' or '1' (scope: '0' = RX only, '1' = RX+TX)
```

Decode path:
- params[3-6] validated as hex digits via `jsr @0x19716` × 4; packed into a 16-bit value via the
  standard nibble-pack sequence, then decoded by `jsr @0x27C62` (4-digit BCD decoder)
- Magnitude clamped to ≤ 0x04B0 (1200 Hz); rounded to nearest 20 Hz step by `divxs.w #0x14, r3` +
  `mulxs.w #0x14, r3`; stored at a hardware IF shift register
- param[1] checked as `'0'`/`'1'` (RX/TX scope flag); stored for response
- param[2] checked as `'+'`/`'-'`; if `'-'`, the magnitude is negated before storage (`not.l er3; inc.l er3`)

Read path formats the stored values back in the same 7-byte order. Response: `IS0<M><S><D4>;` (8 bytes
total incl. 'IS' prefix, not 7 — there is an extra response byte).

The "P1[4]" in the PDF describes only the magnitude field; it omits the leading VFO selector, scope
mode, and sign bytes.

---

#### Systematic leading-'0' prefix omission in PDF

Systematic inspection of BC, CN, and IS handlers reveals a recurring pattern: the first parameter byte
is always the ASCII character `'0'`, rejected with an error (`bne → 0x19358`) if anything else, yet
the PDF description omits this byte from the parameter count.

| Cmd | Firmware format | PDF format | Hidden byte |
|-----|----------------|------------|-------------|
| IS  | `IS0<M><S><D4>;` R3L=7 | `IS P1[4];` | VFO/scope ('0'/'1') and sign stripped from count |
| BC  | `BC0;` / `BC0<x>;` R3L=1/2 | `BC P1[1];` | leading '0' VFO selector |
| CN  | `CN0<ch><D3>;` R3L=5 / `CN0<ch>;` R3L=2 | `CN P1[1] P2[3];` | leading '0' |

The `'0'` byte likely selects VFO-A (or the primary/only channel on single-VFO models). On a future
dual-VFO variant, a value of `'1'` might select VFO-B. For now the firmware rejects any value other
than `'0'`, so these are effectively mandatory structural bytes.

---

#### PB (index 74, handler 0x1BDBE) — DVS playback is a per-channel toggle (undocumented)

The PDF documents `PB0<P2>;` as P2 = 0 (stop) / 1–5 ("DVS CH 1–5 playback **start**"). The firmware
treats 1–5 as a **toggle**, not a start:

| Send | State | Result |
|------|-------|--------|
| `PB0<n>;` | stopped | play channel *n* |
| `PB0<n>;` | channel *n* playing | **stop** (undocumented toggle-off) |
| `PB0<m>;` | channel *n* playing | stop *n*, start *m* (switch) |
| `PB00;` | any | explicit stop (documented) |
| `PB0;` (read, R3L=1) | — | returns current channel = `0xFF2E9C − 6` (`0` = stopped) |

Handler forms: read `R3L=1` (0x1BE3A), write `R3L=2` (0x1BDCA) — no hidden param counts. The write path
range-checks P2 to `'0'`–`'5'`, then at **0x1BE08** does `bclr #6, @0xFF2040` (clears the "already
playing" gate that `0x76F6` tests) and calls the playback starter `jsr @0x76F6`. With that flag cleared,
`0x76F6` falls through to the shared front-panel DVS handler **`jsr @0x2950C`**.

`0x2950C` is the toggle, keyed on playback-active flag `0xFF2041.7`:
- **not playing** → set `0xFF2E9C = channel+6`, `bset #7/#5 @0xFF2041`, start
- **playing** → `jsr @0x293D0` (stop: zeroes `0xFF2E9C`, clears all `0xFF2041` flags), then compares the
  channel that *was* playing (`0xFF2E9C − 6`, captured pre-stop) against the requested one — if equal,
  `beq 0x29438` returns **without restarting** (stays stopped = toggle off); if different, starts the new
  channel.

So a single repeated `PB0<n>;` turns that DVS message on and off, mirroring the physical DVS keys. The
toggle obeys the same readiness gates as front-panel playback (`0x76F6` bails while transmitting or in
certain modes: checks at 0x7724–0x7756). DVS playback state lives at `0xFF2E9C` (0 = stopped, 6+channel
while playing) and flags at `0xFF2041`.

#### DVS playback: on-air (TX) vs monitor (test), and why CAT can't select monitor

The Advance Manual splits DVS playback into two front-panel operations:
- **"Checking Your Recording"** — select a channel directly → you *hear* the message, **no TX** (monitor/test)
- **"Transmitting the Recorded Message"** — select the **"PB"** panel item, then a channel → plays **on-air (TX)**

The transmit-vs-monitor decision is the **DVS-transmit request bit `0xFF2018.4`**. It is one of the TX
audio sources arbitrated in the transmit-source chain at **0x2E738–0x2E758**:

```
0x2E738  btst #6, @0xFF2018   ; MOX active?   (0xFF2018.6 = MOX, set/cleared by the MX handler 0x1BA52)
0x2E744  btst #5, @0xFF2018   ; (another TX source)
0x2E758  btst #4, @0xFF2018   ; DVS active?   ← DVS-transmit request
```
Any of these being set routes to the "TX source active" branch (0x2E7C4) — i.e. `0xFF2018.4` keys the
transmitter for DVS exactly the way bit 6 does for MOX.

`0xFF2018.4` is **set** by the DVS start/toggle handler `0x2950C` (`bset #4, @0xFF2018` at 0x29552),
gated by operating mode (SSB/AM — `jsr @0x2957A` → mode check `0x3E9A`, plus the `0x29584` mode
dispatch), and **cleared** on DVS stop `0x293D0` (`bclr #4, @0xFF2018` at 0x293E4).

**Consequence for CAT:** the CAT `PB` command routes through `0x2950C`, so in a voice mode (SSB/AM) it
sets `0xFF2018.4` and **transmits on-air** — CAT PB is the *real* (TX) playback. The monitor/test
playback ("Checking Your Recording") plays audio **without** setting `0xFF2018.4`, and is reached only
through the front-panel REC-SETTING UI; no CAT command plays a message while leaving bit 4 clear. So the
**test-vs-TX toggle is front-panel only** — there is no CAT hook for the monitor mode. (The per-channel
front-panel mode flag `0xFF8D9A`, toggled by the panel, is likewise written only by front-panel/menu
code — no CAT writer.)

### Front Panel Keys and VFO Encoder

**Main scan function** @ 0x26484 (called in init + main loop task 5):
- Clears GPIO lines 0xFF2014 bits 5,6 (key matrix drive)
- Reads 0xFF201A bit 0 (key input)
- Tests 0xFF2012 bits 7,5 (encoder state)
- Calls 0x3A24 (GPIO read), 0x279EE, 0x267B0, 0x267FE (key decoding)
- Saves current encoder position to 0xFF236E, 0xFF23A6, 0xFF238A

**IRQ_88 (vec 88 @ 0x2C77C)**: Hardware interrupt from encoder — increments 0xFF23C4 and 0xFF23CB on each detent, clears 0xFFFFC5.0

### Display / LCD

**Init pattern** @ 0x16F4: Fills display buffer with `-----2xxxxx` and `dddddddddd` (7-segment initialization)  
**LCD SPI** (vecs 152–154 @ 0x202B2): 4-byte serial transfer state machine, busy flag at 0xFFFF64  
**Display task** @ 0x0B51E: Main loop task 13 — LCD refresh

### RF / Signal Chain

**PLL/VCO** (init at 0x2834E, 0x28366): Three VCO paths (VCO1-HIGH/LOW, VCO2-HIGH/LOW, VCO3-HIGH/LOW) matching factory alignment menu (bands 1.8–50 MHz + local oscillators)

**RF port** @ 0xFF2073 (135 accesses — heavily used): likely RF frontend control (PA bias, band switching, ATT/IPO)

**Most accessed RAM** @ 0xFF8CD0 (246 accesses): VFO-A control/status register (bit 7 = frequency updated flag) — see FA handler analysis; not the frequency value itself

### Audio / DSP

**Task 2** @ 0x2A86C: Audio/DSP processing (large function, upper flash)  
**Task 3** @ 0x1EF38: RX signal processing  
**Audio inits**: 0x2B1CE (codec), 0x2B05C (audio path), 0x2AB68 (output)

### ADC Metering (and where the supply voltage is NOT)

**Single ADC sampling routine** @ 0x2B24C — the only context that reads the on-chip A/D. The primitive
at 0x2B32C writes a channel number to ADCSR (0xFFFFA0), starts the conversion, polls the busy bit
(0xFFFFA0.7), and the caller reads the result high-byte from ADDRn (0xFFFF90 + 2·n). Only **6 channels
(0–5)** are ever sampled; channels 6/7 are unused. Each result is stored to a RAM mirror at
0xFF2431–0xFF243C, split by TX/RX state (0xFF2011.7):

| Ch | ADDR | RX mirror | RX use | TX mirror | TX use |
|----|------|-----------|--------|-----------|--------|
| 0 | 0xFFFF90 | 0xFF2431 | squelch / S (0x2987C, 0xD6D8) | 0xFF2435 | **PO** power out — `raw×0x91/cal(0xFF8C71)` @ 0x2B8E2 |
| 1 | 0xFFFF92 | 0xFF2432 | squelch / noise (0x297DA) | 0xFF243C | **forward power** — `raw×g/0x80 → 0xFF2E9E` @ 0x2BA44 |
| 2 | 0xFFFF94 | 0xFF2433 | meter (0xD6C2) | 0xFF243B | **reflected / SWR** — vs fwd @ 0x2B904 |
| 3 | 0xFFFF96 | 0xFF2434 (on-demand, averaged → ring buf 0xFF8A59) | slow monitor | 0xFF2438 | **ALC** — segmented scale, cal 0xFF8C81 @ 0x2B806 |
| 4 | 0xFFFF98 | 0xFF2439 | scope noise floor (0x2BA96) | — | (same) |
| 5 | 0xFFFF9A | 0xFF243A | **S-meter** → 12-level bargraph @ 0xD174 | — | (same) |

**Every main-CPU ADC channel is an RF/audio meter (PO / FWD / REF-SWR / ALC / scope-noise / S-meter).
None reads the DC supply voltage.**

**Supply voltage is measured by the control-head (panel) CPU, not the main board.** In the panel
firmware (`AH065_P_V0101.bin`) the routine at 0x8240 reads panel ADC channel 0 (0xFFFF90), running-
averages it into 0xFF2D28, then slew-limits it to a smoothed value 0xFF24E8 (0x94E4) and packs it into
an LCD display descriptor (0x9650 → 0x968E, buffer 0xFF219A). This value is **never transmitted over
the SSI link to the main board** — the panel renders it locally on the LCD during its own power-up,
which is why the input voltage is visible only briefly at turn-on (before the main board establishes
SSI comms and overwrites the display with normal content).

**Consequence for CAT:** there is no main-board register holding the external supply voltage, so no CAT
command can return it as shipped. The `RM` (Read Meter) handler (0x1C866) bounds-checks its index to
0–7 but every index maps through the meter dispatch (0x2B504) to one of the processed meters above;
indices 5–7 return 0 in RX. Exposing supply voltage would require (1) a panel-firmware change to send
0xFF24E8 to the main board in a panel→main SSI message, and (2) a main-firmware change to receive it
and add/repurpose a CAT handler (e.g. an unused `RM` index or a dead stub).

### Spectrum Scope (swept-receiver type)

The FT-891 has a **Spectrum Scope** (documented in the Advance Manual, and configured via menu items
**EX 13-01 SCP START CYCLE** = OFF/3/5/10 s and **EX 13-02 SCP SPAN FREQ** = 37.5/75/150/375/750 kHz).
It is a **swept-receiver** scope, not an FFT: at the START CYCLE interval the main board briefly retunes
the receiver across the SPAN, measures the signal level at each point, and sends the trace to the
control head over the internal SSI bus for LCD rendering. (This is why audio mutes during a sweep and
the trace only refreshes every few seconds.)

#### Sweep engine (main board)

A state machine (state var 0xFF8A57; per-state dwell timer 0xFF8A44, seeded by the EX 13-01 START CYCLE
setting; control flags in 0xFF204D) drives a mechanical sweep of the receiver. On sweep start (0x2A0E0):
- `0xFF8A55 = 0xBF` — **191 points** to collect this sweep
- `0xFF8A56 = 0` (ring write index), `0xFF8A58 = 0` (display window index)
- frequency accumulator `0xFF8A3C` seeded from scope center `0xFF8A38`; per-step advance = `2 ×` the
  16-bit step `0xFF8A40` (derived from the EX 13-02 SPAN) — see 0x2A160

Per point (0x2A184 → 0x2A200): retune RX to `0xFF8A3C`, read the detector level (**ADC channel 3
on-demand mirror, 0xFF2434**), store it into the **ring buffer 0xFF8A59[write-index]**, then advance the
accumulator. Points whose accumulator falls outside the active window store `0x00`. When the 191 points
are done, `0xFF8A57` returns to idle.

#### Trace buffer and the main→panel SSI message (tag 0x70)

The display shows a **151-sample window** of the 191-sample ring buffer, starting at
`0xFF8A59 + (0xFF8A58 + 0x14)`. That window is copied into a large periodic **main→panel SSI message,
tag 0x70** (~381 bytes), assembled in the display buffer at **0xFF2A24** (bulk display fields via
0x25E90/0x225B0; the scope block via **0x25DAA**) and queued for SSI TX (message pointer 0xFF2482,
length 0xFF2486 = 0x17D = 381):

| Msg offset | Size | Content | Panel copy dest |
|-----------:|-----:|---------|-----------------|
| 0   | 1   | tag `0x70` | — |
| 1   | 182 | general display (S-meter, freq digits, icons); the S-meter byte-pair here comes from `0x2B360` | 0xFF295B |
| 183 | 11  | display state | 0xFF28EA |
| 194 | 2   | display state | 0xFF28F5 |
| 196 | 184 | **scope block** (main 0xFF2AE8) | 0xFF2B8F |

**Scope block** (184 bytes, built by 0x25DAA):

| Block offset | Size | Content |
|-------------:|-----:|---------|
| 0    | 1   | scope mode = `0xFF8D04 & 3` (off / on / type) |
| 1    | 2   | marker / param (`0x2A4EC`) |
| 3    | 4   | frequency field `0xFF23A2` |
| 7    | 4   | frequency field `0xFF23A6` |
| 11   | 4   | `0xFF8A46` (scope edge/center) |
| 15   | 151 | **trace levels** — `memcpy` (`0x2A7D6`) of 151 bytes from ring buffer `0xFF8A59 + (0xFF8A58 + 0x14)`; each byte a level, `0xFA` = no-data/blank |
| 166  | ~18 | on-screen label descriptors: `"SPN"` (span), `"SWP"`, `"LV"` |

#### Panel side (decode + render)

RX handler **0x8E22** reads the length-prefixed message from the SSI ring buffer and dispatches on the
tag byte (0x8F1C: 0x20 / 0x21 / 0x40 / 0x42 / 0x43 / 0x70 / 0x71 / 0x72 / 0x74 / 0x76). The **0x70
handler (0x8F3A)** scatters the payload back into 0xFF295B (182) / 0xFF28EA (11) / 0xFF28F5 (2) /
**0xFF2B8F (184 = scope)**. The **scope renderer (0x43B0)** reads the mode byte `0xFF2B8F[0]`, then the
**151 column levels from 0xFF2B9E** (= scope block offset 15); each level is scaled to a bar height
(piecewise map at 0x4400: thresholds 0x32/0x33/0x96, ÷8) and drawn as vertical bars into the LCD
framebuffer at **0xFF259A** using the pixel-pattern table at **0xACCE** (framebuffer rows at +0xA0 /
+0x140 / +0x1E0). Level `0xFA` renders as blank/baseline.

#### Noise-floor / scope calibration table @ 0xFF8BA2 (302 bytes, index 0x000A–0x0137)

- Loaded from EEPROM at init (0x1648, via `jsr @0x379C`); ROM defaults copied from 0x16F4 (0x16C4)
- Part of the bulk calibration image (0xFF2ECC region) that `E8` dumps; restored/verified at 0x1DD20
- Saved back to EEPROM by `SPAWE` (`jsr @0x4F78` → 0x24D4 → `jsr @0x387C`)
- Accessible over CAT: one entry via `SPw`/`SPr`, all 302 at once via `SPARD` (see SP command above)
- Used in the meter/scaling path — `0x2B360 → 0x2BA96` reads entry 0; `0xD98A` indexes it. **Correction
  to an earlier note:** it is *not* subtracted per-point across the 191-sample sweep trace (the trace is
  raw ring-buffer levels); the exact per-bin role of this 302-entry table is scope/meter calibration but
  was not tied to a specific sweep bin.

#### CAT reachability

**Still not retrievable via CAT — now confirmed end-to-end.** The trace lives only in main RAM (ring
buffer 0xFF8A59, then the 0xFF2A24 SSI message) and flows exclusively main→panel over SSI for display.
No CAT handler references the ring buffer, the 0xFF2A24 message, or the sweep engine (all in the main
task region ~0x2A0xx/0x25Dxx, outside the CAT handler range 0x19358–0x1D912). To capture the trace
externally, tap the SSI **0x70** message (scope block at message offset 196; 151 trace bytes at block
offset 15, values 0x00–0xF9, 0xFA = blank), or patch the firmware to add a scope-data CAT/serial output.

### Calibration / Alignment

**Factory alignment table** @ 0xE7B8: 120+ calibration entries covering:
- VDD meter, reference freq, FM center freq
- VCO1/2/3 HIGH/LOW for TX and each local oscillator
- RF-AGC, IF Gain Control (IGC) per band (1.8/HFL/HFM/HFH/50 MHz)
- S-meter calibration (S0, S1, S5, S7, S9, +10 to +60 dB)
- Roofing filter, FM squelch thresholds
- I-ALC per band (10 bands)
- Power calibration: FALC, meter correction (MTR), TX gain (TXG) for 100W/50W/20W/10W/5W × 10 bands
- TX carrier (USB, AM), reverse ALC, ALC meter, FM deviation, SWR meter, IDD, compression meter

**User menu** @ 0x138EE: 16 categories, ~200 items (AGC, Display, DVS, Keyer, General, Mode AM/CW/DATA/FM/RTTY/SSB, RX DSP, Scope, Tuning, TX Audio EQ, TX General, Reset, Version)

### CW Identification

**String** @ 0x22FC: `"DE FT-891 K"` — standard amateur radio CW identification string (sent on power-up or test mode)

### Memory System

**Channel names** @ 0x1B1C6: `P1L P1U P2L P2U ... P9L P9U 501–513 EMG` (paired split-VFO memory channels, 9 banks × 2 + 13 standard + 1 emergency)

---

## Dispatch Mechanisms

### computed_goto Dispatcher (0x2A6AA — called 143×)

This function implements a **Codewarrior/Renesas inline jump table** pattern. It is NOT a traditional function and cannot be decompiled by Ghidra (Ghidra sees only 2 bytes of "function body" because it immediately pops the caller's return address off the stack).

**Calling convention:**
```asm
    MOV.B  #index, R0L       ; load index into R0L
    JSR    @0x2A6AA          ; call dispatcher
    .word  N                 ; inline: max valid index (16-bit, N+1 entries)
    .long  &handler_0        ; inline: 4-byte absolute address for index 0
    .long  &handler_1        ; ...
    ...
    .long  &handler_N
    ; normal post-call code continues here (reached only if index > N)
```

**Dispatcher logic:**
```
POP ER1             ; steal return address — ER1 now = &table_header
R2 = *ER1          ; R2 = N (max index)
if R0 > R2: RTS    ; out of range: fall through to post-call code
ER1 += 2           ; skip over header word
ER1 += R0*4        ; point to table[index]
JMP @*ER1           ; jump to handler (never returns here)
```

Used in 4 confirmed contexts:
- **SSI0 RX ISR (0x2605A)**: state machine for multi-byte panel receive (state index at 0xFF2491)
- **task_state_dispatch (0x2A0B2)**: periodic task dispatch (index at 0xFF8A57)
- **task_cw_rtty_dispatch (0x2D7DC)**: CW/RTTY mode dispatch (index at 0xFF8944)
- **task_action_dispatch (0x29B86)**: action dispatch (index at 0xFF2406)
- **Various others** (the remaining ~139 call sites spread throughout upper flash)

---

## Key Utility Functions (Call Graph — 1254 unique functions via JSR)

| Address | Call count | Identified role |
|---------|-----------|----------------|
| 0x02A6AA | 143 | **computed_goto dispatcher** — see Dispatch Mechanisms section above |
| 0x0037E2 | 131 | **SPI byte transfer**: toggles CS/mode bits at 0xFFFF35/5E, calls 0x391C with successive values (SPI clock or data strobes). Likely front panel or RF-IC SPI driver. |
| 0x003A52 | 113 | Low-level register access utility |
| 0x01E7F4 | 111 | Likely display character/digit output |
| 0x003B7E |  89 | Low-level I/O utility |
| 0x003AA6 |  81 | Low-level I/O utility |
| 0x026952 |  71 | Audio/DSP function (upper flash range) |
| 0x01802E |  65 | Likely menu/string output |
| 0x002C2C |  56 | Register/state utility |
| 0x02B0E4 |  39 | Audio codec control (also called from TCI4V ISR) |

---

## Block Diagram

```mermaid
flowchart TD
    POR(["Power-on / Reset"]) --> COLD
    ALT(["Alt-boot pin"]) -->|"Vec 73 CMI0B"| FWMODE

    subgraph INIT["Cold Start 0x7C8"]
        COLD["SP · CCR · EXR · VBR · SBR · DMA\nGPIO · SCI · PLL/VCO/RF · Audio codec · Display\nRestore: NB level · scan limits · CTCSS\n         DSP filter mode · VFO state"]
    end

    COLD --> ML

    subgraph FWU["Firmware Update 0x404"]
        FWMODE["ASCII parser\nPS;  PS0;  PS1;"]
    end

    subgraph ML["Main Loop 0x15B6 — 16-task cooperative scheduler"]
        direction LR
        T1["1·squelch/pwr\n0x0FC2"] --> T2["2·audio_dsp\n0x2A86C"] --> T3["3·rx_proc\n0x1EF38"] --> T4["4·meters\n0x2E64E"]
        T5["5·keys/enc\n0x26484"] --> T6["6·panel_comm\n0x295E0"] --> T7["7·state_dsp\n0x2A0B2"] --> T8["8·enc_rate\n0x21F64"]
        T9["9·cw_rtty\n0x2D7DC"] --> T10["10·VFO\n0x1DF40"] --> T11["11·debounce\n0x29AFC"] --> T12["12·action\n0x29B86"]
        T13["13·display\n0x0B51E"] --> T14["14·memory\n0x0CE82"] --> T15["15·mode_chg\n0x2935A"] --> T16["16·freq_tx\n0x17BBA"]
        T16 --> T1
    end

    ENC(["VFO encoder\nVec 88 IRQ"]) -->|"counter ++"| T5
    PANEL_B(["Panel board\nSSI0 Vecs 220–222"]) <-->|"0x06 key · 0x15 encoder\n0xE0/E1 display · 0xF0 ACK"| T6
    DSP_C(["TMS320C6746 DSP\nEMIF shared SRAM"]) <-->|"mode index → 0x1182DB8C"| T2
    CATS(["CAT / PC\nSCI3 Vec 106"]) <-->|"RS-232 · 121 cmds"| T7
    LCDS(["LCD\nSPI Vecs 152–154"]) -->|"segment data"| T13
    CWDEC(["CW/RTTY dec\nSSI1 Vecs 224–226"]) -->|"0xA0–0xB4"| T9

    subgraph FLASH["Key Flash Tables"]
        FD["CAT dispatch  0x193B4  121 handlers\nCAT cmds       0x19598  121 commands\nUser menu      0x138EE  ~200 items\nAlign table    0xE7B8   ~120 params\nCh names       0x1B1C6  P1L–EMG\nCW ID string   0x22FC   DE FT-891 K"]
    end

    subgraph SRAM["Internal RAM 0xFFB000–0xFFFFFF"]
        RD["freq 0xFF8CD0 ← hot var  246 accesses\nenc  0xFF23C4, 0xFF23CB\npanel buf  0xFFFE93–0xFFFE95\nLCD SCI    0xFFFF63–0xFFFF64\nboot flag  0xFFFF40\nWDT        0xFFFFA4"]
    end
```

---

## Notes / Open Questions

1. **Vectors 67 and 73 as boot modes**: These timer ISRs contain full CPU init code — most likely triggered artificially during power-up (e.g., test pin pulled low during reset) to enter alternate boot modes. The `BTST @0xFFFF40` at cold start may select the path.

2. **SCI channel assignment**: The `RXI2` (vec 101) handler does signal scaling/interpolation (multiply/divide by 45), suggesting it's processing analog data (S-meter or ALC feedback) rather than CAT commands. The CAT TX is on SCI3 (TXI3, vec 106). Full SCI3 RX path not yet traced.

3. **Vectors 152–154**: LCD SPI sequencer confirmed — 4-state machine at 0x202B2/FC/31E, reads table @0xFF2E86, busy flag @0xFFFF64. Vectors 160–162: confirmed as SSI panel communication at 0x1DAA2/AC8/EEC.

4. **0xFF8CD0** (246 accesses): Single most-written RAM location. Almost certainly the current operating frequency; confirm by tracing VFO task (0x1DF40).

5. **Tasks 6 (0x295E0), 7 (0x2A0B2), 9 (0x2D7DC), 12 (0x29B86), 15 (0x2935A)**: Partially characterized via ISR and computed_goto analysis; full internal logic not yet traced.

---

## Toolchain Setup for Further Analysis

```bash
# Install H8 cross-binutils (already done):
sudo dnf install binutils-h8300-linux-gnu

# Disassemble any address range:
h8300-linux-gnu-objdump -b binary -m h8300s --adjust-vma=0 -D \
    --start-address=0xADDR --stop-address=0xBEND \
    AH065_M_V0110.bin

# Full disassembly (169k lines):
h8300-linux-gnu-objdump -b binary -m h8300s --adjust-vma=0 -D \
    AH065_M_V0110.bin > full_disasm.txt

# Ghidra decompiler (H8S support added via patched SLEIGH spec):
#   Module installed: /opt/ghidra_12.1.2_PUBLIC/Ghidra/Processors/H8/
#   Source: github.com/carllom/sleigh-h8 (H8/300H) + local H8S extensions:
#     - BSET/BCLR/BTST/BNOT/BST/BIST/BAND/BOR/BLD/etc @addr:32  (6A 30/38 prefix)
#     - SHLL/SHAR/SHLR/SHAL #2 variants (op4 += 4 vs #1 encoding)
#   Import command:
analyzeHeadless <project_dir> ft891_main \
    -import AH065_M_V0110.bin \
    -processor "H8:BE:32:H8300" -cspec default \
    -loader BinaryLoader -loader-blockname ROM -loader-baseaddress 0 \
    -analysisTimeoutPerFile 120
#   Result: 884 functions identified, decompiler active for most functions
```

---

*Tools: h8300-linux-gnu-objdump (binutils-h8300-linux-gnu), Python 3 for vector table and string extraction*
*Ghidra 12.1.2 with patched H8S SLEIGH spec for decompilation*
*Binary: AH065_M_V0110.bin, 384 KB, H8S/2600 architecture, big-endian, flat binary at base 0x000000*
