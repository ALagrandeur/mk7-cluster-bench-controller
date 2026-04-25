# MK7 Cluster Bench Controller

A Python web UI to control a **VW Golf MK7 instrument cluster** on a bench (or bridge a real
vehicle) over USB serial → ESP32 → CAN bus. The original goal of the project was to **repurpose
the analog coolant temperature gauge to display turbocharger boost pressure** in real time,
but the framework grew to expose most cluster functions documented in the openDBC and
[r00li/CarCluster](https://github.com/r00li/CarCluster) reverse-engineering work.

Tested cluster: **5G1 920 740B** (MK7 Alltrack 2017 highline, FIS+ MFA).

![safety banner](docs/screenshot-armed.png)

## Features

- **🌡️ Coolant / Boost gauge override** — slider in either °C (direct) or BAR absolute (mapped). The
  cluster sees Motor_09 (0x647) with the linear formula confirmed in r00li.
- **⚙️ RPM tachometer** — 0-8000 RPM slider, drives Motor_04 byte 3-4 (LE, ÷3 RPM/tick).
- **🅿️ Gear MFA indicator** — P/R/N/D/S buttons, drives WBA_03 (0x394) byte 1 high nibble.
- **🎮 MFA steering wheel buttons** — 6 click-fired buttons (UP/DOWN/LEFT/RIGHT/OK/BACK), all on
  MFSW (0x5BF, 4 bytes). Each row's CAN ID and payload are **editable** so unknown buttons can
  be identified by sniffing the real car's bus.
- **💡 Dashboard lights & indicators** — 30+ pre-filled rows (warnings, beams, blinkers, doors,
  TPMS, EPC, DPF, …) each with editable ON/OFF payload. Add new rows for indicators you discover.
- **🔆 Cluster wake** — Klemmen_Status_01 (0x3C0) with VW MQB CRC + counter. Required to wake
  the cluster from sleep (in addition to hardware Klemme 15).
- **System Context Bundle** — auto-fired with Wake to satisfy cluster's "alive ECU" checks
  (ESP_05/10/20, TSK_07, LH_EPS_01). Avoids speed timing out at 10s and brake-warning glitches.
  **Airbag_01 is intentionally never broadcast** (see safety policy).
- **📡 Live UDS poll (vehicle-only)** — when connected to a running car, polls Engine ECU DID
  0x39C0 (real MAP, mbar) and 0x202C (real coolant, 0.1°C) for live readback while the slider
  drives the gauge.
- **🚗 Vehicle Mode** — single toggle that hard-blocks every broadcast except `coolant_loop`.
  Designed for safe deployment on a real running car (no conflict with real ECUs).
- **Frame log** with TX/RX filtering.
- **Raw CAN sender** — one-shot or periodic at configurable Hz (Bench mode only).

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

- **Python backend** ([`webui/server.py`](webui/server.py)) — Flask + Flask-SocketIO. ~10
  background threads (one per periodic broadcast). pyserial speaks the GVRET binary protocol
  to the ESP32.
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
  not from this repo.
- CAN transceiver — Waveshare SN65HVD230 (3.3 V) tested.
- VW MK7 cluster (5G1 920 7xxB highline tested).
- 12 V power: pins 1 (Kl.30), 10 (Kl.31), and **16 (Kl.15 — ignition, MUST be powered)**, plus
  CAN H/L on pins 17/18 of the 18-pin connector.

## Quick start

```bash
cd webui
pip install -r requirements.txt
python server.py
# open http://127.0.0.1:5000/
```

On Windows there's a launcher `Start MK7 Cluster.bat` that kills any previous server on port
5000, installs deps, starts the server minimized, and opens the browser.

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
