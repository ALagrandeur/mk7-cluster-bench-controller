# MK7 Cluster Bench Controller — web UI

PC-side web UI that talks to an ESP32 running **ESP32RET** firmware over USB serial,
using the GVRET binary protocol. Lets you drive a Golf MK7 cluster (5G1 920 740B tested) on a
bench, or read/override the coolant gauge on a real car in Vehicle Mode.

> Part of [mk7-cluster-bench-controller](../README.md) (dormant bench tool, code unchanged
> since 2026-04-26). In-car use has moved to [BOT32](https://github.com/ALagrandeur/BOT32),
> which has its own firmware bench mode and its own web UI (different protocol, not GVRET).
> See the root README for the project map and hardware/wiring.

## Features

Cards in the page (`static/index.html`), top to bottom:

- **Connection bar** — COM port, **CAN bus speed** (125 k / 250 k / **500 k** default / 1 M),
  Connect / Disconnect.
- **Bench / Vehicle Mode banner** — Vehicle Mode lets only the coolant section broadcast and
  hides the bench-only cards (see Safety model).
- **SAFETY banner** — master arm switch.
- **🔆 Cluster Wake** — Klemmen_Status_01 (0x3C0, MQB CRC + counter, 10 Hz). Enabling it also
  fires the System Context Bundle (ESP_05, ESP_10, ESP_20, TSK_07, LH_EPS_01) at 10 Hz.
- **⚙️ RPM** — slider 0 … 8000 RPM → Motor_04 (0x107).
- **🌡️ Coolant / Boost Gauge** — Motor_09 (0x647) at 20 Hz. Two slider modes:
  **°C direct** (50 … 130 °C) or **BAR absolute** (0.3 … 2.0 bar, mapped linearly onto
  50 … 130 °C so the needle skips the cluster's 80-110 °C neutral zone). Enabling it in Bench
  mode also enables Motor_Code_01 (0x641), which the cluster needs as engine context.
  - *Advanced* panel: bar/temperature range, scale/offset, rate, and the **live UDS polls** —
    engine ECU MAP (DID 0x39C0) and real coolant (DID 0x202C) on 0x7E0/0x7E8, plus a one-shot
    **Ping cluster** (DID 0x22D0 on 0x714/0x77E). These are read-only diagnostic requests and
    are allowed in Vehicle Mode; in live mode the gauge follows the real MAP.
- **🅿️ Transmission** — P / R / N / D / S → WBA_03 (0x394).
- **🎮 MFA steering wheel buttons** — UP / DOWN / LEFT / RIGHT / OK / BACK on MFSW (0x5BF,
  4 bytes, r00li payloads), each with editable ID / length / press / release payloads.
  **Auto-enable required context** turns on Wake + Motor_Code_01 + Motor_04; without that
  context (LH_EPS_01 in the bundle) the cluster ignores MFSW.
- **💡 Dashboard lights & indicators** — 33 editable rows with ON/OFF payloads. Many are
  placeholders (ID 0x000 or all-zero payload); the Kombi_01 (0x30B) rows probably do not drive
  the lamps, because Kombi_01 is sent *by* the cluster. Identify the real sources with the
  sniffer.
- **👁️ Bus Sniffer** — read-only table of every ID seen (Hz, last payload, age, count), with
  filter, sort, snapshot and pause. Works in both modes, even disarmed.
- **📋 Frame log** — live TX/RX/BLOCKED frames.
- **Raw CAN sender** — one-shot or periodic (0.1 … 50 Hz; periodic needs SAFETY armed). Bench
  mode only.
- **Reset config** — back to the code defaults.

There is no speed card: the speed UI was removed and the backend `speed_loop` (ESP_21 0xFD)
cannot be enabled from the page.

## Quick start

1. Plug the ESP32 (running ESP32RET) into USB. Make sure SavvyCAN is **closed** — only one
   app can hold the COM port.
2. Double-click `run.bat` (or, from the repo root, `Start MK7 Cluster.bat`, which also opens the
   browser). Manual start: `pip install -r requirements.txt` then `python server.py`.
3. Open http://127.0.0.1:5000/ in your browser (the server listens on localhost only).
4. Select your COM port and the CAN speed (500 kbps for the MQB powertrain bus), click
   **Connect**.
5. Arm the **SAFETY** banner, enable the cards you need (Wake first on a bench), then move the
   sliders / press buttons. Watch the frame log to confirm frames are going out.

## Safety model (important)

**Nothing transmits periodically until you cross THREE gates:**

1. **Connect** — serial port to ESP32 must be open.
2. **Configure / enable** — each periodic section (wake, RPM, coolant, gear, …) must have a
   non-zero ID **and** its own ON toggle switched on. The IDs come pre-filled (see below), but
   every section is **disabled** by default.
3. **Arm** — the master `SAFETY` toggle in the red banner at the top must be ON. Disconnecting
   automatically disarms.

Click-fired actions (MFA buttons, lights) need Connect + Arm + a non-zero ID. A blocked action
is rejected with an explicit error message.

**Vehicle Mode** (for a real running car): only the coolant section may broadcast. Wake, system
context, RPM, speed, gear, brightness, MFA buttons, lights, the raw sender (one-shot and
periodic) and the backend ID scanner (no card in the page) are hard-blocked, and the
Motor_Code_01 auto-bundle is skipped (the real engine ECU already sends it). Entering Vehicle Mode asks for confirmation and switches
those sections off.

**Always blocked:** the airbag IDs 0x040 (Airbag_01) and 0x572 (Airbag_02) can never be sent
(`FORBIDDEN_IDS` in `server.py`), whatever the mode or the config.

**Available even when disarmed** (connected only): **Ping cluster** and the one-shot **Raw CAN
sender** (the latter only in Bench mode) — explicit single clicks, useful for safe probing
without risking a runaway transmitter — and the **live UDS polls** of the Advanced panel
(read-only diagnostic requests to the engine ECU).

## Default CAN IDs

The default configuration (`DEFAULT_CONFIG` in `server.py`, `CONFIG_VERSION = 8`) is pre-filled
with the IDs confirmed on the bench / from r00li/CarCluster and openDBC:

| Section | ID | Message |
|---|---|---|
| MFA buttons | 0x5BF | MFSW |
| Coolant / boost gauge | 0x647 | Motor_09 |
| Engine context | 0x641 | Motor_Code_01 |
| RPM / engine context | 0x107 | Motor_04 |
| Speed (no UI) | 0xFD + 0x31B | ESP_21 + ESP_24 |
| Gear | 0x394 | WBA_03 |
| Wake | 0x3C0 | Klemmen_Status_01 |
| Brightness (no UI card) | 0x5F0 | Dimmung_01 |
| UDS engine ECU | 0x7E0 / 0x7E8 | DIDs 0x39C0 (MAP), 0x202C (coolant) |
| UDS cluster | 0x714 / 0x77E | DID 0x22D0 (displayed coolant) |

Your edits are saved in `webui/config.json` (git-ignored). When `CONFIG_VERSION` changes in the
code, a saved file with another version is ignored and the code defaults are loaded (the file
is overwritten at the next save). Background on each ID:
[`../can_ids/mqb_can_ids.md`](../can_ids/mqb_can_ids.md) (confirmed IDs in its lower sections)
and [`../can_ids/vw_mk7_cluster.dbc`](../can_ids/vw_mk7_cluster.dbc).

## Notes

- The serial baud is fixed at 1 000 000 (1 Mbps) in `static/app.js`, which is what ESP32RET
  uses. Don't lower it.
- The page loads the Socket.IO client from `cdn.socket.io`: the PC needs Internet access,
  otherwise the page shows but nothing reacts (no COM ports listed).
- The CAN bus speed is **configured by `server.py` on Connect** (bus 0, from the selector in the
  header; ESP32RET also keeps it in its own settings). No need to set it in SavvyCAN first.
- Keyboard shortcuts in the browser: arrow keys = D-pad, Enter = OK, Esc/Backspace = BACK.
- The Wake card text still lists Airbag_01 (0x040) in the bundle; the server does not send it.

## Finding a new ID (sniffer workflow)

The main IDs are already confirmed. To identify an unknown lamp or button:

1. Connect the ESP32 to the car's bus, switch to **Vehicle Mode** and open the
   **Bus Sniffer** (it works even disarmed); take a **Snapshot**.
2. Trigger the function on the car (press the button, open the door, …) and look for the ID
   and byte that change. SavvyCAN logs can be used the same way.
3. Back on the bench, enter the ID / payload in the matching row and save.
4. Connect to the cluster, click **Ping cluster** to confirm the bus is alive, arm **SAFETY**
   and test.
