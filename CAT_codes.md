# FT-891 CAT Command Reference

Sources:
- **PDF**: Yaesu FT-891 CAT Operation Reference Book (1909-C, September 2019)
- **FW**: Firmware analysis of `AH065_M_V0110.bin`, V01-10, compiled 2021-09-27 (version string at 0x2F11A)

## Legend

| Column | Values |
|--------|--------|
| **PDF** | **Y** = documented in official CAT manual; **N** = not in manual |
| **FW** | **Active** = functional handler; **Stub** = handler is a single `BRA` to error exit (confirmed in binary) |
| **S** | Set command supported |
| **R** | Read command supported |
| **AI** | Auto-Information: **+** = radio sends unsolicited answer when value changes (requires `AI1;`); **—** = not supported |

Parameter notation: `Pn[d]` means field Pn with d digits. Literal `0` means a fixed zero required by the protocol.
Mode codes (P6 in IF/MR/OI/MT/MW): `1`=SSB(USB BFO) `2`=SSB(LSB BFO) `3`=CW(USB BFO) `4`=FM `5`=AM `6`=RTTY(LSB BFO) `7`=CW(LSB BFO) `8`=DATA(LSB BFO) `9`=RTTY(USB BFO) `A`=– `B`=FM-N `C`=DATA(USB BFO) `D`=AM-N

---

## Command Table

