# OFF-to-start capture -> bench replay analysis

- Total rows parsed: 13003
- Capture span: 14.941 s
- 11-bit frames: 10890  | 29-bit frames: 2113
- Distinct 11-bit IDs: 105
- Late window (steady-state) = last 10% of time = [111892634 .. 113386719] us (1.494 s)

## Replay table (11-bit periodic, sorted by frequency)

| ID | count | period(ms) | ~Hz | DLC | steady payload (late 10%) | late variability | CRC+ctr? | name guess | in bench? |
|----|------:|-----------:|----:|---:|----------------------------|------------------|----------|------------|-----------|
| 0x107 | 745 | 20.0 | 50.0 | 8 | `00 00 F8 0B 01 00 6D 57` | 40 variants | static/other | Motor_xx (RPM/engine - bench-confirmed RPM) | YES |
| 0x147 | 745 | 20.0 | 50.0 | 8 | `00 00 00 00 F0 73 C0 15` | 2 variants | static/other | ? | no |
| 0x101 | 738 | 20.0 | 50.0 | 8 | `F4 0E 80 01 A2 05 40 00` | 61 variants | CRC+counter | ESP_02 | no |
| 0x0FD | 737 | 20.0 | 50.0 | 8 | `9F D7 1F 80 00 00 00 00` | 16 variants | static/other | ESP_21 (ESP/ABS dynamics) | no |
| 0x12B | 495 | 30.0 | 33.3 | 8 | `EB 4D 40 28 00 00 00 00` | 16 variants | static/other | ? | no |
| 0x3DC | 302 | 50.0 | 20.0 | 8 | `C0 80 A0 0C 00 05 00 00` | 12 variants | static/other | Kombi/diag? | no |
| 0x30B | 299 | 50.0 | 20.0 | 8 | `10 2E 00 00 08 00 00 10` | 16 variants | static/other | Kombi_01 / KOMBI status (telltale data) | no |
| 0x31E | 298 | 50.0 | 20.0 | 8 | `8B F2 3F 00 00 00 00 40` | 16 variants | static/other | (bench) | YES |
| 0x32F | 298 | 49.9 | 20.0 | 8 | `00 FF 00 00 00 00 FA 00` | static | static/other | unknown | no |
| 0x32A | 296 | 50.0 | 20.0 | 8 | `7C 0B 00 00 48 02 00 00` | 16 variants | static/other | EPB_01? steering/EPS column (bench sends) | YES |
| 0x31B | 295 | 50.0 | 20.0 | 8 | `04 09 00 00 00 00 00 7E` | 16 variants | static/other | unknown | no |
| 0x040 | 282 | 50.0 | 20.0 | 8 | `9D 0D 00 44 C1 00 00 00` | 16 variants | static/other | Airbag_01 (airbag/SRS status) | YES |
| 0x3BE | 160 | 100.0 | 10.0 | 8 | `A1 05 E6 00 C8 80 00 80` | 15 variants | static/other | unknown | no |
| 0x3C0 | 151 | 100.0 | 10.0 | 4 | `35 0F 03 00 00 00 00 00` | 15 variants | static/other | Klemmen_Status_01 (terminal/ignition) | YES |
| 0x3B5 | 150 | 100.0 | 10.0 | 8 | `80 FE 12 02 08 00 20 00` | 2 variants | static/other | unknown | no |
| 0x3E9 | 150 | 99.9 | 10.0 | 8 | `FE F8 DF FF 00 00 00 00` | static | static/other | unknown | no |
| 0x3D5 | 150 | 100.0 | 10.0 | 8 | `B7 C9 40 02 04 00 00 00` | 15 variants | static/other | unknown | no |
| 0x3D6 | 150 | 100.0 | 10.0 | 8 | `09 00 00 00 00 00 30 00` | 15 variants | static/other | unknown | no |
| 0x663 | 149 | 100.0 | 10.0 | 8 | `70 28 20 0E 0F BC 2A 00` | 4 variants | static/other | unknown | no |
| 0x5AC | 149 | 100.0 | 10.0 | 8 | `00 00 FF FE FE F7 07 00` | static | static/other | unknown | no |
| 0x3CF | 149 | 100.1 | 10.0 | 8 | `00 00 00 00 84 00 00 01` | static | static/other | unknown | no |
| 0x48B | 149 | 100.0 | 10.0 | 8 | `00 00 00 00 00 80 03 00` | static | static/other | unknown | no |
| 0x3DA | 149 | 100.0 | 10.0 | 8 | `32 08 00 00 00 58 00 00` | static | static/other | unknown | no |
| 0x3CE | 149 | 100.1 | 10.0 | 8 | `00 00 00 00 84 00 00 00` | static | static/other | unknown | no |
| 0x391 | 149 | 100.0 | 10.0 | 8 | `0E 7F 20 39 00 27 00 22` | 2 variants | static/other | ? | no |
| 0x3C7 | 149 | 100.0 | 10.0 | 8 | `14 10 23 00 00 40 80 00` | 2 variants | static/other | unknown | no |
| 0x3EB | 149 | 100.0 | 10.0 | 8 | `E4 00 00 FF 00 00 00 00` | static | static/other | unknown | no |
| 0x3D0 | 149 | 100.1 | 10.0 | 8 | `01 00 00 00 8C 00 00 00` | static | static/other | ? | no |
| 0x3E5 | 149 | 100.1 | 10.0 | 8 | `93 28 00 00 00 00 00 00` | 15 variants | static/other | Gateway? | no |
| 0x3D1 | 149 | 100.0 | 10.0 | 8 | `00 00 00 00 8C 00 00 00` | static | static/other | unknown | no |
| 0x3D8 | 141 | 100.0 | 10.0 | 8 | `00 00 08 00 00 00 00 00` | static | static/other | unknown | no |
| 0x395 | 140 | 100.0 | 10.0 | 8 | `10 0F 24 04 79 FE 83 1C` | 14 variants | static/other | ? | no |
| 0x394 | 97 | 159.9 | 6.3 | 8 | `93 11 00 1A 00 00 00 00` | 9 variants | static/other | unknown | no |
| 0x462 | 97 | 150.0 | 6.7 | 8 | `00 00 38 00 00 01 00 00` | static | static/other | unknown | no |
| 0x5F0 | 83 | 200.0 | 5.0 | 8 | `AE E4 64 00 00 64 00 00` | 2 variants | static/other | unknown | no |
| 0x583 | 79 | 200.0 | 5.0 | 8 | `00 10 80 01 00 04 40 40` | static | static/other | ? | no |
| 0x551 | 77 | 200.1 | 5.0 | 8 | `F1 22 4C 22 00 00 00 00` | 2 variants | static/other | unknown | no |
| 0x5F2 | 77 | 200.0 | 5.0 | 2 | `40 00 00 00 00 00 00 00` | 2 variants | static/other | unknown | no |
| 0x530 | 75 | 200.0 | 5.0 | 8 | `00 00 00 00 00 00 00 00` | static | static/other | unknown | no |
| 0x584 | 75 | 200.0 | 5.0 | 6 | `43 0F 00 00 00 00 00 00` | 7 variants | static/other | unknown | no |
| 0x5A0 | 75 | 200.0 | 5.0 | 5 | `00 12 80 20 78 00 00 00` | 3 variants | static/other | ? | no |
| 0x5E1 | 75 | 200.0 | 5.0 | 8 | `7C 2A 00 60 FE 00 00 00` | static | static/other | ? | no |
| 0x5E9 | 75 | 200.0 | 5.0 | 8 | `00 4F 01 00 00 00 00 00` | static | static/other | unknown | no |
| 0x668 | 75 | 200.0 | 5.0 | 8 | `02 00 00 37 00 05 00 00` | static | static/other | unknown | no |
| 0x592 | 75 | 200.0 | 5.0 | 8 | `00 00 00 00 00 00 00 00` | static | static/other | unknown | no |
| 0x6B4 | 75 | 200.0 | 5.0 | 8 | `00 91 97 71 29 33 56 57` | 3 variants | static/other | unknown | no |
| 0x116 | 74 | 200.0 | 5.0 | 8 | `D7 09 00 00 00 00 00 FF` | 8 variants | static/other | ESP_19 (wheel/ABS) | YES |
| 0x484 | 74 | 198.7 | 5.0 | 8 | `37 88 50 C2 12 42 00 40` | static | static/other | ? | no |
| 0x485 | 74 | 198.7 | 5.0 | 8 | `09 0C E0 13 CC 81 1B 6A` | 2 variants | static/other | ? | no |
| 0x486 | 74 | 198.7 | 5.0 | 8 | `52 4F B4 8A B2 AE 22 D3` | 2 variants | static/other | unknown | no |
| 0x520 | 73 | 200.0 | 5.0 | 8 | `4B 02 00 08 00 0A 00 0A` | 7 variants | CRC+counter | unknown | no |
| 0x588 | 38 | 498.1 | 2.0 | 8 | `00 00 40 4C 00 00 00 00` | static | static/other | unknown | no |
| 0x670 | 32 | 500.0 | 2.0 | 8 | `19 10 00 00 00 01 00 88` | static | static/other | unknown | no |
| 0x481 | 32 | 497.8 | 2.0 | 8 | `00 00 00 00 00 00 00 00` | static | static/other | unknown | no |
| 0x5E0 | 30 | 498.3 | 2.0 | 8 | `00 00 00 DC 00 00 00 00` | static | static/other | unknown | no |
| 0x5EA | 30 | 499.0 | 2.0 | 8 | `00 00 00 36 F8 FE FB FF` | static | static/other | unknown | no |
| 0x5F4 | 30 | 497.8 | 2.0 | 8 | `60 60 64 00 C1 00 40 00` | static | static/other | unknown | no |
| 0x5EB | 30 | 499.0 | 2.0 | 8 | `00 00 FE FE FB 0F 80 FF` | static | static/other | unknown | no |
| 0x6B0 | 30 | 499.9 | 2.0 | 6 | `E8 01 40 02 74 71 00 00` | 2 variants | static/other | unknown | no |
| 0x6B5 | 30 | 498.4 | 2.0 | 8 | `FD 83 FD 03 FD 00 FD 07` | static | static/other | unknown | no |
| 0x65E | 30 | 500.0 | 2.0 | 8 | `00 00 9A 60 0D 00 00 00` | static | static/other | unknown | no |
| 0x569 | 30 | 500.0 | 2.0 | 8 | `00 00 00 3E F8 10 00 00` | static | static/other | unknown | no |
| 0x2C2 | 30 | 500.0 | 2.0 | 8 | `00 00 00 00 00 00 00 00` | static | static/other | unknown | no |
| 0x640 | 30 | 500.0 | 2.0 | 8 | `A0 78 8B B5 7E 20 CF 08` | 2 variants | static/other | unknown | no |
| 0x647 | 30 | 500.1 | 2.0 | 8 | `B8 FD FF 7F 00 00 00 C1` | 3 variants | static/other | (bench coolant override bundle) | YES |
| 0x64A | 29 | 500.1 | 2.0 | 4 | `00 00 00 00 00 00 00 00` | static | static/other | unknown | no |
| 0x645 | 27 | 428.8 | 2.3 | 8 | `00 20 1C 00 25 00 5E 00` | static | static/other | unknown | no |
| 0x64E | 23 | 997.8 | 1.0 | 8 | `00 00 A8 00 00 00 00 00` | static | static/other | unknown | no |
| 0x585 | 22 | 999.8 | 1.0 | 8 | `02 1C 00 7F 12 00 00 00` | static | static/other | unknown | no |
| 0x656 | 18 | 1000.0 | 1.0 | 8 | `00 30 0A 00 00 00 00 00` | static | static/other | unknown | no |
| 0x650 | 17 | 998.8 | 1.0 | 8 | `01 19 44 00 00 00 00 00` | static | static/other | unknown | no |
| 0x658 | 16 | 1000.0 | 1.0 | 8 | `00 30 04 00 00 00 00 00` | static | static/other | unknown | no |
| 0x65A | 16 | 1000.0 | 1.0 | 8 | `00 00 02 10 00 00 3C 00` | static | static/other | unknown | no |
| 0x3D4 | 16 | 1000.0 | 1.0 | 8 | `CA 0E 80 00 00 04 00 00` | 2 variants | CRC+counter | unknown | no |
| 0x65D | 16 | 1000.0 | 1.0 | 8 | `29 2F 2B 12 00 40 82 7B` | static | CRC+counter | (bench) | YES |
| 0x184 | 15 | 1000.0 | 1.0 | 8 | `00 00 00 00 00 00 00 00` | static | static/other | unknown | no |
| 0x366 | 15 | 1000.0 | 1.0 | 8 | `00 00 00 20 80 03 00 00` | static | static/other | unknown | no |
| 0x6A6 | 15 | 1000.2 | 1.0 | 2 | `10 00 00 00 00 00 00 00` | static | static/other | unknown | no |
| 0x643 | 15 | 1000.7 | 1.0 | 8 | `85 02 13 00 00 00 00 00` | static | static/other | unknown | no |
| 0x386 | 15 | 1000.0 | 1.0 | 8 | `00 00 00 00 00 00 20 00` | static | static/other | unknown | no |
| 0x5F7 | 15 | 1000.0 | 1.0 | 8 | `00 FF FB DF FF FE FF FF` | static | static/other | unknown | no |
| 0x01A | 15 | 50.0 | 20.0 | 8 | `01 79 9C E4 F1 00 00 00` | 5 variants | static/other | unknown | no |
| 0x52A | 15 | 1000.0 | 1.0 | 8 | `00 00 00 00 00 00 00 00` | static | static/other | unknown | no |
| 0x6B6 | 15 | 1000.1 | 1.0 | 6 | `5B 1A 1E 14 21 10 00 00` | static | static/other | unknown | no |
| 0x6B7 | 15 | 1000.1 | 1.0 | 8 | `59 9E 83 04 00 30 00 7C` | static | static/other | unknown | no |
| 0x6B8 | 15 | 1000.1 | 1.0 | 8 | `B8 07 60 01 4B 6C 00 00` | static | static/other | unknown | no |
| 0x641 | 15 | 1000.0 | 1.0 | 8 | `CA 15 42 13 14 12 7D 14` | 2 variants | CRC+counter | (bench) | YES |
| 0x6B2 | 15 | 1000.0 | 1.0 | 8 | `7E 59 9E A3 29 4F C3 27` | 2 variants | static/other | ? | no |
| 0x6AE | 15 | 1000.6 | 1.0 | 4 | `00 00 00 00 00 00 00 00` | static | static/other | unknown | no |
| 0x5F5 | 14 | 1000.0 | 1.0 | 8 | `FE 07 F8 1F 00 FF DF FF` | static | static/other | unknown | no |
| 0x66E | 9 | 1992.4 | 0.5 | 8 | `E0 00 3A 00 FE 00 00 00` | static | static/other | unknown | no |
| 0x671 | 8 | 2000.1 | 0.5 | 8 | `00 01 80 01 00 00 00 00` | static | static/other | unknown | no |
| 0x642 | 7 | 2000.0 | 0.5 | 8 | `1E 00 00 00 0C 18 11 1F` | 5 variants | static/other | unknown | no |
| 0x5BF | 5 | 987.7 | 1.0 | 4 | `00 00 00 40 00 00 00 00` | static | static/other | ? | no |
| 0x155 | 3 | 140.3 | 7.1 | 8 | `FF FF FF FF FF 02 FF FF` | 2 variants | static/other | unknown | no |
| 0x29D | 3 | 176.6 | 5.7 | 8 | `08 EB C0 AF 00 00 10 04` | 3 variants | static/other | unknown | no |
| 0x593 | 2 | 166.0 | 6.0 | 8 | `00 00 00 00 00 00 00 00` | static | static/other | unknown | no |
| 0x157 | 1 | n/a(1 frame) | - | 8 | `D7 EC 5C A5 1A F2 D2 3C` | static | static/other | unknown | no |
| 0x01B | 1 | n/a(1 frame) | - | 8 | `83 0E B4 41 53 A9 A0 59` | static | static/other | unknown | no |
| 0x010 | 1 | n/a(1 frame) | - | 8 | `F3 64 AC DA F3 00 58 A8` | static | static/other | unknown | no |
| 0x011 | 1 | n/a(1 frame) | - | 8 | `9C 90 01 B1 00 00 00 1F` | static | static/other | unknown | no |
| 0x29E | 1 | n/a(1 frame) | - | 8 | `D8 2D A5 6D 70 D2 E4 B6` | static | static/other | unknown | no |
| 0x29F | 1 | n/a(1 frame) | - | 8 | `F1 AA 61 FC 00 00 00 00` | static | static/other | unknown | no |
| 0x012 | 1 | n/a(1 frame) | - | 8 | `37 A8 69 A9 7A B8 C2 1D` | static | static/other | unknown | no |
| 0x013 | 1 | n/a(1 frame) | - | 8 | `EC 70 0F FF 00 00 00 1F` | static | static/other | unknown | no |

