# MK7 Cluster Bench Controller

A Python web UI to control a **VW Golf MK7 instrument cluster** on a bench (or bridge a real
vehicle) over USB serial → ESP32 → CAN bus. The original goal of the project was to **repurpose
the analog coolant temperature gauge to display turbocharger boost pressure** in real time,
but the framework grew to expose most cluster functions documented in the openDBC and
[r00li/CarCluster](https://github.com/r00li/CarCluster) reverse-engineering work.

Tested cluster: **5G1 920 740B** (MK7 Alltrack 2017 highline, FIS+ MFA).

> **Status: dormant bench tool.** The web UI is complete and nothing marks it as abandoned
> (the `python vw_mqb.py` CRC self-test passes), but its code has not changed since
> 2026-04-26 and the DBC files since 2026-05-11.
> In-car use has moved to [BOT32](https://github.com/ALagrandeur/BOT32) (ESP32 firmware,
> v4.6.0), which also has its **own bench mode** in the firmware (`BOT32/bench_test.cpp`,
> `BOT32/bench_frames.cpp`) and its own web UI. Use this repo to drive a cluster on the table
> from a PC through an ESP32 running ESP32RET, or as a reference.

## Project map (all vehicle projects)

| Vehicle | Device | Repo / folder | Role |
|---|---|---|---|
| Golf MK7 Alltrack 2017 | ESP Main (ESP32 + HAT WaveShare 2-CH CAN) | [BOT32](https://github.com/ALagrandeur/BOT32) | jauge boost sur le combiné, données live, interface web (cellulaire + PC), effacement des codes moteur, commande des modes Haldex |
| Golf MK7 Alltrack 2017 | ESP32-CAN-X2 en série sur le bus Haldex | [BOT32-HALDEX](https://github.com/ALagrandeur/BOT32-HALDEX) (privé) | modes Haldex STOCK / FWD / 50-50 |
| Westfalia | ESP32-CAN-X2 | [Remote32](https://github.com/ALagrandeur/Remote32) / Emetteur_CAN_X2 | lit le CAN du Microsquirt et diffuse les données (ESP-NOW + WiFi/UDP) |
| Westfalia | ESP32-P4 écran rond 3.4" | [Remote32](https://github.com/ALagrandeur/Remote32) / Recepteur_P4_IDF | tableau de bord à cadrans (version finale v1.4) |
| Les deux | ESP32-S3 AMOLED 1.8" | [Remote32](https://github.com/ALagrandeur/Remote32) / Recepteur_AMOLED | manette universelle : cadrans Westfalia + mode Golf (modes Haldex) |
| **Outil** | **ESP32 (ESP32RET) + PC** | **[mk7-cluster-bench-controller](https://github.com/ALagrandeur/mk7-cluster-bench-controller)** | **banc d'essai du combiné MK7 (dormant)** |
| Référence | — | [OpenHaldex-C6-perso](https://github.com/ALagrandeur/OpenHaldex-C6-perso) | copie non modifiée d'OpenHaldex-C6, non utilisée |
| Archivé | — | [MK7BoostGauge](https://github.com/ALagrandeur/MK7BoostGauge) | ancêtre de BOT32 (Raspberry Pi) |

The row in bold is this repository.

## What this repo is today

- **The original bench prototype.** A PC (Python Flask + Socket.IO) talks the GVRET binary
  protocol over USB to an ESP32 flashed with [ESP32RET](https://github.com/collin80/ESP32RET),
  which puts the frames on the cluster's CAN bus at 500 kbps.
- **Lineage of the boost gauge:** this bench tool (ESP32RET/GVRET) →
  [MK7BoostGauge](https://github.com/ALagrandeur/MK7BoostGauge) (Raspberry Pi, archived) →
  [BOT32](https://github.com/ALagrandeur/BOT32) (ESP32, the in-car device). BOT32's README says
  its logic was *ported from mk7-cluster-bench-controller*.
- **Still a reference for BOT32:** `bot32/tools/verify_crc.py` uses [`webui/vw_mqb.py`](webui/vw_mqb.py)
  as its reference CRC implementation, and `bot32/tools/derive_bench_frames.py` writes its
  outputs into [`analysis/`](analysis/) here (they feed BOT32's `bench_frames` tables).
- **Backup "hub" (since 2026-07-27):** CAN notes and DBC files, capture-analysis scripts, the
  legacy `AMOLED_Remote/` project and [`MIGRATION.md`](MIGRATION.md) (new-PC guide for all
  the repos, in French).
- No live link with BOT32, BOT32-HALDEX or Remote32: no ESP-NOW, no shared protocol. The
  relationship is code and documentation heritage only.

## Contents

| Path | What it is | Status |
|---|---|---|
| [`webui/`](webui/) | Bench web UI: `server.py` (Flask + Socket.IO), `gvret.py`, `vw_mqb.py`, `static/` front-end. See [`webui/README.md`](webui/README.md). | working, dormant |
| `Start MK7 Cluster.bat` | Windows launcher for the web UI (see Quick start). | working |
| [`can_ids/`](can_ids/) | `mqb_can_ids.md` (CAN notes for the Golf, in French), `vw_mk7_cluster.dbc`, `obd2_universal.dbc` (for SavvyCAN). | reference |
| [`analysis/`](analysis/) | `find_hazards.py`, `replay_analyze.py` + `replay_report.md` (historical snapshot of one BOT32 capture), `bench_crc_tables.txt` / `bench_frame_rows.txt` (outputs of BOT32's `tools/derive_bench_frames.py`). | reference for BOT32 |
| [`AMOLED_Remote/`](AMOLED_Remote/) | ESP-NOW 12 V relay remote: ESP32-S3 AMOLED 1.8" **V1** board (SH8601/FT3168) + ESP32 DevKit relay receiver. Ancestor of [Remote32](https://github.com/ALagrandeur/Remote32) / `Recepteur_AMOLED`. | **legacy** (superseded) |
| `analyze_haldex*.py`, `eng*.py`, `hb*.py`, `run3*.py`, `final_verify.py`, `verify_fix.py` (16 scripts at the root) | One-off analyses of the Haldex-bus CAN captures from the X2 (`KEY ON ENGINE OFF`, `IDLE`, `run`, `run2`, `run3`; e.g. rear-axle engagement, handbrake pulls), made around the BOT32-HALDEX v0.7.x work (June 2026). They read local CSV captures through hard-coded Windows paths (the captures are not in Git). Not related to the cluster bench. | **legacy** (kept for reference) |
| [`MIGRATION.md`](MIGRATION.md) | How to set up all the repos on a new PC (in French). | maintained |
| [`LICENSE`](LICENSE) | MIT. | |

Nothing here has been moved or deleted; archiving the legacy items is pending the owner's
decision.

## Features (web UI)

- **🔆 Cluster wake** — Klemmen_Status_01 (0x3C0) with VW MQB CRC + counter. Required to wake
  the cluster from sleep (in addition to hardware Klemme 15).
- **System Context Bundle** — auto-fired with Wake to satisfy cluster's "alive ECU" checks
  (ESP_05/10/20, TSK_07, LH_EPS_01). Avoids speed timing out at 10s and brake-warning glitches.
  **Airbag_01 is intentionally never broadcast** (see safety policy).
- **⚙️ RPM tachometer** — 0-8000 RPM slider, drives Motor_04 (0x107) bytes 3-4 (LE, ÷3 RPM/tick).
- **🌡️ Coolant / Boost gauge override** — slider in either °C (50 … 130 °C, direct) or BAR
  absolute (0.3 … 2.0 bar, mapped onto 50 … 130 °C to skip the cluster's 80-110 °C neutral
  zone). The cluster sees Motor_09 (0x647) with the linear formula confirmed in r00li.
- **📡 Live UDS poll (vehicle-only)** — when connected to a running car, polls Engine ECU DID
  0x39C0 (real MAP, mbar) and 0x202C (real coolant, 0.1°C) for live readback; in live mode the
  gauge follows the real MAP. One-shot cluster ping (DID 0x22D0 on 0x714/0x77E).
- **🅿️ Gear MFA indicator** — P/R/N/D/S buttons, drives WBA_03 (0x394) byte 1 high nibble.
- **🎮 MFA steering wheel buttons** — 6 click-fired buttons (UP/DOWN/LEFT/RIGHT/OK/BACK), all on
  MFSW (0x5BF, 4 bytes). Each row's CAN ID and payload are **editable**. The
  **"Auto-enable required context"** button turns on Wake + Motor_Code_01 + Motor_04, which the
  cluster needs before it accepts MFSW.
- **💡 Dashboard lights & indicators** — 33 pre-filled rows (warnings, beams, blinkers, doors,
  TPMS, EPC, DPF, …) each with editable ON/OFF payload. Many are placeholders (ID 0x000 or
  all-zero payload) to identify with the sniffer. Add new rows for indicators you discover.
- **👁️ Bus Sniffer (read-only)** — every CAN ID seen on the bus with its rate (Hz), last
  payload and age. No TX; works in Bench and Vehicle mode, even disarmed.
- **🚗 Vehicle Mode** — single toggle that hard-blocks every broadcast except `coolant_loop`.
  Designed for safe deployment on a real running car (no conflict with real ECUs).
- **Frame log** with TX/RX filtering.
- **Raw CAN sender** — one-shot or periodic at configurable Hz (Bench mode only).
- **Reset config** — restores the code defaults. The configuration is saved in
  `webui/config.json` (git-ignored).

## Safety

The project is for hobbyist/educational use only. Multiple defensive layers:

1. **`FORBIDDEN_IDS = {0x040, 0x572}`** — hardcoded blocklist that intercepts at `send_can()`.
   The Airbag_01 (0x040) and Airbag_02 (0x572) IDs **cannot leave the device** regardless of
   any code path (loops, raw, scanner, MFA, lights). Never add to this list without a very
   good reason.
2. **Vehicle Mode** disables every broadcast except coolant when the device is on a real car.
3. **SAFETY ARMED** master toggle — periodic transmissions are blocked until the user explicitly
   arms the system. Auto-disarms on disconnect.
4. **Per-section enable** flags — every periodic broadcast is opt-in. Default safe state is OFF.
5. **Confirmation prompts** before destructive actions (Reset, enter Vehicle Mode).

## Architecture

```
Browser (HTML/JS) ←─WebSocket(socketio)─→ Python (Flask) ←─USB Serial─→ ESP32 (ESP32RET) ←─CAN─→ Cluster
```

- **Python backend** ([`webui/server.py`](webui/server.py)) — Flask + Flask-SocketIO. 13
  background threads (serial reader, two UDS pollers and one loop per periodic broadcast).
  pyserial speaks the GVRET binary protocol to the ESP32. Listens on `127.0.0.1:5000` only.
- **GVRET protocol** ([`webui/gvret.py`](webui/gvret.py)) — ports the binary frame format
  for ESP32RET (Collin Kidder).
- **VW MQB checksum** ([`webui/vw_mqb.py`](webui/vw_mqb.py)) — CRC8H2F + per-counter constants
  from openpilot's `mqbcan.py`. Self-test runnable via `python vw_mqb.py`.
- **Frontend** ([`webui/static/`](webui/static/)) — vanilla JS, no framework. Sliders compute
  the bytes locally and emit set_* events; backend periodic loops read state and emit `can_frame`
  events for the live frame log.

## Hardware

- ESP32 with [ESP32RET firmware](https://github.com/collin80/ESP32RET) (provides GVRET serial
  protocol over USB to a CAN transceiver; SavvyCAN-compatible). Get the firmware from collin80,
  not from this repo (a local `ESP32RET_Updater/` folder is git-ignored).
- CAN transceiver — Waveshare SN65HVD230 (3.3 V) tested.
- VW MK7 cluster (5G1 920 7xxB highline tested).
- 12 V power: pins 1 (Kl.30), 10 (Kl.31), and **16 (Kl.15 — ignition, MUST be powered)**, plus
  CAN H/L on pins 17/18 of the 18-pin connector.

## Quick start

1. Flash the ESP32 with ESP32RET (from collin80) and wire it to the cluster (see Hardware).
2. **Close SavvyCAN** — only one application can hold the COM port.
3. Start the server:

   ```bash
   cd webui
   pip install -r requirements.txt   # flask, flask-socketio, pyserial, simple-websocket
   python server.py
   # open http://127.0.0.1:5000/
   ```

   On Windows there's a launcher `Start MK7 Cluster.bat` that kills any previous server on port
   5000, installs deps, starts the server minimized, and opens the browser (`webui/run.bat`
   installs the deps and starts the server, without the browser step).
4. Pick the COM port and the CAN speed (500 kbps for the MQB powertrain bus; the server sends
   it to ESP32RET when you click **Connect**). The serial link is fixed at 1 Mbps (set in
   `webui/static/app.js`).
5. Switch the **SAFETY** banner to ARMED, then enable the sections you want (start with
   **Cluster Wake**).

Keyboard shortcuts: arrow keys = D-pad, Enter = OK, Esc/Backspace = BACK.

## Troubleshooting

| Symptom | What to check |
|---|---|
| "open failed" on Connect | SavvyCAN (or another program) still holds the COM port. |
| Cluster stays dark | Pin 16 (Kl.15) must have +12 V; no CAN message wakes the cluster without it. |
| Buttons / lights rejected with a "blocked" error | Not connected, SAFETY disarmed, or Vehicle Mode on (buttons, lights, wake and raw sender are bench-only). |
| MFA buttons do nothing | Enable the context first (**Auto-enable required context**, or Wake + engine context). |
| Server won't start: port 5000 busy | An old server is still running; `Start MK7 Cluster.bat` kills it for you. |
| Page loads but nothing reacts (no COM ports listed, Connect does nothing) | The page loads the Socket.IO client from `cdn.socket.io` (`webui/static/index.html`): the PC needs Internet access. |
| Saved settings lost after an update | `CONFIG_VERSION` (currently 8) was bumped in `server.py`; a `webui/config.json` with another version is ignored and the code defaults are loaded (the file is overwritten at the next save). |

Note: the Wake card text in the UI still lists Airbag_01 (0x040) in the context bundle; the
server does not send it (removed from the bundle and hard-blocked by `FORBIDDEN_IDS`).

## Related repositories

- [BOT32](https://github.com/ALagrandeur/BOT32) — in-car ESP32 device for the Golf (boost gauge,
  live data, web UI, Haldex mode control), with its own firmware bench mode.
- [BOT32-HALDEX](https://github.com/ALagrandeur/BOT32-HALDEX) (private) — ESP32-CAN-X2 on the
  Haldex bus.
- [Remote32](https://github.com/ALagrandeur/Remote32) (private) — Westfalia dashboard and the
  universal AMOLED remote (successor of `AMOLED_Remote/`).
- [MK7BoostGauge](https://github.com/ALagrandeur/MK7BoostGauge) — archived Raspberry Pi version.
- [OpenHaldex-C6-perso](https://github.com/ALagrandeur/OpenHaldex-C6-perso) (private) — unmodified
  OpenHaldex-C6 copy, reference only.

## Sources / credits

- [commaai/opendbc — vw_mqb.dbc](https://github.com/commaai/opendbc/blob/master/opendbc/dbc/vw_mqb.dbc)
  — message IDs and signal layouts.
- [commaai/openpilot — mqbcan.py](https://github.com/commaai/openpilot/blob/master/selfdrive/car/volkswagen/mqbcan.py)
  — VW MQB CRC8H2F algorithm and per-message constants.
- [r00li/CarCluster](https://github.com/r00li/CarCluster) — Arduino reference for Golf 7 MQB
  cluster control. The coolant magic bytes, MFSW button codes, and engine-context bundle all
  came from this project.
- [collin80/ESP32RET](https://github.com/collin80/ESP32RET) — the GVRET binary protocol firmware
  on the ESP32 side.

## License

MIT — see [LICENSE](LICENSE). No warranty; use at your own risk on your own hardware.