| # | Code | PDF | FW | S | R | AI | Set arguments | Read answer / Notes |
|---|------|-----|----|---|---|----|---------------|---------------------|
| 0 | **AB** | Y | Active | S | — | — | `AB;` | Copy VFO-A → VFO-B |
| 1 | **AC** | Y | Active | S | R | + | `AC 0 0 P3;` P3: 0=tuner off, 1=on, 2=start tuning | `AC 0 0 P3;` — Antenna tuner |
| 2 | **AG** | Y | Active | S | R | + | `AG 0 P2[3];` P2: 000–255 | `AG 0 P2[3];` — AF gain |
| 3 | **AI** | Y | Active | S | R | — | `AI P1;` P1: 0=off, 1=on | `AI P1;` — Auto-information mode (resets to 0 at power-off) |
| 4 | **AM** | Y | Active | S | — | — | `AM;` | Copy VFO-A → current memory channel |
| 5 | **AN** | N | Stub | — | — | — | — | No-op in V0110 |
| 6 | **BA** | Y | Active | S | — | — | `BA;` | Copy VFO-B → VFO-A |
| 7 | **BC** | Y | Active | S | R | + | `BC 0 P2;` P2: 0=off, 1=on | `BC 0 P2;` — Auto notch |
| 8 | **BD** | Y | Active | S | — | — | `BD 0;` | Band down (step to next lower band) |
| 9 | **BG** | N | Stub | — | — | — | — | No-op in V0110 |
| 10 | **BI** | Y | Active | S | R | + | `BI P1;` P1: 0=off, 1=on | `BI P1;` — CW break-in |
| 11 | **BM** | N | Stub | — | — | — | — | No-op in V0110 |
| 12 | **BP** | Y | Active | S | R | + | `BP 0 P2 P3[3];` P2: 0=notch on/off, 1=notch freq; P3 when P2=0: 000=off/001=on; P3 when P2=1: 001–320 (×10 Hz) | `BP 0 P2 P3[3];` — Manual notch |
| 13 | **BS** | Y | Active | S | — | — | `BS P1[2];` 00=1.8 MHz 01=3.5 03=7 04=10 05=14 06=18 07=21 08=24.5 09=28 10=50 11=GEN 12=MW | Band select |
| 14 | **BU** | Y | Active | S | — | — | `BU 0;` | Band up (step to next higher band) |
| 15 | **BY** | Y | Active | — | R | — | — | `BY P1 P2;` P1: 0=RX busy off, 1=on; P2: 0 (fixed) — RX busy status |
| 16 | **CF** | Y | Active | S | R | + | `CF 0 P2 0;` P2: 0=clar off, 1=on | `CF 0 P2 0;` — Clarifier on/off |
| 17 | **CH** | Y | Active | S | — | — | `CH P1;` P1: 0=channel up, 1=down | Memory channel step |
| 18 | **CN** | Y | Active | S | R | + | `CN 0 P2 P3[3];` P2: 0=CTCSS, 1=DCS; P3 (CTCSS): 000–049 tone number; P3 (DCS): 000–103 code number | `CN 0 P2 P3[3];` — CTCSS/DCS tone number |
| 19 | **CO** | Y | Active | S | R | + | `CO 0 P2 P3[4];` P2: 0=contour on/off, 1=contour freq, 2=APF on/off, 3=APF freq; P3 by P2: 0→0000=off/0001=on; 1→0010–3200 (contour freq ×10 Hz); 2→0000=off/0001=on; 3→0000–0050 (APF freq, –250 to +250 Hz) | `CO 0 P2 P3[4];` — Contour / APF filter |
| 20 | **CS** | Y | Active | S | R | + | `CS P1;` P1: 0=off, 1=on | `CS P1;` — CW spot tone |
| 21 | **CT** | Y | Active | S | R | + | `CT 0 P2;` P2: 0=off, 1=CTCSS ENC+DEC, 2=CTCSS ENC, 3=DCS | `CT 0 P2;` — CTCSS/DCS mode |
| 22 | **DA** | Y | Active | S | R | — | `DA P1[2] P2[2] P3[2] P4[2] ...;` P1: 01–15 LCD contrast; P2: 01–15 backlight; P3: 00–15 LCD dim; P4: 00–15 TX/BUSY dim (20-char set packet) | `DA P1[2] P2[2] P3[2] P4[2];` — Dimmer settings |
| 23 | **DN** | Y | Active | S | — | — | `DN;` | Microphone DOWN key |
| 24 | **DP** | N | Stub | — | — | — | — | No-op in V0110 |
| 25 | **DS** | N | Stub | — | — | — | — | No-op in V0110 |
| 26 | **DT** | N | Stub | — | — | — | — | No-op in V0110 |
| 27 | **ED** | Y | Active | S | — | — | `ED P1 P2[2];` P1: 0=main encoder, 8=multi-function knob; P2: 01–99 steps | Simulate encoder rotation downward |
| 28 | **EK** | Y | Active | S | — | — | `EK;` | ENT key press |
| 29 | **EM** | N | Stub | — | — | — | — | No-op in V0110 |
| 30 | **EN** | N | Stub | — | — | — | — | No-op in V0110 |
| 31 | **EU** | Y | Active | S | — | — | `EU P1 P2[2];` P1: 0=main encoder, 8=multi-function knob; P2: 01–99 steps | Simulate encoder rotation upward |
| 32 | **EX** | Y | Active | S | R | — | `EX P1[4] P2[n];` P1: menu number 0101–1803; P2: parameter (digit count varies by menu item) | Menu parameter access. Handler (0x1A558) decodes P1 → section (01–18) + item, maps via ROM tables at 0x100DA/0x100EC to global index 0–158; calls 0x15A84+0x2576 (write) or 0x17036 (read). See [EX — Menu](#ex--menu) for structure. |
| 33 | **FA** | Y | Active | S | R | + | `FA P1[9];` P1: 9-digit Hz (000000000–999999999) **(firmware uses 9 digits; PDF states 11)** | `FA P1[9];` — VFO-A frequency. Packs to 5-byte BCD at 0xFF8B8E, applies via 0xB370, retunes PLL via 0xB3A2. VFO-A primary storage: 0xFF2372–0xFF2376. |
| 34 | **FB** | Y | Active | S | R | + | `FB P1[11];` P1: 000030000–056000000 (Hz) | `FB P1[11];` — VFO-B frequency |
| 35 | **FI** | N | Stub | — | — | — | — | No-op in V0110 |
| 36 | **FK** | N | Stub | — | — | — | — | No-op in V0110 |
| 37 | **FO** | N | Stub | — | — | — | — | No-op in V0110 |
| 38 | **FR** | N | Stub | — | — | — | — | No-op in V0110 |
| 39 | **FS** | Y | Active | S | R | + | `FS P1;` P1: 0=fast key off, 1=on | `FS P1;` — VFO-A fast step |
| 40 | **FT** | N | Stub | — | — | — | — | No-op in V0110 |
| 41 | **GT** | Y | Active | S | R | + | `GT 0 P2;` P2: 0=AGC off, 1=fast, 2=mid, 3=slow, 4=auto | `GT 0 P3;` P3: 0=off, 1=fast, 2=mid, 3=slow, 4=auto-fast, 5=auto-mid, 6=auto-slow — AGC |
| 42 | **HR** | N | Stub | — | — | — | — | No-op in V0110 |
| 43 | **HW** | N | Stub | — | — | — | — | No-op in V0110 (binary has `HW`, earlier analysis incorrectly listed as `HI`) |
| 44 | **ID** | Y | Active | — | R | + | — | `ID P1[4];` P1: 0650 (= FT-891). Extended (undocumented): `ID 0891;` → `ID P1[4];` with 4-digit firmware version | Model identification |
| 45 | **IF** | Y | Active | — | R | + | — | `IF` + 27 fields: freq[11] + clarifier_dir(+/-) + clarifier_offset[4] + clar_on + 0 + mode + VFO_status + CTCSS + 0 + offset_dir + `;` — See [IF note](#if-information) |
| 46 | **IS** | Y | Active | S | R | + | Read: `IS0;` (R3L=1). Write: `IS0<M><S><D4>;` (R3L=7) — M='0'/'1' (RX-only or RX+TX shift), S='+'/'−' (sign), D4=4 hex digits (magnitude 0x0000–0x04B0 = 0–1200 Hz, stored in 20 Hz steps). PDF documents `IS P1[4];` — omits leading '0', mode byte M, and sign byte S from param count. Max value 0x04B0 (1200); rounded to nearest 20 Hz. | `IS0<M><S><D4>;` — IF shift (firmware format: 7 params, not 4 as documented) |
| 47 | **KC** | N | Stub | — | — | — | — | No-op in V0110 |
| 48 | **KM** | Y | Active | S | R | — | `KM P1 P2[≤50];` P1: 1–5 (keyer memory channel); P2: message text (up to 50 ASCII chars) | `KM P1 P2;` — CW keyer memory channel read/write |
| 49 | **KP** | Y | Active | S | R | + | `KP P1[2];` 00–75 (300–1050 Hz in 10 Hz steps) | `KP P1[2];` — CW key pitch |
| 50 | **KR** | Y | Active | S | R | + | `KR P1;` P1: 0=off, 1=on | `KR P1;` — CW keyer on/off |
| 51 | **KS** | Y | Active | S | R | + | `KS P1[3];` 004–060 (WPM) | `KS P1[3];` — CW key speed |
| 52 | **KY** | Y | Active | S | — | — | `KY P1;` P1: 1–5=keyer memory 1–5 playback; 6–A=message keyer 1–5 playback | CW keying / message playback trigger |
| 53 | **LK** | Y | Active | S | R | + | `LK P1;` P1: 0=VFO dial lock off, 1=on | `LK P1;` — VFO dial lock |
| 54 | **LM** | Y | Active | S | R | + | `LM 0 P2;` P2: 0=DVS rec stop, 1–5=DVS CH 1–5 rec start/stop | `LM 0 P2;` — DVS (digital voice) record control |
| 55 | **MA** | Y | Active | S | — | — | `MA;` | Memory channel → VFO-A |
| 56 | **MB** | N | Stub | — | — | — | — | No-op in V0110 |
| 57 | **MC** | Y | Active | S | R | + | `MC P1[3];` 001–099 (regular) or P1L–P9U (PMS) | `MC P1[3];` — Memory channel select |
| 58 | **MD** | Y | Active | S | R | + | `MD 0 P2;` P2: mode code (see legend above) | `MD 0 P2;` — Operating mode |
| 59 | **MG** | Y | Active | S | R | + | `MG P1[3];` 000–100 | `MG P1[3];` — Microphone gain |
| 60 | **MK** | N | Stub | — | — | — | — | No-op in V0110 |
| 61 | **ML** | Y | Active | S | R | + | `ML P1 P2[3];` P1: 0=monitor on/off, 1=level; P2 when P1=0: 000=off/001=on; P2 when P1=1: 000–100 | `ML P1 P2[3];` — TX monitor level |
| 62 | **MR** | Y | Active | — | R | + | `MR P0[3];` P0: 001–099 (regular), P1L–P9U (PMS), or EMG | 30-field answer: channel, freq[11], clarifier, mode, CTCSS, offset — See [MR note](#mr-memory-read) |
| 63 | **MS** | Y | Active | S | R | + | `MS P1;` P1: 0=COMP, 1=ALC, 2=PO, 3=SWR, 4=ID | `MS P1;` — Front-panel meter selection |
| 64 | **MT** | Y | Active | S | R | — | Read: `MT P1[3];` (3-digit channel → recall, R3L=3, jumps into MR read logic). **Hidden write (R3L=38, undocumented):** `MT <ch[3]> <MW-data[25]> <tx-flag> <name[12]>;` — params[0-2]=channel, params[3-27]=MW-format data, param[28]='0'/'1' TX split flag (→0xFF2076.7), params[29-38]=12-char printable ASCII name (→0xFF20BE). Falls through to MW core at 0x1B788 after writing name. PDF documents MT as read-only only. | Memory tune (recall) + undocumented combined channel-write-with-name |
| 65 | **MW** | Y | Active | S | — | — | `MW P1[3] P2[11] P3 P3[4] P4 0 P6 P7 P8 P9 P10;` P1=channel, P2=freq, P3=clarifier dir+offset, P4=clar on, P6=mode, P7=VFO/mem, P8=CTCSS, P9=0(fixed), P10=offset dir | Memory channel write (no read; use MR to read back) |
| 66 | **MX** | Y | Active | S | R | + | `MX P1;` P1: 0=MOX off, 1=on | `MX P1;` — Manual PTT (MOX) |
| 67 | **NA** | Y | Active | S | R | + | `NA 0 P2;` P2: 0=off, 1=on | `NA 0 P2;` — Narrow IF bandwidth |
| 68 | **NB** | Y | Active | S | R | + | `NB 0 P2;` P2: 0=off, 1=on | `NB 0 P2;` — Noise blanker |
| 69 | **NL** | Y | Active | S | R | + | `NL 0 P2[3];` P2: 000–010 | `NL 0 P2[3];` — Noise blanker level |
| 70 | **NR** | Y | Active | S | R | + | `NR 0 P2;` P2: 0=off, 1=on | `NR 0 P2;` — Noise reduction |
| 71 | **OI** | Y | Active | — | R | + | — | Same format as IF but for opposite band (VFO-B in split) — See [OI note](#oi-opposite-band-information) |
| 72 | **OS** | Y | Active | S | R | + | `OS 0 P2;` P2: 0=simplex, 1=plus shift, 2=minus shift | `OS 0 P2;` — Repeater offset direction (FM mode only) |
| 73 | **PA** | Y | Active | S | R | + | `PA 0 P2;` P2: 0=IPO (no preamp), 1=AMP | `PA 0 P2;` — Preamplifier / IPO |
| 74 | **PB** | Y | Active | S | R | + | Read `PB0;` → `PB0<n>;` (n=current channel, 0=stopped). Write `PB0<P2>;` P2: 0=stop, 1–5=DVS CH 1–5. **Undocumented:** P2 1–5 is a per-channel **toggle**, not just start — re-sending the channel that is already playing stops it (see note). | `PB0<P2>;` — DVS (digital voice) playback / per-channel toggle |
| 75 | **PC** | Y | Active | S | R | + | `PC P1[3];` 005–100 | `PC P1[3];` — TX power level |
| 76 | **PE** | N | Active | S | R | — | `PE<CA><CB><CC><D4><D5><D6>;` CA∈{'0','2'} (EQ channel), CB∈{'0','1','2'} (band), CC∈{'0','1','2'} (freq/level/bwth), D4D5D6=value (sign+2digits for CC='1') | `PE<CA><CB><CC><sign><v1><v2>;` — Parametric EQ band coefficient read/write (index 76, handler 0x1BF1E). CA selects EQ bank; CB selects band 1–3; CC='0'=freq (0–7/9/18), CC='1'=level (−20 to +10 dB), CC='2'=bandwidth (1–10). Updates calibration RAM 0xFF8DB3–0xFF8DC4 and hardware immediately via SPI (jsr @0x37E2). Not in PDF — factory/service use only. |
| 77 | **PL** | Y | Active | S | R | + | `PL P1[3];` 000–100 | `PL P1[3];` — Speech processor level |
| 78 | **PR** | Y | Active | S | R | + | `PR P1 P2;` P1: 0=speech processor, 1=parametric mic EQ; P2: 0=off, 1=on | `PR P1 P2;` — Speech processor / parametric mic EQ |
| 79 | **PS** | Y | Active | S | R | + | `PS P1;` P1: 0=power off, 1=power on (send dummy byte first, then wait 1–2 s before issuing) | `PS P1;` — Power switch |
| 80 | **QI** | Y | Active | S | — | — | `QI;` | Store current VFO to Quick Memory Bank |
| 81 | **QR** | Y | Active | S | — | — | `QR;` | Recall from Quick Memory Bank |
| 82 | **QS** | Y | Active | S | — | — | `QS;` | Quick split (store VFO-A → QMB, enable split) |
| 83 | **RA** | Y | Active | S | R | + | `RA 0 P2;` P2: 0=ATT off, 1=on | `RA 0 P2;` — RF attenuator |
| 84 | **RC** | Y | Active | S | — | — | `RC;` | Clear (zero) clarifier offset |
| 85 | **RD** | Y | Active | S | — | — | `RD P1[4];` P1: 0000–9999 Hz step | Clarifier step down |
| 86 | **RF** | N | Stub | — | — | — | — | No-op in V0110 |
| 87 | **RG** | Y | Active | S | R | + | `RG 0 P2[3];` P2: 000–030 | `RG 0 P2[3];` — RF gain |
| 88 | **RI** | Y | Active | — | R | + | `RI P1;` P1: 0=Hi-SWR, 3=REC, 4=PLAY, A=TX LED, B=RX LED | `RI P1 P2;` P2: 0=off, 1=on — Radio indicator / LED status |
| 89 | **RL** | Y | Active | S | R | + | `RL 0 P2[2];` P2: 01–15 | `RL 0 P2[2];` — Noise reduction level |
| 90 | **RM** | Y | Active | — | R | + | `RM P1;` P1: 0=front-panel meter, 1=S, 2=front-panel meter (PO/COMP/ALC/SWR/ID), 3=COMP, 4=ALC, 5=PO, 6=SWR, 7=ID | `RM P1 P2[3];` P2: 000–255 — Read meter value |
| 91 | **RO** | N | Stub | — | — | — | — | No-op in V0110 |
| 92 | **RS** | Y | Active | — | R | + | — | `RS P1;` P1: 0=normal mode, 1=menu mode — Radio operating status |
| 93 | **RT** | N | Stub | — | — | — | — | No-op in V0110 |
| 94 | **RU** | Y | Active | S | — | — | `RU P1[4];` P1: 0000–9999 Hz step | Clarifier step up |
| 95 | **SC** | Y | Active | S | R | + | `SC P1;` P1: 0=scan off, 1=scan up, 2=scan down | `SC P1;` — Scan control |
| 96 | **SD** | Y | Active | S | R | + | `SD P1[4];` P1: 0030–3000 ms | `SD P1[4];` — CW semi break-in delay time |
| 97 | **SF** | N | Stub | — | — | — | — | No-op in V0110 |
| 98 | **SH** | Y | Active | S | R | + | `SH 0 P2 P3[2];` P2: 0=off, 1=on; P3: 00–21 (bandwidth code, see SH table PDF p.17) | `SH 0 P2 P3[2];` — IF bandwidth (width filter) |
| 99 | **SM** | Y | Active | — | R | + | `SM 0;` | `SM 0 P2[3];` P2: 000–255 — S-meter reading |
| 100 | **SQ** | Y | Active | S | R | + | `SQ 0 P2[3];` P2: 000–100 | `SQ 0 P2[3];` — Squelch level |
| 101 | **ST** | Y | Active | S | R | + | `ST P1;` P1: 0=split off, 1=split on, 2=split on +5 kHz | `ST P1;` — Split operation |
| 102 | **SV** | Y | Active | S | — | — | `SV;` | Swap VFO-A ↔ VFO-B |
| 103 | **TS** | Y | Active | S | R | + | `TS P1;` P1: 0=TXW off, 1=on | `TS P1;` — TX-watch (TXW). Note: internally bypassed by a direct check at 0x19324 |
| 104 | **TX** | Y | Active | S | R | + | `TX P1;` P1: 0=TX off/CAT TX off, 1=TX on/CAT TX on, 2=TX on/CAT TX off (answer-only) | `TX P1;` — TX control |
| 105 | **UL** | Y | Active | — | R | + | — | `UL P1;` P1: 0=PLL locked, 1=unlocked — PLL unlock status |
| 106 | **UP** | Y | Active | S | — | — | `UP;` | Microphone UP key |
| 107 | **VD** | Y | Active | S | R | + | `VD P1[4];` P1: 0030–3000 ms (10 ms steps) | `VD P1[4];` — VOX delay time |
| 108 | **VF** | N | Stub | — | — | — | — | No-op in V0110 |
| 109 | **VG** | Y | Active | S | R | + | `VG P1[3];` 000–100 | `VG P1[3];` — VOX gain |
| 110 | **VM** | Y | Active | S | — | — | `VM;` | [V/M] key function (VFO ↔ Memory toggle) |
| 111 | **VS** | N | Stub | — | — | — | — | No-op in V0110 |
| 112 | **VX** | Y | Active | S | R | + | `VX P1;` P1: 0=VOX off, 1=on | `VX P1;` — VOX on/off |
| 113 | **XT** | N | Stub | — | — | — | — | No-op in V0110 (4-byte handler; not in PDF) |
| 114 | **ZI** | Y | Active | S | — | — | `ZI;` | CW auto zero-in |

---

## Undocumented Active Commands (Factory / Diagnostic)

These six commands are not in the official CAT manual. They appear at the tail of the dispatch table (indices 115–120) and have substantial handlers implementing factory and service functions.

| # | Code | PDF | FW | S | R | AI | Arguments / Response | Function |
|---|------|-----|----|---|---|----|----------------------|----------|
| 115 | **SP** | N | Active | S | R | — | Sub-commands (see below) | Service Parameter — SPI bus access, spectrum-scope noise-floor **calibration** (not live scope data), noise-reduction register |
| 116 | **VE** | N | Active | — | R | — | `VE RAH065H;` → `R M<ver> DSP<dsp> LCD<lcd>;` | Version query (password = `RAH065H`). Returns main, DSP, and LCD firmware versions |
| 117 | **JP** | N | Active | S | R | — | Read: `JP 0891;` → 15-byte hex response. Write: `JP 0891 <8 hex digits>;` (1's-complement XOR checksum required: pair1 XOR pair2 = 0xFF) | GPIO port access — reads/writes output port registers 0xFF200A–0xFF200B (band decoder / GPIO lines). Password `0891` = FT-891 model number |
| 118 | **ZZ** | N | Active | S | — | — | `ZZ PE0891 <nn>;` where `nn` = 2 hex digits, 0–7 | Factory mode entry. Password `PE0891`. Writes `nn` to Port 1 Data Register (0xFF2001), then `JMP 0x726` (factory boot code) |
| 119 | **E0** | N | Active | — | R | — | `E0;` → ~0xE3 bytes (encoded) | Calibration data export. Reads 200 entries (20 groups × 10 bytes) from calibration table at 0xFF8D66. Each byte XOR-encoded with key derived from encoder counter (0xFF23CB). Checksummed per-group and overall |
| 120 | **E8** | N | Active | — | R | — | `E8;` → 0x294A bytes (~10.6 KB, encoded) | Bulk calibration / alignment dump. Full dataset from 0xFF2ECC, same XOR encoding as E0 |

### SP Sub-commands

`SP` dispatches on the first parameter byte:

| Sub-cmd | Format | Direction | Description |
|---------|--------|-----------|-------------|
| `W` | `SPW<addr[2]><data[2]><cksum>;` (6 params) | Write | Direct SPI **bus** write via SPI driver (0x37E2). Checksum validated |
| `R` | `SPR<addr[2]><cksum>;` (4 params) | Read | Direct SPI **bus** read via 0x3762; returns 2 data bytes + checksum |
| `w` | `SPw<idx[2]><byte>;` | Write | Write **one** spectrum-scope noise-floor calibration entry (table 0xFF8BA2, indices 0x000A–0x0137 = 302 entries); handler 0x1D35C, sets 0xFF2012.7 |
| `r` | `SPr<idx[2]>;` → `SPr<idx><byte>;` | Read | Read **one** scope noise-floor calibration entry; handler 0x1D3BC |
| `ARD` | `SPARD<cksum>;` | Read | **Dump all 302** scope calibration bytes in one response (309 bytes, output 0xFF5849); handler 0x1D4DC→0x1D500. Requires factory mode (0xFF2023.7) |
| `AWE` | `SPAWE<cksum>;` | Write | Save the scope calibration table to EEPROM (0x4F78→0x24D4→0x387C); handler 0x1D4A4. Factory mode |
| `ACL` | `SPACL<cksum>;` | Write | Scope calibration clear/reset; handler 0x1D556. Factory mode |
| `MTR` | `SPMTR<data[5]>;` | Read | Reads current meter / S-value via 0x2B5DE; 12-byte reply; handler 0x1D43E |
| `N` | `SPN<val[2]>;` (write) / `SPN;` (read) | R/W | Noise-reduction register 0xFF8D14, range 0–0xE2 (226); applied via 0xD5E4 |

**Note:** every scope sub-command (`w`/`r`/`ARD`/`AWE`/`ACL`) accesses only the **noise-floor calibration** table (0xFF8BA2) — the per-bin constants the firmware *subtracts* to flatten the trace. There is **no CAT command for live spectrum-scope data**; the swept trace is generated on the main board and streamed to the control head over the internal SSI bus for LCD display only. See `MAIN_FIRMWARE_ANALYSIS.md` → "Spectrum Scope".

---

## Notes on Complex Commands

### IF — Information

Read: `IF;`

Answer format (29 characters + terminator):
```
IF <freq[11]> <clar_dir> <clar_offset[4]> <clar_on> <0> <mode> <vfo_status> <ctcss> <0> <offset_dir> ;
```

| Field | Chars | Values |
|-------|-------|--------|
| Freq (VFO-A) | 11 | Hz, e.g. `014250000` |
| Clar direction | 1 | `+` or `-` |
| Clar offset | 4 | 0000–9999 Hz |
| Clar on/off | 1 | 0=off, 1=on |
| Fixed | 1 | `0` |
| Mode | 1 | See legend |
| VFO/memory | 1 | 0=VFO, 1=Memory, 2=Memory Tune, 5=PMS |
| CTCSS | 1 | 0=off, 1=ENC+DEC, 2=ENC |
| Fixed | 1 | `0` |
| Offset dir | 1 | 0=simplex, 1=plus shift, 2=minus shift |

### OI — Opposite Band Information

Same format as IF but returns VFO-B (the "opposite" or TX band in split mode). Read: `OI;`

OI P7 (VFO/memory) field also supports: 0=VFO, 1=Memory, 2=Memory Tune, 3=QMB, 4=QMB-MT, 5=PMS, 6=HOME.

### MR — Memory Channel Read

Read: `MR P0[3];`  P0 = memory channel number (001–099, P1L–P9U, or EMG)

Answer format (30+ characters + terminator):
```
MR <chan[3]> <freq[11]> <clar_dir> <clar_offset[4]> <clar_on> <0> <mode> <vfo_status> <ctcss> <0> <offset_dir> ;
```

Fields are the same as IF with the addition of the 3-digit memory channel at the start.

### EX — Menu

`EX P1[4] P2[n];`  P1 = menu number (0101–1803), P2 = value.

**Internal structure** (from handler 0x1A558 disassembly):  
Menu number decoded → section (01–18) + item within section. Two ROM tables at **0x100DA** (max items per section, 18 bytes) and **0x100EC** (section base offsets, 18 bytes) map to a **global parameter index 0–158** (total 159 parameters). Write path sets same flags as PE (0xFF2012.7, 0xFF202D.4).

Section 15 (EX 1501–1518, global idx 114–131) = EQ + P-EQ parameters, directly corresponding to the PE CAT command:  
EX 1501–1509 = SSB TX EQ bands 1–3 → PE CA=`'0'`; EX 1510–1518 = P-EQ Mic bands 1–3 → PE CA=`'2'`.

Selected frequently-used menu items:

| P1 | Function | P2 |
|----|----------|----|
| 0101–0103 | AGC fast/mid/slow delay | 20–4000 ms |
| 0201–0204 | LCD contrast, backlight, dimmer LCD, dimmer TX/BUSY | 01–15 |
| 0506 | CAT baud rate | 0=4800, 1=9600, 2=19200, 3=38400 |
| 0507 | CAT TOT | 0=10ms, 1=100ms, 2=1000ms, 3=3000ms |
| 0508 | CAT RTS | 0=disable, 1=enable |
| 1301 | SCP start cycle | 0=off, 1=3s, 2=5.5s, 3=10s |
| 1302 | SCP span freq | 0=37.5kHz, 1=75kHz, 2=150kHz, 3=375kHz, 4=750kHz |
| 1401–1408 | Quick dial, dial steps per mode (SSB/AM/FM/AM CH) | various |
| 1601–1606 | HF/50M TX power limits per mode | 5–100 W |
| 1801 | Main FW version (read only) | 0000–9999 |
| 1802 | DSP FW version (read only) | 0000–9999 |
| 1803 | LCD FW version (read only) | 0000–9999 |

---

## Summary

| Category | Count |
|----------|-------|
| Documented in PDF (functional) | 89 |
| Undocumented, active — factory/diagnostic | 7 (SP, VE, JP, ZZ, E0, E8, PE) |
| Dead stubs (registered in table, always return error) | 25 |
| **Total in firmware dispatch table** | **121** |

Dead stubs (all confirmed `BRA 0x19358` in binary): AN, BG, BM, DP, DS, DT, EM, EN, FI, FK, FO, FR, FT, HR, HW, KC, MB, MK, RF, RO, RT, SF, VF, VS, XT

**PE** (index 76, handler 0x1BF1E): parametric EQ band coefficient access. CA=EQ channel ('0'/'2', likely TX-EQ vs P-EQ Mic); CB=band 1–3; CC='0'=frequency index, '1'=level (signed, −20..+10 dB), '2'=bandwidth (1–10). Freq option counts per band (7/9/18) match EX menus 1501–1518 exactly. Coefficients stored at 0xFF8DB3–0xFF8DC4 and pushed to hardware via SPI driver (jsr @0x37E2) on every write.

---

## Hidden Extended Forms and Format Discrepancies

Commands where the firmware behavior differs from the PDF documentation, discovered by scanning all 121 handlers for multi-R3L dispatch logic:

### MT — Hidden 38-param combined write (undocumented)

PDF says MT is read-only (`MT P1[3];` = memory channel recall). Firmware handler at 0x1B708 also
accepts R3L=38 (never documented):

```
MT <ch[3]> <MW-data[25]> <tx[1]> <name[12]>;
```
Params[0-2] = 3-digit channel; params[3-27] = 25-byte MW-format channel data; param[28] = '0'/'1'
TX split flag (sets 0xFF2076 bit 7); params[29-38] = 12-char printable ASCII channel name stored at
0xFF20BE. After writing the name the code falls through to MW's core write path at 0x1B788, performing
the channel data write atomically. Both MT and MW share the memory init function at 0x1DDC.

### IS — Actual wire format is 7 bytes, not 4

PDF: `IS P1[4];`. Firmware: R3L=7 write, R3L=1 read.

```
Write: IS0<M><S><D0D1D2D3>;    (7 params)
Read:  IS0;                     (1 param)
```
M = '0'/'1' (RX-only / RX+TX scope); S = '+'/'-' (sign of shift); D0-D3 = 4 hex digits of magnitude
(0x0000–0x04B0 = 0–1200 Hz, rounded to 20 Hz steps by divxs/mulxs #20). PDF counts only the
magnitude field and omits M, S, and the mandatory leading '0'.

### Systematic leading-'0' prefix omitted in PDF

Multiple command handlers enforce a mandatory first-param byte of '0' (VFO-A selector) that the PDF
does not mention:

| Cmd | Firmware R3L | PDF params | Undocumented prefix |
|-----|-------------|-----------|---------------------|
| IS  | 1 / 7 | — / 4 | leading '0' + mode + sign not counted |
| BC  | 1 / 2 | — / 1 | leading '0' (VFO selector) |
| CN  | 2 / 5 | — / 4 | leading '0' (VFO selector) |

The byte is always ASCII '0'; any other value returns error. On dual-VFO hardware '1' might select
VFO-B, but the FT-891 rejects it, making these bytes mandatory structural prefixes.

### PB — DVS playback is a per-channel toggle (undocumented)

The PDF documents `PB0<P2>;` with P2 = 0 (stop) / 1–5 ("DVS CH 1–5 playback start"). The firmware
does not merely *start* on 1–5 — it **toggles** that channel:

| Send | State | Result |
|------|-------|--------|
| `PB0<n>;` | stopped | play channel *n* |
| `PB0<n>;` | channel *n* playing | **stop** (undocumented toggle-off) |
| `PB0<m>;` | channel *n* playing | stop *n*, start *m* (switch) |
| `PB00;` | any | explicit stop (documented) |
| `PB0;` | — | read current channel (0xFF2E9C − 6; 0 = stopped) |

Mechanism: the PB write handler (0x1BDBE) clears 0xFF2040.6 at 0x1BE08 before calling the playback
starter 0x76F6, which therefore routes to the shared front-panel DVS handler **0x2950C**. That handler
is a toggle keyed on the playback-active flag 0xFF2041.7: if already playing it calls the stop routine
0x293D0 and, when the requested channel equals the one that was playing, returns without restarting.
So a single repeated `PB0<n>;` turns that message on and off, exactly like the physical DVS keys. Obeys
the same readiness gates as front-panel playback (0x76F6 bails while transmitting / in certain modes).
