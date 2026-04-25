# MK7 Cluster Bench Controller

PC-side web UI that talks to an ESP32 running **ESP32RET** firmware over USB serial,
using the GVRET binary protocol. Lets you drive a Golf MK7 cluster on a bench:

- Slider MAP (-1.0 … +2.5 BAR) → faked coolant temp byte → analog gauge becomes a boost gauge
- Gear selector P / R / N / D / S
- 6 steering-wheel buttons: UP / DOWN / LEFT / RIGHT / OK / BACK
- Editable CAN ID + payload config for each element (until the real IDs are reverse-engineered)
- Raw frame sender + live TX/RX log

## Quick start

1. Plug the ESP32 (running ESP32RET) into USB. Make sure SavvyCAN is **closed** — only one
   app can hold the COM port.
2. Double-click `run.bat`. It will pip-install deps and launch the server.
3. Open http://127.0.0.1:5000/ in your browser.
4. Select your COM port, click **Connect**.
5. Move the slider / press buttons. Watch the log to confirm frames are going out.

## Safety model (important)

**Nothing transmits periodically until you cross THREE gates:**

1. **Connect** — serial port to ESP32 must be open.
2. **Configure** — each broadcast section (coolant, gear, each button) has `id != 0x000`
   AND `enabled == true` in its config. Defaults are zero & disabled.
3. **Arm** — the master `SAFETY` toggle in the red banner at the top must be ON. Disconnecting
   automatically disarms.

A button press is only sent if all three are true for that specific button. A blocked press emits
an explicit error in the browser console and the frame log.

**On-demand actions remain available even when disarmed**: Cluster ping, Engine temp read,
Raw CAN sender. These are explicit single clicks — useful for safe sniffing/probing without
risking a runaway transmitter.

## Notes

- Default baud is 1 000 000 (1 Mbps) which is what ESP32RET uses. Don't lower it.
- The CAN bus speed is set by ESP32RET's own config (saved on the device). Verify in
  SavvyCAN that bus 0 is set to **500 kbps** before unplugging.
- The default CAN IDs are all **0x000 (unconfigured)** — see [`../can_ids/mqb_can_ids.md`](../can_ids/mqb_can_ids.md)
  for the methodology to identify real IDs from a SavvyCAN sniff, then enter them via the Config panel.
- Keyboard shortcuts in the browser: arrow keys = D-pad, Enter = OK, Esc/Backspace = BACK.

## Workflow once you have a real CAN log

1. Open the log in SavvyCAN, identify the IDs of interest (broadcast Motor_xx for coolant,
   Getriebe_xx for gear, MFL/GRA_xx for buttons).
2. In the webui Config panel, enter each ID and the byte/payload structure.
3. Tick `enabled` for the sections you want active.
4. Connect to ESP32 (with cluster on the bus).
5. Click **Cluster ping** first — confirms the bus is alive before any TX.
6. Toggle the **SAFETY** banner to ARMED.
7. Move sliders / press buttons.