## MISSING FROM BENCH (periodic 11-bit IDs present in capture but NOT in bench TX list)

bench currently sends: 0x040, 0x106, 0x107, 0x116, 0x31E, 0x32A, 0x3C0, 0x641, 0x647, 0x65D

| ID | period(ms) | ~Hz | steady payload | CRC+ctr? | name guess |
|----|-----------:|----:|----------------|----------|------------|
| 0x147 | 20.0 | 50.0 | `00 00 00 00 F0 73 C0 15` | static | ? |
| 0x101 | 20.0 | 50.0 | `F4 0E 80 01 A2 05 40 00` | CRC+counter | ESP_02 |
| 0x0FD | 20.0 | 50.0 | `9F D7 1F 80 00 00 00 00` | static | ESP_21 (ESP/ABS dynamics) |
| 0x12B | 30.0 | 33.3 | `EB 4D 40 28 00 00 00 00` | static | ? |
| 0x3DC | 50.0 | 20.0 | `C0 80 A0 0C 00 05 00 00` | static | Kombi/diag? |
| 0x30B | 50.0 | 20.0 | `10 2E 00 00 08 00 00 10` | static | Kombi_01 / KOMBI status (telltale data) |
| 0x32F | 49.9 | 20.0 | `00 FF 00 00 00 00 FA 00` | static | unknown |
| 0x31B | 50.0 | 20.0 | `04 09 00 00 00 00 00 7E` | static | unknown |
| 0x3BE | 100.0 | 10.0 | `A1 05 E6 00 C8 80 00 80` | static | unknown |
| 0x3B5 | 100.0 | 10.0 | `80 FE 12 02 08 00 20 00` | static | unknown |
| 0x3E9 | 99.9 | 10.0 | `FE F8 DF FF 00 00 00 00` | static | unknown |
| 0x3D5 | 100.0 | 10.0 | `B7 C9 40 02 04 00 00 00` | static | unknown |
| 0x3D6 | 100.0 | 10.0 | `09 00 00 00 00 00 30 00` | static | unknown |
| 0x663 | 100.0 | 10.0 | `70 28 20 0E 0F BC 2A 00` | static | unknown |
| 0x5AC | 100.0 | 10.0 | `00 00 FF FE FE F7 07 00` | static | unknown |
| 0x3CF | 100.1 | 10.0 | `00 00 00 00 84 00 00 01` | static | unknown |
| 0x48B | 100.0 | 10.0 | `00 00 00 00 00 80 03 00` | static | unknown |
| 0x3DA | 100.0 | 10.0 | `32 08 00 00 00 58 00 00` | static | unknown |
| 0x3CE | 100.1 | 10.0 | `00 00 00 00 84 00 00 00` | static | unknown |
| 0x391 | 100.0 | 10.0 | `0E 7F 20 39 00 27 00 22` | static | ? |
| 0x3C7 | 100.0 | 10.0 | `14 10 23 00 00 40 80 00` | static | unknown |
| 0x3EB | 100.0 | 10.0 | `E4 00 00 FF 00 00 00 00` | static | unknown |
| 0x3D0 | 100.1 | 10.0 | `01 00 00 00 8C 00 00 00` | static | ? |
| 0x3E5 | 100.1 | 10.0 | `93 28 00 00 00 00 00 00` | static | Gateway? |
| 0x3D1 | 100.0 | 10.0 | `00 00 00 00 8C 00 00 00` | static | unknown |
| 0x3D8 | 100.0 | 10.0 | `00 00 08 00 00 00 00 00` | static | unknown |
| 0x395 | 100.0 | 10.0 | `10 0F 24 04 79 FE 83 1C` | static | ? |
| 0x394 | 159.9 | 6.3 | `93 11 00 1A 00 00 00 00` | static | unknown |
| 0x462 | 150.0 | 6.7 | `00 00 38 00 00 01 00 00` | static | unknown |
| 0x5F0 | 200.0 | 5.0 | `AE E4 64 00 00 64 00 00` | static | unknown |
| 0x583 | 200.0 | 5.0 | `00 10 80 01 00 04 40 40` | static | ? |
| 0x551 | 200.1 | 5.0 | `F1 22 4C 22 00 00 00 00` | static | unknown |
| 0x5F2 | 200.0 | 5.0 | `40 00 00 00 00 00 00 00` | static | unknown |
| 0x530 | 200.0 | 5.0 | `00 00 00 00 00 00 00 00` | static | unknown |
| 0x584 | 200.0 | 5.0 | `43 0F 00 00 00 00 00 00` | static | unknown |
| 0x5A0 | 200.0 | 5.0 | `00 12 80 20 78 00 00 00` | static | ? |
| 0x5E1 | 200.0 | 5.0 | `7C 2A 00 60 FE 00 00 00` | static | ? |
| 0x5E9 | 200.0 | 5.0 | `00 4F 01 00 00 00 00 00` | static | unknown |
| 0x668 | 200.0 | 5.0 | `02 00 00 37 00 05 00 00` | static | unknown |
| 0x592 | 200.0 | 5.0 | `00 00 00 00 00 00 00 00` | static | unknown |
| 0x6B4 | 200.0 | 5.0 | `00 91 97 71 29 33 56 57` | static | unknown |
| 0x484 | 198.7 | 5.0 | `37 88 50 C2 12 42 00 40` | static | ? |
| 0x485 | 198.7 | 5.0 | `09 0C E0 13 CC 81 1B 6A` | static | ? |
| 0x486 | 198.7 | 5.0 | `52 4F B4 8A B2 AE 22 D3` | static | unknown |
| 0x520 | 200.0 | 5.0 | `4B 02 00 08 00 0A 00 0A` | CRC+counter | unknown |
| 0x588 | 498.1 | 2.0 | `00 00 40 4C 00 00 00 00` | static | unknown |
| 0x670 | 500.0 | 2.0 | `19 10 00 00 00 01 00 88` | static | unknown |
| 0x481 | 497.8 | 2.0 | `00 00 00 00 00 00 00 00` | static | unknown |
| 0x5E0 | 498.3 | 2.0 | `00 00 00 DC 00 00 00 00` | static | unknown |
| 0x5EA | 499.0 | 2.0 | `00 00 00 36 F8 FE FB FF` | static | unknown |
| 0x5F4 | 497.8 | 2.0 | `60 60 64 00 C1 00 40 00` | static | unknown |
| 0x5EB | 499.0 | 2.0 | `00 00 FE FE FB 0F 80 FF` | static | unknown |
| 0x6B0 | 499.9 | 2.0 | `E8 01 40 02 74 71 00 00` | static | unknown |
| 0x6B5 | 498.4 | 2.0 | `FD 83 FD 03 FD 00 FD 07` | static | unknown |
| 0x65E | 500.0 | 2.0 | `00 00 9A 60 0D 00 00 00` | static | unknown |
| 0x569 | 500.0 | 2.0 | `00 00 00 3E F8 10 00 00` | static | unknown |
| 0x2C2 | 500.0 | 2.0 | `00 00 00 00 00 00 00 00` | static | unknown |
| 0x640 | 500.0 | 2.0 | `A0 78 8B B5 7E 20 CF 08` | static | unknown |
| 0x64A | 500.1 | 2.0 | `00 00 00 00 00 00 00 00` | static | unknown |
| 0x645 | 428.8 | 2.3 | `00 20 1C 00 25 00 5E 00` | static | unknown |
| 0x64E | 997.8 | 1.0 | `00 00 A8 00 00 00 00 00` | static | unknown |
| 0x585 | 999.8 | 1.0 | `02 1C 00 7F 12 00 00 00` | static | unknown |
| 0x656 | 1000.0 | 1.0 | `00 30 0A 00 00 00 00 00` | static | unknown |
| 0x650 | 998.8 | 1.0 | `01 19 44 00 00 00 00 00` | static | unknown |
| 0x658 | 1000.0 | 1.0 | `00 30 04 00 00 00 00 00` | static | unknown |
| 0x65A | 1000.0 | 1.0 | `00 00 02 10 00 00 3C 00` | static | unknown |
| 0x3D4 | 1000.0 | 1.0 | `CA 0E 80 00 00 04 00 00` | CRC+counter | unknown |
| 0x184 | 1000.0 | 1.0 | `00 00 00 00 00 00 00 00` | static | unknown |
| 0x366 | 1000.0 | 1.0 | `00 00 00 20 80 03 00 00` | static | unknown |
| 0x6A6 | 1000.2 | 1.0 | `10 00 00 00 00 00 00 00` | static | unknown |
| 0x643 | 1000.7 | 1.0 | `85 02 13 00 00 00 00 00` | static | unknown |
| 0x386 | 1000.0 | 1.0 | `00 00 00 00 00 00 20 00` | static | unknown |
| 0x5F7 | 1000.0 | 1.0 | `00 FF FB DF FF FE FF FF` | static | unknown |
| 0x01A | 50.0 | 20.0 | `01 79 9C E4 F1 00 00 00` | static | unknown |
| 0x52A | 1000.0 | 1.0 | `00 00 00 00 00 00 00 00` | static | unknown |
| 0x6B6 | 1000.1 | 1.0 | `5B 1A 1E 14 21 10 00 00` | static | unknown |
| 0x6B7 | 1000.1 | 1.0 | `59 9E 83 04 00 30 00 7C` | static | unknown |
| 0x6B8 | 1000.1 | 1.0 | `B8 07 60 01 4B 6C 00 00` | static | unknown |
| 0x6B2 | 1000.0 | 1.0 | `7E 59 9E A3 29 4F C3 27` | static | ? |
| 0x6AE | 1000.6 | 1.0 | `00 00 00 00 00 00 00 00` | static | unknown |
| 0x5F5 | 1000.0 | 1.0 | `FE 07 F8 1F 00 FF DF FF` | static | unknown |
| 0x66E | 1992.4 | 0.5 | `E0 00 3A 00 FE 00 00 00` | static | unknown |
| 0x671 | 2000.1 | 0.5 | `00 01 80 01 00 00 00 00` | static | unknown |
| 0x642 | 2000.0 | 0.5 | `1E 00 00 00 0C 18 11 1F` | static | unknown |
| 0x5BF | 987.7 | 1.0 | `00 00 00 40 00 00 00 00` | static | ? |

## Bench TX IDs cross-check

- 0x040: present in capture
- 0x106: NOT in capture
- 0x107: present in capture
- 0x116: present in capture
- 0x31E: present in capture
- 0x32A: present in capture
- 0x3C0: present in capture
- 0x641: present in capture
- 0x647: present in capture
- 0x65D: present in capture

## Raw per-ID detail (counter diagnostics)

| ID | count | med_dt_us | b0_distinct | nib_distinct | inc_ratio | sample_n |
|----|------:|----------:|------------:|-------------:|----------:|---------:|
| 0x107 | 745 | 19995.0 | 1 | 1 | 0.00 | 80 |
| 0x147 | 745 | 20000.0 | 1 | 1 | 0.00 | 80 |
| 0x101 | 738 | 20007 | 63 | 16 | 1.00 | 80 |
| 0x0FD | 737 | 20001.0 | 16 | 16 | 1.00 | 80 |
| 0x12B | 495 | 30000.0 | 16 | 16 | 1.00 | 80 |
| 0x3DC | 302 | 49998 | 1 | 1 | 0.00 | 80 |
| 0x30B | 299 | 50000.5 | 1 | 16 | 1.00 | 80 |
| 0x31E | 298 | 50002 | 16 | 16 | 1.00 | 80 |
| 0x32F | 298 | 49943 | 1 | 1 | 0.00 | 80 |
| 0x32A | 296 | 50000 | 16 | 16 | 1.00 | 80 |
| 0x31B | 295 | 49971.0 | 16 | 16 | 1.00 | 80 |
| 0x040 | 282 | 49991 | 16 | 16 | 1.00 | 80 |
| 0x3BE | 160 | 99991 | 16 | 16 | 1.00 | 80 |
| 0x3C0 | 151 | 100009.5 | 16 | 16 | 1.00 | 80 |
| 0x3B5 | 150 | 99973 | 1 | 1 | 0.00 | 80 |
| 0x3E9 | 150 | 99942 | 1 | 1 | 0.00 | 80 |
| 0x3D5 | 150 | 100017 | 16 | 16 | 1.00 | 80 |
| 0x3D6 | 150 | 100001 | 16 | 1 | 0.00 | 80 |
| 0x663 | 149 | 99996.0 | 1 | 1 | 0.00 | 80 |
| 0x5AC | 149 | 100000.5 | 1 | 1 | 0.00 | 80 |
| 0x3CF | 149 | 100080.5 | 1 | 1 | 0.00 | 80 |
| 0x48B | 149 | 99997.0 | 1 | 1 | 0.00 | 80 |
| 0x3DA | 149 | 100003.5 | 1 | 1 | 0.00 | 80 |
| 0x3CE | 149 | 100069.5 | 1 | 1 | 0.00 | 80 |
| 0x391 | 149 | 100010.5 | 5 | 1 | 0.00 | 80 |
| 0x3C7 | 149 | 100000.0 | 2 | 1 | 0.00 | 80 |
| 0x3EB | 149 | 100000.0 | 1 | 1 | 0.00 | 80 |
| 0x3D0 | 149 | 100067.5 | 1 | 1 | 0.00 | 80 |
| 0x3E5 | 149 | 100068.5 | 16 | 16 | 1.00 | 80 |
| 0x3D1 | 149 | 100010.0 | 1 | 1 | 0.00 | 80 |
| 0x3D8 | 141 | 99997.5 | 1 | 1 | 0.00 | 80 |
| 0x395 | 140 | 100004 | 1 | 16 | 1.00 | 80 |
| 0x394 | 97 | 159895.0 | 18 | 16 | 1.00 | 80 |
| 0x462 | 97 | 150009.5 | 1 | 1 | 0.00 | 80 |
| 0x5F0 | 83 | 199979.0 | 6 | 2 | 0.00 | 80 |
| 0x583 | 79 | 199987.0 | 1 | 1 | 0.00 | 79 |
| 0x551 | 77 | 200090.0 | 3 | 1 | 0.00 | 77 |
| 0x5F2 | 77 | 200000.5 | 6 | 1 | 0.00 | 77 |
| 0x530 | 75 | 199960.0 | 1 | 1 | 0.00 | 75 |
| 0x584 | 75 | 200008.0 | 16 | 16 | 1.00 | 75 |
| 0x5A0 | 75 | 200007.0 | 1 | 4 | 0.22 | 75 |
| 0x5E1 | 75 | 200008.0 | 1 | 1 | 0.00 | 75 |
| 0x5E9 | 75 | 199970.5 | 1 | 3 | 0.00 | 75 |
| 0x668 | 75 | 199990.5 | 1 | 1 | 0.00 | 75 |
| 0x592 | 75 | 199962.5 | 1 | 1 | 0.00 | 75 |
| 0x6B4 | 75 | 200006.5 | 3 | 4 | 0.00 | 75 |
| 0x116 | 74 | 199992 | 16 | 8 | 0.00 | 74 |
| 0x484 | 74 | 198662 | 3 | 3 | 0.00 | 74 |
| 0x485 | 74 | 198656 | 2 | 3 | 0.00 | 74 |
| 0x486 | 74 | 198681 | 8 | 2 | 0.01 | 74 |
| 0x520 | 73 | 199978.0 | 23 | 16 | 1.00 | 73 |
| 0x588 | 38 | 498111 | 1 | 1 | 0.00 | 38 |
| 0x670 | 32 | 500012 | 1 | 1 | 0.00 | 32 |
| 0x481 | 32 | 497783 | 1 | 1 | 0.00 | 32 |
| 0x5E0 | 30 | 498292 | 1 | 1 | 0.00 | 30 |
| 0x5EA | 30 | 498966 | 1 | 1 | 0.00 | 30 |
| 0x5F4 | 30 | 497769 | 1 | 1 | 0.00 | 30 |
| 0x5EB | 30 | 498971 | 1 | 1 | 0.00 | 30 |
| 0x6B0 | 30 | 499896 | 2 | 1 | 0.00 | 30 |
| 0x6B5 | 30 | 498386 | 1 | 1 | 0.00 | 30 |
| 0x65E | 30 | 500017 | 1 | 1 | 0.00 | 30 |
| 0x569 | 30 | 499980 | 1 | 1 | 0.00 | 30 |
| 0x2C2 | 30 | 500021 | 1 | 1 | 0.00 | 30 |
| 0x640 | 30 | 500014 | 3 | 3 | 0.00 | 30 |
| 0x647 | 30 | 500050 | 2 | 1 | 0.00 | 30 |
| 0x64A | 29 | 500063.0 | 1 | 1 | 0.00 | 29 |
| 0x645 | 27 | 428823.5 | 1 | 1 | 0.00 | 27 |
| 0x64E | 23 | 997810.0 | 1 | 2 | 0.23 | 23 |
| 0x585 | 22 | 999793 | 3 | 2 | 0.00 | 22 |
| 0x656 | 18 | 999955 | 1 | 1 | 0.00 | 18 |
| 0x650 | 17 | 998836.0 | 2 | 2 | 0.00 | 17 |
| 0x658 | 16 | 999958 | 1 | 1 | 0.00 | 16 |
| 0x65A | 16 | 999979 | 1 | 1 | 0.00 | 16 |
| 0x3D4 | 16 | 1000027 | 16 | 16 | 1.00 | 16 |
| 0x65D | 16 | 999964 | 16 | 16 | 1.00 | 16 |
| 0x184 | 15 | 999992.5 | 1 | 1 | 0.00 | 15 |
| 0x366 | 15 | 1000004.0 | 1 | 1 | 0.00 | 15 |
| 0x6A6 | 15 | 1000164.5 | 1 | 1 | 0.00 | 15 |
| 0x643 | 15 | 1000658.0 | 1 | 1 | 0.00 | 15 |
| 0x386 | 15 | 999971.5 | 1 | 1 | 0.00 | 15 |
| 0x5F7 | 15 | 999967.5 | 1 | 1 | 0.00 | 15 |
| 0x01A | 15 | 50007.0 | 2 | 9 | 0.21 | 15 |
| 0x52A | 15 | 1000050.0 | 1 | 1 | 0.00 | 15 |
| 0x6B6 | 15 | 1000081.0 | 1 | 1 | 0.00 | 15 |
| 0x6B7 | 15 | 1000077.5 | 1 | 1 | 0.00 | 15 |
| 0x6B8 | 15 | 1000051.5 | 1 | 1 | 0.00 | 15 |
| 0x641 | 15 | 1000027.5 | 15 | 15 | 1.00 | 15 |
| 0x6B2 | 15 | 999964.5 | 1 | 1 | 0.00 | 15 |
| 0x6AE | 15 | 1000649.5 | 1 | 1 | 0.00 | 15 |
| 0x5F5 | 14 | 999967 | 1 | 1 | 0.00 | 14 |
| 0x66E | 9 | 1992443.5 | 1 | 1 | 0.00 | 9 |
| 0x671 | 8 | 2000062 | 1 | 1 | 0.00 | 8 |
| 0x642 | 7 | 2000027.0 | 6 | 1 | 0.00 | 7 |
| 0x5BF | 5 | 987692.0 | 1 | 1 | 0.00 | 5 |
| 0x155 | 3 | 140256.0 | 1 | 2 | 0.00 | 3 |
| 0x29D | 3 | 176621.0 | 3 | 3 | 0.00 | 3 |
| 0x593 | 2 | 166029 | 1 | 1 | 0.00 | 2 |
| 0x157 | 1 | - | 1 | 1 | 0.00 | 1 |
| 0x01B | 1 | - | 1 | 1 | 0.00 | 1 |
| 0x010 | 1 | - | 1 | 1 | 0.00 | 1 |
| 0x011 | 1 | - | 1 | 1 | 0.00 | 1 |
| 0x29E | 1 | - | 1 | 1 | 0.00 | 1 |
| 0x29F | 1 | - | 1 | 1 | 0.00 | 1 |
| 0x012 | 1 | - | 1 | 1 | 0.00 | 1 |
| 0x013 | 1 | - | 1 | 1 | 0.00 | 1 |
