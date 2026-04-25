"""
MK7 cluster bench controller — PC-side web server.

- Talks to an ESP32 running ESP32RET firmware over USB serial using the GVRET binary protocol.
- Hosts a small web UI on http://127.0.0.1:5000/ with:
    * D-pad buttons (UP/DOWN/LEFT/RIGHT/OK/BACK) sent as one-shot CAN frames.
    * Three "gauge modes" for the analog coolant gauge:
        - "live"   : poll DID 0x39C0 (Saugrohrdruck) on engine ECU via UDS, use the live MAP.
        - "slider" : MAP value comes from the web slider (0..2 bar absolute).
        - "normal" : send a fixed normal coolant temperature (e.g. 90 °C).
      Mapping bar -> faked coolant byte is configurable.
    * Gear selector (P/R/N/D/S) sent periodically (~10 Hz).
    * Per-element CAN ID + payload config (editable until real IDs are reverse-engineered).

Run:
    pip install -r requirements.txt
    python server.py
Open http://127.0.0.1:5000/ in your browser.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import serial
import serial.tools.list_ports
from flask import Flask, send_from_directory, jsonify
from flask_socketio import SocketIO

import gvret
import vw_mqb


HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
CONFIG_PATH = HERE / "config.json"

app = Flask(__name__, static_folder=None)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# ---------- State ----------

@dataclass
class State:
    port: str | None = None
    baud: int = 1000000           # ESP32RET default USB baud
    can_speed: int = 500000       # CAN bitrate (configured on device side)
    bus: int = 0                  # which bus on the ESP32 to TX on
    connected: bool = False

    map_mode: str = "slider"      # "live" | "slider" | "normal"
    map_bar: float = 0.3          # current MAP (slider mode), bar absolute

    # Slider-driven values for the live broadcasts
    speed_kmh: float = 0.0        # speed slider (0..260 km/h)
    rpm: int = 1500               # RPM slider (0..8000 RPM)
    coolant_mode: str = "boost"   # "temp" or "boost" — drives slider interpretation in UI

    # Raw sender periodic mode
    raw_periodic_id: int = 0
    raw_periodic_data_hex: str = ""
    raw_periodic_extended: bool = False
    raw_periodic_rate_hz: float = 5.0
    raw_periodic_enabled: bool = False
    live_map_bar: float | None = None  # last MAP value parsed from UDS response
    live_map_ts: float = 0.0      # epoch time of last successful UDS read

    cluster_temp_byte: int | None = None   # last raw byte from cluster DID 0x22D0
    cluster_temp_ts: float = 0.0           # epoch time of last cluster ping response

    engine_temp_c: float | None = None     # last value from engine ECU DID 0x202C
    engine_temp_raw: int | None = None
    engine_temp_ts: float = 0.0

    gear: str = "P"
    last_error: str = ""

    # Master safety: when False, NO periodic TX happens regardless of per-element enable flags.
    # On-demand reads (cluster_ping, engine_temp_read, send_raw) still work — they're explicit clicks.
    armed: bool = False

    # Vehicle Mode — when True, ESP32 is connected to a REAL CAR, not a bench cluster.
    # Only the coolant section is allowed to broadcast (the boost-on-coolant feature). Everything
    # else (wake, system_context, RPM, speed, gear, MFA buttons, raw_periodic, scanner) is HARD
    # BLOCKED to prevent collisions/conflicts with the real ECUs already broadcasting on the bus.
    # The auto-bundle of engine_code with coolant is also disabled in vehicle mode (real engine
    # ECU already provides Motor_Code_01 heartbeat).
    vehicle_mode: bool = False

    # ID Scanner — sends ONE selected test frame at 5 Hz. User clicks to switch between
    # candidate IDs to find which one moves the gauge. scanner_id=0 = inactive.
    scanner_id: int = 0
    scanner_data_hex: str = ""
    scanner_label: str = ""

state = State()
state_lock = threading.Lock()

ser: serial.Serial | None = None
ser_lock = threading.Lock()
parser = gvret.GvretParser()

# Per-CAN-ID rolling 4-bit counter for VW MQB messages that need counter+checksum.
mqb_counters: dict[int, int] = {}
mqb_counters_lock = threading.Lock()


def next_mqb_counter(address: int) -> int:
    """Increment and return the rolling 4-bit counter for a given CAN ID."""
    with mqb_counters_lock:
        c = (mqb_counters.get(address, 0) + 1) & 0x0F
        mqb_counters[address] = c
        return c


# ---------- Config ----------
#
# All editable from the web UI. CAN IDs default to MQB candidates — verify with SavvyCAN.

# Bumped whenever DEFAULT_CONFIG changes structure / IDs / formulas in a way that should
# REPLACE the user's saved config.json on next start. Increment when defaults need to win.
# v3 = r00li/CarCluster Motor_09 coolant + Motor_Code_01/Motor_04 engine context
# v4 = added speed (ESP_21 + ESP_24) / fuel (Kombi_02), gear → WBA_03, buttons → MFSW r00li
# v5 = removed fuel (analog only on this cluster); fixed gear (byte 3 = 0 for P/R/N/D)
# v6 = REMOVED Airbag_01 from system context (safety) + added Vehicle Mode (coolant-only on real car)
# v7 = added "lights" section (~25 dashboard indicators with editable per-light config)
# v8 = wake_once now blocks in vehicle mode (was a safety hole) + UDS poll IDs/DIDs editable
CONFIG_VERSION = 8

BUTTON_NAMES = ["UP", "DOWN", "LEFT", "RIGHT", "OK", "BACK"]


def _empty_button_cfg() -> dict:
    """Fallback default for one button (used by safety-by-default until r00li values applied)."""
    return {
        "id": 0x5BF,            # MFSW MultiFunction Steering Wheel (r00li)
        "extended": False,
        "length": 4,            # MFSW is 4 bytes per r00li!
        "press_payload_hex": "00 00 00 40",
        "release_payload_hex": "00 00 00 40",
        "hold_ms": 30,
        "mqb_checksum": False,  # no CRC on MFSW per r00li
        "enabled": False,
    }


# r00li-confirmed MFSW press payloads. Pattern: byte0 = button code, byte2 = direction/sub, byte3=0x40.
# Release frame for all buttons: 00 00 00 40
BUTTON_DEFAULTS = {
    "UP":    {"press_payload_hex": "06 00 01 40"},   # MFA up
    "DOWN":  {"press_payload_hex": "06 00 0F 40"},   # MFA down
    "LEFT":  {"press_payload_hex": "03 00 01 40"},   # menu left
    "RIGHT": {"press_payload_hex": "02 00 01 40"},   # menu right
    "OK":    {"press_payload_hex": "07 00 01 40"},   # OK / select
    "BACK":  {"press_payload_hex": "23 00 01 40"},   # View button (cycles MFA pages, used as "back")
}


# Default dashboard lights / indicators list. Pre-filled with known CAN positions where possible
# (mainly Kombi_01 0x30B from openDBC). Unknown ones have id=0 so user fills them after sniffing
# with SavvyCAN. Each light has ON and OFF payload templates.
# Kombi_01 (0x30B, 8 bytes, no CRC) — byte 0 / byte 1 / byte 2 hold most warning lamp bits.
# Kombi_01 byte 1 nibble bas = counter (auto if mqb_checksum=True).
LIGHT_DEFAULTS = [
    # === Kombi_01 0x30B byte 0 — basic warnings ===
    {"name": "ABS Warning",       "id": 0x30B, "length": 8, "on_payload_hex": "01 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": True},
    {"name": "ESP Warning",       "id": 0x30B, "length": 8, "on_payload_hex": "02 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": True},
    {"name": "Brake System (BKL)","id": 0x30B, "length": 8, "on_payload_hex": "04 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": True},
    {"name": "Airbag Warning",    "id": 0x30B, "length": 8, "on_payload_hex": "08 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": True},
    {"name": "Steering Warning",  "id": 0x30B, "length": 8, "on_payload_hex": "20 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": True},
    {"name": "Glow Plug (Diesel)","id": 0x30B, "length": 8, "on_payload_hex": "40 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": True},
    # === Kombi_01 byte 1 / byte 2 ===
    {"name": "Oil Pressure SW",   "id": 0x30B, "length": 8, "on_payload_hex": "00 80 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": True},
    {"name": "Low Fuel",          "id": 0x30B, "length": 8, "on_payload_hex": "00 00 01 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": True},
    {"name": "Oil Pressure RED",  "id": 0x30B, "length": 8, "on_payload_hex": "00 00 40 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": True},
    {"name": "Handbrake",         "id": 0x30B, "length": 8, "on_payload_hex": "00 00 80 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": True},
    # === LICHT_VORNE_01 0x658 — front lights ===
    {"name": "High Beam",         "id": 0x658, "length": 8, "on_payload_hex": "00 40 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Low Beam",          "id": 0x658, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Front Fog",         "id": 0x658, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    # === LICHT_HINTEN_01 0x3D6 — rear lights ===
    {"name": "Rear Fog",          "id": 0x3D6, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    # === BLINKMODI_02 0x366 — turn signals ===
    {"name": "Turn Signal LEFT",  "id": 0x366, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Turn Signal RIGHT", "id": 0x366, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Hazard (both)",     "id": 0x366, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    # === DOOR_STATUS 0x583 — door open ===
    {"name": "Door FL Open",      "id": 0x583, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Door FR Open",      "id": 0x583, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Door RL Open",      "id": 0x583, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Door RR Open",      "id": 0x583, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Trunk Open",        "id": 0x583, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Hood Open",         "id": 0x583, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    # === Other indicators (unknown ID — fill via SavvyCAN sniff) ===
    {"name": "Seatbelt Warning",  "id": 0x000, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "TPMS Warning",      "id": 0x64A, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "EPC Warning",       "id": 0x000, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "DPF Warning",       "id": 0x000, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Check Engine",      "id": 0x000, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Battery Warning",   "id": 0x000, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Cruise Control",    "id": 0x000, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Service Interval",  "id": 0x000, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "Wash Fluid Low",    "id": 0x000, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
    {"name": "ESP OFF",           "id": 0x000, "length": 8, "on_payload_hex": "00 00 00 00 00 00 00 00", "off_payload_hex": "00 00 00 00 00 00 00 00", "hold_ms": 200, "mqb_checksum": False},
]


def _r00li_button_cfg(name: str) -> dict:
    """Build a per-button config preloaded with r00li-confirmed MFSW values."""
    cfg = _empty_button_cfg()
    cfg.update(BUTTON_DEFAULTS.get(name, {}))
    return cfg


DEFAULT_CONFIG = {
    # NOTE: all gauge/gear/button CAN IDs default to zero and "enabled: False" so that NOTHING
    # transmits until the user has explicitly identified the real IDs from a SavvyCAN sniff
    # AND ticked enabled AND armed the master switch. This is intentional safety.
    "coolant": {
        # Motor_09 = 0x647 (8 bytes), sender = Motor_Diesel_MQB.
        # 🟢 CONFIRMED on Golf 7 MQB cluster via r00li/CarCluster production code:
        #   https://github.com/r00li/CarCluster/blob/main/CarCluster/src/Clusters/VW_MQB/VWMQBCluster.cpp
        #
        # byte 0 is the coolant display value with LINEAR mapping:
        #   byte = map(temp_C, 50°C → 130°C, 0x80 → 0xED)
        #
        # Inverse (what webui computes): temp_C = raw * 0.7339 - 43.94
        #   0x80 (128) → 50°C
        #   0xB6 (182) → 90°C  (center/normal)
        #   0xED (237) → 130°C (max red zone)
        #
        # ⚠️ CRITICAL: bytes 1-7 MUST contain these "magic" values from r00li buffer init, otherwise
        # the cluster REJECTS the message and doesn't move the needle. Zeros do NOT work.
        #   {byte0=temp, byte1=0xFD, byte2=0xFF, byte3=0x7F, byte4=0x00, byte5=0x00, byte6=0x00, byte7=0xC1}
        #
        # Motor_09 has NO counter and NO CRC in r00li code — byte 0 is set directly.
        # Must be broadcast at 20 Hz (50ms cycle) alongside Motor_Code_01 (0x641) and Motor_04 (0x107)
        # as the engine-ECU-alive context. Alone it won't work.
        "id": 0x647,            # 🟢 Motor_09 (r00li/CarCluster confirmed)
        "extended": False,
        "length": 8,
        "byte_index": 0,        # coolant display value
        "scale": 0.7339,        # temp_C = raw * 0.7339 - 43.94  (inverse of map 50-130 → 0x80-0xED)
        "offset": -43.94,
        "other_bytes_hex": "FD FF 7F 00 00 00 C1",   # magic values from r00li motor09Buf init
        # Bar -> gauge mapping (skips cluster's neutral zone 80-110°C):
        "map_low_bar": 0.3,
        "map_high_bar": 2.0,
        "temp_low_c": 50.0,
        "temp_high_c": 130.0,
        "normal_temp_c": 90.0,
        "rate_hz": 20.0,        # r00li uses 20 Hz (50ms)
        "mqb_checksum": False,  # Motor_09 has neither counter nor CRC per r00li
        "enabled": False,       # safe-by-default
    },
    # Engine context broadcasts — REQUIRED alongside coolant for the cluster to trust it.
    # Sent at 20 Hz same as coolant. Derived from r00li/CarCluster sendMotor() function.
    "engine_code": {
        # Motor_Code_01 (0x641, 8 bytes) — engine ECU heartbeat with MQB CRC + counter.
        # r00li default buffer: {0x00, 0x00, 0x00, 0xE8, 0x03, 0x00, 0x00, 0x00}
        # Byte 1 upper nibble is 0x10 (per r00li: crc = (0x10 | seq) ^ 0xFF). Our code puts counter
        # in byte 1 low nibble, so total byte 1 = 0x10 | counter. We handle this via payload_hex
        # where byte 1 = 0x10, and the MQB CRC function overwrites nibble low with counter.
        "id": 0x641,            # Motor_Code_01
        "extended": False,
        "length": 8,
        # byte 0 = CRC (auto-computed), byte 1 = 0x10 | counter (auto-computed low nibble),
        # bytes 2-7 from r00li buffer
        "payload_hex": "00 10 00 E8 03 00 00 00",
        "rate_hz": 20.0,
        "mqb_checksum": True,   # Motor_Code_01 is in our MQB constants table (0x641: 0x47 x 16)
        "enabled": False,
    },
    "engine_rpm": {
        # Motor_04 (0x107, 8 bytes) — display RPM tachometer. No CRC, no counter (r00li confirmed).
        # Bytes 3-4 LE = MO_Anzeigedrehz: byte3 = (rpm/3) % 256, byte4 = (rpm/3) / 256.
        # The "template" payload below is the r00li static buffer; the server overwrites bytes 3-4
        # at TX time with the current state.rpm value (slider-driven).
        "id": 0x107,            # Motor_04
        "extended": False,
        "length": 8,
        "payload_hex": "00 00 00 00 00 00 00 00",   # bytes 3-4 overwritten by RPM slider
        "rate_hz": 20.0,
        "mqb_checksum": False,
        "enabled": False,
    },
    "speed": {
        # ESP_21 (0xFD, 8 bytes) — speed/distance broadcast that drives the speedometer needle.
        # bytes 4-5 LE = vSpeed = round(speed_kmh × 98.5)
        # MQB CRC + counter at byte 0 / byte 1 nibble bas (uses constant 0xD0|seq trick from r00li).
        # r00li initial buffer: {0x00, 0xD0, 0x1F, 0x80, 0xD8, 0x0D, 0x00, 0x00}
        #
        # IMPORTANT: r00li sends ESP_24 (0x31B) IN PARALLEL — it carries the "kombi speed"
        # (vSpeed × 1.35 at bytes 2-3) plus a distance-counter for the odometer at bytes 5-6.
        # Both are required to drive the speedometer cleanly. Our backend sends both from this
        # one config slot via the speed_loop.
        "id": 0xFD,             # ESP_21 (primary speed)
        "extended": False,
        "length": 8,
        # template — bytes 4-5 overwritten by speed slider
        "payload_hex": "00 D0 1F 80 D8 0D 00 00",
        "rate_hz": 20.0,
        "mqb_checksum": True,   # ESP_21 in MQB constants table
        "enabled": False,
        # Companion ESP_24 (sent in parallel by speed_loop):
        "esp24_id": 0x31B,
        "esp24_payload_hex": "00 00 00 00 00 01 00 00",  # bytes 2-3 + 5-6 overwritten
    },
    # NOTE: "fuel" removed in v5 — MK7 highline cluster reads fuel level via an ANALOG fuel
    # sender on a dedicated pin, not via CAN. r00li/CarCluster confirms this (uses a digipot,
    # not a CAN message). No software-only solution exists.
    "gear": {
        # WBA_03 (0x394, 8 bytes) — gateway → cluster, drives the gear indicator in the
        # top-right corner of the MFA display. Per r00li/CarCluster:
        #   byte 0             = CRC (auto)
        #   byte 1 high nibble = gear selector: 0x10=P, 0x20=R, 0x30=N, 0x40=D, 0x60=Manual
        #   byte 1 low nibble  = counter (auto)
        #   byte 3             = M-mode gear number (1-9) — MUST be 0 for P/R/N/D otherwise
        #                        cluster shows "P4", "D2", etc. instead of just the letter
        #   bytes 2,4-7        = template (kept as r00li default)
        # We hardcode the gear→(selector, m_gear) mapping in build_gear_frame to handle byte 3
        # correctly (the old generic "values" dict approach didn't allow per-gear byte 3 control).
        "id": 0x394,
        "extended": False,
        "length": 8,
        # Template for bytes 2,4,5,6,7 (bytes 0,1,3 set dynamically by build_gear_frame).
        "template_hex": "00 00 00 00 04 00 00 00",
        "rate_hz": 20.0,
        "mqb_checksum": True,   # WBA_03 is in MQB constants table (r00li constants)
        "enabled": False,
    },
    # Per-button independent config — preloaded with r00li MFSW (0x5BF, 4 bytes) values.
    "buttons": {name: _r00li_button_cfg(name) for name in BUTTON_NAMES},
    # Dashboard lights / indicators — list (order preserved) of light configs.
    "lights": [json.loads(json.dumps(L)) for L in LIGHT_DEFAULTS],
    # Cluster wake / Klemme 15 simulation = Klemmen_Status_01 (CAN ID 0x3C0, 4 bytes).
    # Source: openDBC vw_mqb.dbc — "BO_ 960 Klemmen_Status_01: 4 Gateway_MQB".
    # Independently confirmed by community sources (multiple bench-cluster projects).
    # Although openDBC lists Airbag/BMS/Motor as receivers, the cluster on bench also relies on
    # this message to know the ignition is "on" (alongside the hardware Kl.15 line).
    #
    # Layout (from openDBC):
    #   byte 0       = CHECKSUM (custom MQB CRC8H2F + constant 0xC3 — auto-computed)
    #   byte 1 nibble bas = COUNTER (auto-incremented 0..15)
    #   byte 2 bit 0 = ZAS_Kl_S   (start)
    #   byte 2 bit 1 = ZAS_Kl_15  (ignition — THE bit that signals "car is on")
    #   byte 2 bit 2 = ZAS_Kl_X   (accessory)
    #   byte 2 bit 3 = ZAS_Kl_50  (crank)
    #   byte 3       = unused
    #
    # Default payload byte 2 = 0x03 sets BOTH Kl.15 AND Kl.S (= ignition + start switch).
    #
    # ⚠️ IMPORTANT: hardware Kl.15 (+12V on pin 16 of the 18-pin connector for 5G1 920 7xxB)
    # is the PRIMARY wake mechanism. Without it, no CAN message reaches an awake cluster.
    # This message is the secondary "keep-alive" sent at ~10 Hz on the bus.
    "wake": {
        "id": 0x3C0,            # 🟢 openDBC — Klemmen_Status_01 (also confirmed by community)
        "extended": False,
        "length": 4,
        "payload_hex": "00 00 03 00",   # byte 0/1 overwritten by checksum/counter; byte 2 = Kl.15+Kl.S
        "rate_hz": 10.0,
        "mqb_checksum": True,   # has both counter and custom MQB CRC (in constants table)
        "enabled": False,       # safe-by-default; user must enable + arm explicitly
    },
    # Engine context = Motor_04 (CAN ID 0x107, 8 bytes). CONFIRMED on bench: byte 3 affects
    # the cluster's RPM tachometer needle. Sending this periodically tells the cluster
    # "the engine is running at X RPM" — likely required before the coolant gauge will move.
    #
    # Per openDBC vw_mqb.dbc:
    #   bits 24-35 (bytes 3-4 LE, 12-bit) = MO_Anzeigedrehz (displayed RPM, formula raw * 3 RPM/tick)
    #   bits 39-47 (bytes 4-5)            = MO_Ladedruck (boost pressure, raw * 0.01 bar)
    #   bits 8-11  (byte 1 nibble bas)    = MO_Istgang (current gear)
    #   bits 12-15 (byte 1 nibble haut)   = MO_Sollgang (target gear)
    #   bits 16-23 (byte 2)               = MO_Oeldruck (oil pressure, raw * 0.04 bar)
    # No counter, no MQB checksum (Motor_04 not in constants table).
    #
    # Default payload: byte 3=0x35, byte 4=0x05 → 12-bit value = 0x535 = 1333 → ~4000 RPM.
    # Calibrate empirically: cluster's actual scale may differ from openDBC formula.
    "rpm": {
        "id": 0x107,            # 🟢 Motor_04 — CONFIRMED on bench
        "extended": False,
        "length": 8,
        "payload_hex": "00 00 00 35 05 00 00 00",
        "rate_hz": 10.0,
        "mqb_checksum": False,
        "enabled": False,
    },
    # Cluster brightness = Dimmung_01 (CAN ID 0x5F0, 8 bytes).
    # Source: openDBC vw_mqb.dbc — "BO_ 1520 Dimmung_01: 8 Gateway_MQB".
    # Tells the cluster what brightness to use for the analog needles, MFA backlight, etc.
    # Without this message, the cluster typically defaults to MAXIMUM brightness — so this is
    # only required if you want to dim, or to suppress potential errors / suit night use.
    # Layout:
    #   byte 0 = DI_KL_58xd (raw control source, 0-253)
    #   byte 1 = DI_KL_58xs (target dim percent, 0-100)        ← THE brightness byte
    #   byte 1 bit 7 = DI_Display_Nachtdesign (night design flag)
    #   byte 2 = DI_KL_58xt (actual dim percent, 0-100)
    #   bytes 3-4 = DI_Fotosensor (photo sensor reading, 16-bit)
    #   bytes 5-7 = unused
    # Default 100% day mode: byte 1 = 0x64, byte 2 = 0x64. Byte 1 bit 7 stays 0 (day design).
    # No counter, no MQB checksum on this message.
    "brightness": {
        "id": 0x5F0,            # 🟢 openDBC — Dimmung_01
        "extended": False,
        "length": 8,
        "payload_hex": "00 64 64 00 00 00 00 00",
        "rate_hz": 5.0,         # brightness changes slowly, 5 Hz is plenty
        "mqb_checksum": False,
        "enabled": False,
    },
    "uds": {
        # UDS poller for "live" MAP mode. Confirmed from an Alltrack 2017 OBD log.
        "request_id": 0x7E0,    # tester -> engine ECU
        "response_id": 0x7E8,   # engine ECU -> tester
        "did": 0x39C0,          # Saugrohrdruck (intake manifold absolute pressure, mbar)
        "rate_hz": 10.0,        # poll rate
        "stale_after_s": 1.0,   # if no response in this long, mark live MAP stale
    },
    "cluster_ping": {
        # Aliveness probe for the instrument cluster. Confirmed from an Alltrack 2017 log.
        "request_id": 0x714,    # tester -> cluster (J285)
        "response_id": 0x77E,   # cluster -> tester
        "did": 0x22D0,          # engine coolant temp (as displayed by the cluster)
        # Formula candidates: byte * 0.75 (~89.25 rounded), or byte - 29 (exact 90).
        # Defaulting to byte * 0.75; user can change in the UI once verified at multiple temps.
        "scale": 0.75,
        "offset": 0.0,
    },
    "engine_temp": {
        # Live engine coolant temperature poller (real value from engine ECU).
        # Confirmed Alltrack 2017: DID 0x202C returns 2 bytes BE in 0.1 °C units.
        "request_id": 0x7E0,
        "response_id": 0x7E8,
        "did": 0x202C,
        "scale": 0.1,           # °C = (B1*256 + B2) * scale + offset
        "offset": 0.0,
        "rate_hz": 5.0,         # poll rate when enabled
        "auto_poll": False,     # toggle from UI
        "stale_after_s": 2.0,
    },
}


def deep_merge_defaults(saved: dict, defaults: dict) -> dict:
    """Recursively fill missing keys in `saved` with values from `defaults`. Returns saved."""
    for k, v in defaults.items():
        if k not in saved:
            saved[k] = json.loads(json.dumps(v))
        elif isinstance(v, dict) and isinstance(saved[k], dict):
            deep_merge_defaults(saved[k], v)
    return saved


def _fresh_default_config() -> dict:
    """Deep-copy DEFAULT_CONFIG and stamp the current version into it."""
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    cfg["_config_version"] = CONFIG_VERSION
    return cfg


def load_config() -> dict:
    """Load config.json, but reset to defaults if version mismatch (defaults win)."""
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if cfg.get("_config_version") == CONFIG_VERSION:
                return deep_merge_defaults(cfg, DEFAULT_CONFIG)
            print(f"[config] saved version {cfg.get('_config_version')} != current {CONFIG_VERSION} — resetting to defaults")
        except Exception as e:
            print(f"[config] failed to load existing config ({e}) — resetting to defaults")
    return _fresh_default_config()


def save_config(cfg: dict):
    cfg["_config_version"] = CONFIG_VERSION
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


config: dict = load_config()
config_lock = threading.Lock()


# ---------- Helpers ----------

def parse_hex_bytes(s: str, expected_len: int | None = None) -> bytes:
    parts = [p for p in s.replace(",", " ").split() if p]
    out = bytearray(int(p, 16) & 0xFF for p in parts)
    if expected_len is not None:
        if len(out) > expected_len:
            out = out[:expected_len]
        while len(out) < expected_len:
            out.append(0x00)
    return bytes(out)


def map_bar_to_temp(map_bar: float, cfg: dict) -> float:
    lo_bar, hi_bar = cfg["map_low_bar"], cfg["map_high_bar"]
    lo_t, hi_t = cfg["temp_low_c"], cfg["temp_high_c"]
    if hi_bar == lo_bar:
        return lo_t
    t = (map_bar - lo_bar) / (hi_bar - lo_bar)
    t = max(0.0, min(1.0, t))
    return lo_t + t * (hi_t - lo_t)


def temp_c_to_raw(temp_c: float, cfg: dict) -> int:
    raw = (temp_c - cfg["offset"]) / cfg["scale"] if cfg["scale"] else 0
    return max(0, min(255, int(round(raw))))


def build_coolant_payload(temp_c: float, cfg: dict) -> tuple[int, bytes]:
    raw = temp_c_to_raw(temp_c, cfg)
    length = int(cfg["length"])
    payload = bytearray(length)
    fill = parse_hex_bytes(cfg.get("other_bytes_hex", ""), expected_len=max(0, length - 1))
    j = 0
    for i in range(length):
        if i == cfg["byte_index"]:
            payload[i] = raw
        else:
            payload[i] = fill[j] if j < len(fill) else 0
            j += 1
    return int(cfg["id"]), bytes(payload)


# r00li/CarCluster gear mapping for WBA_03 (0x394):
# Returns (byte 1 selector nibble, byte 3 manual-gear-number).
# For P/R/N/D the M-gear must be 0 (cluster appends it to the letter otherwise → "P4", "D4"...).
WBA03_GEAR_MAP = {
    "P": (0x10, 0),
    "R": (0x20, 0),
    "N": (0x30, 0),
    "D": (0x40, 0),
    "S": (0x50, 0),   # 0x50 = "S" letter (sport mode). 0x60 is manual mode (shows gear digit).
}


def build_gear_frame(gear: str, cfg: dict) -> tuple[int, bytes]:
    """Build WBA_03 frame for a given gear position. byte 1 high nibble = selector, byte 3 = M-gear."""
    length = int(cfg["length"])
    template = parse_hex_bytes(cfg.get("template_hex", ""), expected_len=length)
    payload = bytearray(template)
    selector, m_gear = WBA03_GEAR_MAP.get(gear, (0, 0))
    payload[1] = (selector & 0xF0) | (payload[1] & 0x0F)   # high nibble = selector, low nibble = counter (auto)
    payload[3] = m_gear & 0xFF
    return int(cfg["id"]), bytes(payload)


def build_button_frames(button_cfg: dict) -> tuple[int, bytes, bytes]:
    """For a single per-button config, return (can_id, press_bytes, release_bytes)."""
    length = int(button_cfg["length"])
    press = parse_hex_bytes(button_cfg.get("press_payload_hex", ""), expected_len=length)
    release = parse_hex_bytes(button_cfg.get("release_payload_hex", ""), expected_len=length)
    return int(button_cfg["id"]), press, release


def build_uds_read_did_payload(did: int) -> bytes:
    """ISO-TP single frame: ReadDataByIdentifier(did)."""
    return bytes([0x03, 0x22, (did >> 8) & 0xFF, did & 0xFF, 0x00, 0x00, 0x00, 0x00])


def apply_mqb_checksum_if_needed(can_id: int, payload: bytes, cfg: dict) -> bytes:
    """Apply VW MQB protocol fields based on what the message needs.

    MQB messages on the bus use one of three patterns:
      A) Counter (4-bit, byte 1 low nibble) + custom CRC8H2F checksum (byte 0)
         e.g. Klemmen_Status_01, Motor_14, GRA_ACC_01 — IDs in the constants table.
      B) Counter only (byte 1 low nibble), no checksum at byte 0 (byte 0 holds data)
         e.g. Kombi_01 (0x30B) — gateway-to-cluster lamp/status message.
      C) Neither (raw payload).

    cfg.mqb_checksum=True means "do whatever this ID needs":
      - in the constants table → A (counter + checksum)
      - not in the constants table but len >= 2 → B (counter only at byte 1 low nibble)
    cfg.mqb_checksum=False → C (untouched).
    """
    if not cfg.get("mqb_checksum"):
        return payload
    counter = next_mqb_counter(can_id)
    if vw_mqb.has_mqb_checksum(can_id):
        return vw_mqb.apply_counter_and_checksum(can_id, payload, counter)
    if len(payload) < 2:
        return payload
    out = bytearray(payload)
    out[1] = (out[1] & 0xF0) | (counter & 0x0F)
    return bytes(out)


# ---------- Serial I/O ----------

def serial_open(port: str, baud: int, can_speed: int = 500000) -> str:
    global ser
    with ser_lock:
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass
            ser = None
        try:
            ser = serial.Serial(port, baudrate=baud, timeout=0.05, write_timeout=0.5)
        except Exception as e:
            return f"open failed: {e}"
        # Best-effort: switch device into binary mode (no-op if already binary)
        try:
            ser.write(bytes([gvret.CMD_ENABLE_BINARY_MODE]))
            ser.flush()
        except Exception:
            pass
        # Configure CAN bus 0 to the requested speed (default 500 kbps for VW MQB Powertrain).
        # ESP32RET also persists this setting in NVS, so this is idempotent across runs.
        try:
            setup_frame = gvret.build_setup_canbus(
                bus0_speed=can_speed, bus0_enabled=True, bus0_listen_only=False,
                bus1_speed=0,
            )
            ser.write(setup_frame)
            ser.flush()
        except Exception as e:
            with state_lock:
                state.last_error = f"can-speed setup failed: {e}"
    with state_lock:
        state.port = port
        state.baud = baud
        state.can_speed = can_speed
        state.connected = True
        state.last_error = ""
    return ""


def serial_close():
    global ser
    with ser_lock:
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass
            ser = None
    with state_lock:
        state.connected = False
        # Auto-disarm on disconnect — user must re-arm consciously after reconnecting.
        state.armed = False
        # Stop the scanner too — no point broadcasting to a dead port.
        state.scanner_id = 0
        state.scanner_label = ""


def serial_write(data: bytes) -> bool:
    with ser_lock:
        if ser is None:
            return False
        try:
            ser.write(data)
            return True
        except Exception as e:
            with state_lock:
                state.last_error = f"write failed: {e}"
            return False


def send_can(can_id: int, data: bytes, *, bus: int | None = None, extended: bool | None = None,
             tag: str = "tx"):
    # SAFETY: hard blocklist for IDs that must never be transmitted (airbag, etc.). Cannot be
    # bypassed by any code path — if it's in FORBIDDEN_IDS, nothing leaves the box.
    if can_id in FORBIDDEN_IDS:
        socketio.emit("can_frame", {
            "dir": "BLOCKED", "tag": f"FORBIDDEN:{tag}",
            "id": f"0x{can_id:X}", "bus": bus or 0,
            "data": " ".join(f"{b:02X}" for b in data), "ts": time.time(),
        })
        return
    if bus is None:
        bus = state.bus
    frame_bytes = gvret.build_can_frame(can_id, data, bus=bus, extended=extended)
    ok = serial_write(frame_bytes)
    socketio.emit("can_frame", {
        "dir": "TX" if ok else "TX-FAIL",
        "tag": tag,
        "id": f"0x{can_id:X}",
        "bus": bus,
        "data": " ".join(f"{b:02X}" for b in data),
        "ts": time.time(),
    })


# ---------- UDS response handling (extracts live MAP) ----------

def _parse_uds_single_frame(data: bytes) -> tuple[int, int, bytes] | None:
    """Decode a UDS positive single-frame response. Returns (service_id, did, value_bytes) or None."""
    if len(data) < 4:
        return None
    if (data[0] & 0xF0) != 0x00:
        return None  # not a single frame
    iso_len = data[0] & 0x0F
    if iso_len + 1 > len(data):
        return None
    sid = data[1]
    if sid < 0x40:
        return None  # not a positive response
    did = (data[2] << 8) | data[3]
    value = bytes(data[4:1 + iso_len])
    return sid, did, value


def maybe_parse_uds_responses(can_id: int, data: bytes):
    """Inspect a received frame: if it's a known UDS response we care about, update state."""
    with config_lock:
        ucfg = config.get("uds", {})
        ccfg = config.get("cluster_ping", {})
        ecfg = config.get("engine_temp", {})

    parsed = _parse_uds_single_frame(data)
    if not parsed:
        return
    sid, did, value = parsed
    if sid != 0x62:  # only ReadDataByIdentifier responses
        return

    # Engine ECU response with MAP DID
    if can_id == int(ucfg.get("response_id", 0x7E8)) and did == int(ucfg.get("did", 0x39C0)):
        if len(value) >= 2:
            raw = (value[0] << 8) | value[1]
            bar = raw / 1000.0
            with state_lock:
                state.live_map_bar = bar
                state.live_map_ts = time.time()
            socketio.emit("live_map", {"bar": bar, "raw": raw, "ts": state.live_map_ts})

    # Cluster response with coolant-temp DID
    if can_id == int(ccfg.get("response_id", 0x77E)) and did == int(ccfg.get("did", 0x22D0)):
        if len(value) >= 1:
            raw = value[0]
            temp_c = raw * float(ccfg.get("scale", 0.75)) + float(ccfg.get("offset", 0.0))
            with state_lock:
                state.cluster_temp_byte = raw
                state.cluster_temp_ts = time.time()
            socketio.emit("cluster_ping_response", {
                "raw": raw, "temp_c": temp_c, "ts": state.cluster_temp_ts,
            })

    # Engine ECU response with real coolant-temp DID
    if can_id == int(ecfg.get("response_id", 0x7E8)) and did == int(ecfg.get("did", 0x202C)):
        if len(value) >= 2:
            raw = (value[0] << 8) | value[1]
            temp_c = raw * float(ecfg.get("scale", 0.1)) + float(ecfg.get("offset", 0.0))
            with state_lock:
                state.engine_temp_c = temp_c
                state.engine_temp_raw = raw
                state.engine_temp_ts = time.time()
            socketio.emit("engine_temp_response", {
                "raw": raw, "temp_c": temp_c, "ts": state.engine_temp_ts,
            })


# ---------- Reader thread ----------

def reader_loop():
    while True:
        time.sleep(0.005)
        with ser_lock:
            s = ser
            if s is None:
                continue
            try:
                n = s.in_waiting
                chunk = s.read(n) if n else b""
            except Exception:
                chunk = b""
        if chunk:
            for f in parser.feed(chunk):
                socketio.emit("can_frame", {
                    "dir": "RX",
                    "tag": "rx",
                    "id": f"0x{f['id']:X}",
                    "bus": f["bus"],
                    "data": " ".join(f"{b:02X}" for b in f["data"]),
                    "ts": time.time(),
                })
                maybe_parse_uds_responses(f["id"], f["data"])


# ---------- Periodic senders ----------

def coolant_loop():
    """Send the (faked) coolant temp at the configured rate, source depending on map_mode.
    Gated by: state.armed AND coolant.enabled AND state.connected AND coolant.id != 0."""
    while True:
        with config_lock:
            cfg = config["coolant"]
            ucfg = config["uds"]
        rate_hz = float(cfg.get("rate_hz", 10.0)) or 10.0

        if state.armed and cfg.get("enabled") and state.connected and int(cfg.get("id", 0)) != 0:
            with state_lock:
                mode = state.map_mode
                slider_bar = state.map_bar
                live_bar = state.live_map_bar
                live_ts = state.live_map_ts

            if mode == "normal":
                temp_c = float(cfg.get("normal_temp_c", 90.0))
                tag = "coolant:normal"
            elif mode == "live":
                stale = (time.time() - live_ts) > float(ucfg.get("stale_after_s", 1.0))
                if live_bar is None or stale:
                    # No live reading yet — fall back to "min" of the bar range so the gauge
                    # parks at cold rather than swinging to a misleading value.
                    temp_c = float(cfg["temp_low_c"])
                    tag = "coolant:live(stale)"
                else:
                    temp_c = map_bar_to_temp(live_bar, cfg)
                    tag = "coolant:live"
            else:  # "slider"
                temp_c = map_bar_to_temp(slider_bar, cfg)
                tag = "coolant:slider"

            cid, data = build_coolant_payload(temp_c, cfg)
            data = apply_mqb_checksum_if_needed(cid, data, cfg)
            send_can(cid, data, tag=tag)

        time.sleep(max(0.02, 1.0 / rate_hz))


def gear_loop():
    """WBA_03 gear indicator (top-right of MFA). BENCH mode only — blocked in vehicle mode."""
    while True:
        with config_lock:
            cfg = config["gear"]
        rate_hz = float(cfg.get("rate_hz", 20.0)) or 20.0
        if state.armed and cfg.get("enabled") and state.connected and int(cfg.get("id", 0)) != 0 and not state.vehicle_mode:
            with state_lock:
                gear = state.gear
            cid, data = build_gear_frame(gear, cfg)
            data = apply_mqb_checksum_if_needed(cid, data, cfg)
            send_can(cid, data, tag=f"gear:{gear}")
        time.sleep(max(0.02, 1.0 / rate_hz))


def uds_poll_loop():
    """Poll DID for live MAP — only when in 'live' mode and connected."""
    while True:
        with state_lock:
            mode = state.map_mode
            connected = state.connected
        with config_lock:
            ucfg = config["uds"]
        rate_hz = float(ucfg.get("rate_hz", 10.0)) or 10.0

        if mode == "live" and connected:
            payload = build_uds_read_did_payload(int(ucfg["did"]))
            send_can(int(ucfg["request_id"]), payload, tag="uds:read_map")

        time.sleep(max(0.05, 1.0 / rate_hz))


def wake_loop():
    """Periodic cluster wake-up (Klemmen_Status_01). BENCH mode only — blocked in vehicle mode
    (real gateway already broadcasts Klemmen_Status_01, our duplicate would conflict)."""
    while True:
        with config_lock:
            cfg = config["wake"]
        rate_hz = float(cfg.get("rate_hz", 10.0)) or 10.0
        if state.armed and cfg.get("enabled") and state.connected and int(cfg.get("id", 0)) != 0 and not state.vehicle_mode:
            cid = int(cfg["id"])
            length = int(cfg.get("length", 4))
            payload = parse_hex_bytes(cfg.get("payload_hex", ""), expected_len=length)
            payload = apply_mqb_checksum_if_needed(cid, payload, cfg)
            send_can(cid, payload, extended=bool(cfg.get("extended")), tag="wake")
        time.sleep(max(0.02, 1.0 / rate_hz))


def scanner_loop():
    """ID Scanner. BENCH mode only — blocked in vehicle mode."""
    while True:
        with state_lock:
            cid = state.scanner_id
            data_hex = state.scanner_data_hex
            label = state.scanner_label
            armed = state.armed
            connected = state.connected
            vehicle = state.vehicle_mode
        if armed and connected and cid != 0 and not vehicle:
            payload = parse_hex_bytes(data_hex, expected_len=8)
            send_can(cid, payload, tag=f"scan:{label}")
        time.sleep(0.2)  # 5 Hz


def brightness_loop():
    """Dimmung_01 brightness. BENCH mode only — blocked in vehicle mode (real BCM controls brightness)."""
    while True:
        with config_lock:
            cfg = config["brightness"]
        rate_hz = float(cfg.get("rate_hz", 5.0)) or 5.0
        if state.armed and cfg.get("enabled") and state.connected and int(cfg.get("id", 0)) != 0 and not state.vehicle_mode:
            cid = int(cfg["id"])
            length = int(cfg.get("length", 8))
            payload = parse_hex_bytes(cfg.get("payload_hex", ""), expected_len=length)
            payload = apply_mqb_checksum_if_needed(cid, payload, cfg)
            send_can(cid, payload, extended=bool(cfg.get("extended")), tag="brightness")
        time.sleep(max(0.05, 1.0 / rate_hz))


def engine_code_loop():
    """Motor_Code_01 (0x641) heartbeat. BENCH mode only — blocked in vehicle mode
    (real engine ECU sends Motor_Code_01 already)."""
    while True:
        with config_lock:
            cfg = config["engine_code"]
        rate_hz = float(cfg.get("rate_hz", 20.0)) or 20.0
        if state.armed and cfg.get("enabled") and state.connected and int(cfg.get("id", 0)) != 0 and not state.vehicle_mode:
            cid = int(cfg["id"])
            length = int(cfg.get("length", 8))
            payload = parse_hex_bytes(cfg.get("payload_hex", ""), expected_len=length)
            payload = apply_mqb_checksum_if_needed(cid, payload, cfg)
            send_can(cid, payload, extended=bool(cfg.get("extended")), tag="engine_code")
        time.sleep(max(0.02, 1.0 / rate_hz))


# System context heartbeats — bench-only "system alive" messages so the cluster doesn't invalidate
# speed/MFSW. ⚠️ NEVER includes Airbag_01 (0x040) — explicit safety policy from user. Airbag system
# is too critical to risk any bus-spoofing of its messages.
# Sources: r00li/CarCluster initial buffers + openpilot constants.
# These ONLY fire in BENCH mode (vehicle_mode = False) so they cannot conflict with real ECUs on a car.
SYSTEM_CONTEXT_BROADCASTS = [
    # Airbag_01 (0x040) DELIBERATELY EXCLUDED — safety policy. Never re-add.
    {"id": 0x106, "name": "ESP_05",     "payload_hex": "00 00 00 00 00 00 00 00"},
    {"id": 0x116, "name": "ESP_10",     "payload_hex": "00 00 00 00 00 00 00 00"},
    {"id": 0x65D, "name": "ESP_20",     "payload_hex": "00 30 2B 12 00 00 B4 79"},
    {"id": 0x31E, "name": "TSK_07",     "payload_hex": "CA EF 3F 00 00 00 00 40"},
    {"id": 0x32A, "name": "LH_EPS_01",  "payload_hex": "4B 08 00 00 02 02 00 00"},
]

# Hard-coded blacklist of CAN IDs that CANNOT be transmitted regardless of mode/config.
# This is the absolute last line of defense against accidentally writing to safety-critical ECUs.
FORBIDDEN_IDS = {
    0x040,  # Airbag_01 — airbag system status. Never spoof.
    0x572,  # Airbag_02 — also airbag.
    # Add other safety-critical IDs here if needed.
}


def system_context_loop():
    """Auto-fires the system-alive heartbeats at 10 Hz when wake is enabled (BENCH mode only).
    Cluster needs these to NOT invalidate speed/brake/MFSW logic. NEVER fires in vehicle mode."""
    fake_cfg = {"mqb_checksum": True}
    while True:
        with config_lock:
            wake_enabled = config.get("wake", {}).get("enabled", False)
        if state.armed and wake_enabled and state.connected and not state.vehicle_mode:
            for msg in SYSTEM_CONTEXT_BROADCASTS:
                payload = parse_hex_bytes(msg["payload_hex"], 8)
                payload = apply_mqb_checksum_if_needed(msg["id"], payload, fake_cfg)
                send_can(msg["id"], payload, tag=f"ctx:{msg['name']}")
        time.sleep(0.1)


def engine_rpm_loop():
    """Motor_04 (0x107) RPM. BENCH mode only — blocked in vehicle mode (real engine sends RPM)."""
    while True:
        with config_lock:
            cfg = config["engine_rpm"]
        rate_hz = float(cfg.get("rate_hz", 20.0)) or 20.0
        if state.armed and cfg.get("enabled") and state.connected and int(cfg.get("id", 0)) != 0 and not state.vehicle_mode:
            cid = int(cfg["id"])
            length = int(cfg.get("length", 8))
            payload = bytearray(parse_hex_bytes(cfg.get("payload_hex", ""), expected_len=length))
            with state_lock:
                rpm = max(0, min(8000, int(state.rpm)))
            rpm_val = rpm // 3                      # r00li formula
            payload[3] = rpm_val & 0xFF             # low byte
            payload[4] = (rpm_val >> 8) & 0xFF      # high byte
            payload = apply_mqb_checksum_if_needed(cid, bytes(payload), cfg)
            send_can(cid, payload, extended=bool(cfg.get("extended")), tag=f"engine_rpm:{rpm}rpm")
        time.sleep(max(0.02, 1.0 / rate_hz))


def speed_loop():
    """ESP_21 + ESP_24 speed. BENCH mode only — blocked in vehicle mode (real ESP broadcasts speed)."""
    while True:
        with config_lock:
            cfg = config["speed"]
        rate_hz = float(cfg.get("rate_hz", 20.0)) or 20.0
        if state.armed and cfg.get("enabled") and state.connected and int(cfg.get("id", 0)) != 0 and not state.vehicle_mode:
            with state_lock:
                spd = max(0.0, min(260.0, float(state.speed_kmh)))
            v_speed = int(round(spd * 98.5)) & 0xFFFF
            esp24_speed = int(round(spd * 1.35 * 100)) & 0xFFFF  # *100 for proper scaling per r00li

            # ESP_21 (primary)
            cid = int(cfg["id"])
            length = int(cfg.get("length", 8))
            payload = bytearray(parse_hex_bytes(cfg.get("payload_hex", ""), expected_len=length))
            payload[4] = v_speed & 0xFF
            payload[5] = (v_speed >> 8) & 0xFF
            payload = apply_mqb_checksum_if_needed(cid, bytes(payload), cfg)
            send_can(cid, payload, extended=bool(cfg.get("extended")), tag=f"speed:ESP_21 {spd:.0f}km/h")

            # ESP_24 (kombi companion)
            esp24_id = int(cfg.get("esp24_id", 0x31B))
            if esp24_id != 0:
                payload24 = bytearray(parse_hex_bytes(cfg.get("esp24_payload_hex", ""), expected_len=8))
                payload24[2] = esp24_speed & 0xFF
                payload24[3] = (esp24_speed >> 8) & 0xFF
                # Always treat ESP_24 as MQB-checksummed regardless of cfg flag (it's in our table)
                fake_cfg = {"mqb_checksum": True}
                payload24 = apply_mqb_checksum_if_needed(esp24_id, bytes(payload24), fake_cfg)
                send_can(esp24_id, payload24, tag=f"speed:ESP_24 {spd:.0f}km/h")

        time.sleep(max(0.02, 1.0 / rate_hz))


# NOTE: fuel_loop removed in v5 — fuel level is read by MK7 cluster via analog sender, not CAN.


def engine_temp_poll_loop():
    """Poll engine ECU coolant-temp DID when auto_poll is enabled."""
    while True:
        with state_lock:
            connected = state.connected
        with config_lock:
            ecfg = config["engine_temp"]
        rate_hz = float(ecfg.get("rate_hz", 5.0)) or 5.0

        if ecfg.get("auto_poll") and connected:
            payload = build_uds_read_did_payload(int(ecfg["did"]))
            send_can(int(ecfg["request_id"]), payload, tag="uds:read_engine_temp")

        time.sleep(max(0.05, 1.0 / rate_hz))


# ---------- HTTP routes ----------

@app.route("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC, filename)


@app.route("/api/ports")
def api_ports():
    ports = [{"device": p.device, "description": p.description} for p in serial.tools.list_ports.comports()]
    return jsonify(ports)


@app.route("/api/state")
def api_state():
    with state_lock, config_lock:
        return jsonify({"state": asdict(state), "config": config})


# ---------- WebSocket events ----------

@socketio.on("connect_serial")
def ws_connect_serial(data):
    port = data.get("port")
    baud = int(data.get("baud", state.baud))
    can_speed = int(data.get("can_speed", state.can_speed))
    err = serial_open(port, baud, can_speed=can_speed)
    if err:
        socketio.emit("status", {"connected": False, "error": err})
        return
    socketio.emit("status", {"connected": True, "port": port, "baud": baud, "can_speed": can_speed})


@socketio.on("disconnect_serial")
def ws_disconnect_serial(_):
    serial_close()
    socketio.emit("status", {"connected": False})


@socketio.on("set_map")
def ws_set_map(data):
    with state_lock:
        state.map_bar = float(data.get("bar", 0.3))


@socketio.on("set_speed")
def ws_set_speed(data):
    with state_lock:
        state.speed_kmh = max(0.0, min(260.0, float(data.get("kmh", 0.0))))


@socketio.on("set_rpm")
def ws_set_rpm(data):
    with state_lock:
        state.rpm = max(0, min(8000, int(data.get("rpm", 0))))


@socketio.on("set_coolant_mode")
def ws_set_coolant_mode(data):
    """Toggle coolant slider interpretation: 'temp' (50-130°C direct) or 'boost' (BAR mapped)."""
    m = str(data.get("mode", "boost")).lower()
    if m in ("temp", "boost"):
        with state_lock:
            state.coolant_mode = m
        socketio.emit("coolant_mode_changed", {"mode": m})


@socketio.on("set_live_diag")
def ws_set_live_diag(data):
    """Single toggle that enables BOTH UDS polls when on:
       - DID 0x39C0 on Engine ECU @ 0x7E0 → Saugrohrdruck (real MAP, mbar absolute)
       - DID 0x202C on Engine ECU @ 0x7E0 → Kuehlmitteltemp (real coolant temp, 0.1°C)
       Useful when ESP32 is connected in parallel on a real running car's CAN."""
    enabled = bool(data.get("enabled", False))
    with config_lock:
        # Enable map_mode = "live" pour activer uds_poll_loop sur 0x39C0
        state.map_mode = "live" if enabled else "slider"
        # Enable engine_temp.auto_poll
        if "engine_temp" in config:
            config["engine_temp"]["auto_poll"] = enabled
            save_config(config)
    socketio.emit("live_diag_changed", {"enabled": enabled})


# set_fuel removed in v5 — fuel is analog-only on MK7 cluster.


@socketio.on("set_vehicle_mode")
def ws_set_vehicle_mode(data):
    """Toggle Vehicle Mode. When ON: only coolant section is allowed to broadcast.
    Designed for safe deployment on a real running car (no conflict with real ECUs)."""
    enabled = bool(data.get("enabled", False))
    with state_lock:
        state.vehicle_mode = enabled
        if enabled:
            # Force-disable everything risky on the bus when entering vehicle mode.
            with config_lock:
                for section in ["wake", "engine_code", "engine_rpm", "speed", "gear", "brightness"]:
                    if section in config and isinstance(config[section], dict):
                        config[section]["enabled"] = False
                save_config(config)
            # Stop any active raw periodic / scanner.
            state.raw_periodic_enabled = False
            state.scanner_id = 0
    socketio.emit("vehicle_mode_changed", {"enabled": enabled})


@socketio.on("set_armed")
def ws_set_armed(data):
    """Master safety toggle. When False, no periodic TX (coolant/gear) and buttons reject."""
    armed = bool(data.get("armed", False))
    with state_lock:
        if armed and not state.connected:
            socketio.emit("status", {"error": "cannot arm: not connected"})
            return
        state.armed = armed
    socketio.emit("armed_changed", {"armed": armed})


@socketio.on("set_mode")
def ws_set_mode(data):
    m = str(data.get("mode", "slider")).lower()
    if m not in ("live", "slider", "normal"):
        return
    with state_lock:
        state.map_mode = m
        if m != "live":
            state.live_map_bar = None
            state.live_map_ts = 0.0
    socketio.emit("mode_changed", {"mode": m})


@socketio.on("set_gear")
def ws_set_gear(data):
    g = str(data.get("gear", "P")).upper()
    if g in ("P", "R", "N", "D", "S"):
        with state_lock:
            state.gear = g


@socketio.on("press_button")
def ws_press_button(data):
    """MFA button click. Click-fired only (no periodic), so no per-button enable flag needed —
    just gated by armed + connected. Per r00li, MFSW (0x5BF) is 4 bytes, no CRC."""
    name = str(data.get("name", "")).upper()
    if name not in BUTTON_NAMES:
        return
    with state_lock:
        armed = state.armed
        connected = state.connected
        vehicle = state.vehicle_mode
    if vehicle:
        socketio.emit("status", {"error": f"button {name} blocked: VEHICLE MODE (bench-only feature)"})
        return
    if not armed:
        socketio.emit("status", {"error": f"button {name} blocked: master switch is DISARMED"})
        return
    if not connected:
        socketio.emit("status", {"error": f"button {name} blocked: not connected"})
        return
    with config_lock:
        button_cfg = config["buttons"].get(name)
    if not button_cfg or int(button_cfg.get("id", 0)) == 0:
        socketio.emit("status", {"error": f"button {name}: ID is 0x000 (unconfigured)"})
        return

    cid, press, release = build_button_frames(button_cfg)
    extended = bool(button_cfg.get("extended", False))
    # MFSW (0x5BF) per r00li is plain — NEVER apply MQB checksum. Force off here regardless of
    # saved config (defensive: a stale config.json could have mqb_checksum=True which would
    # corrupt byte 1 with the counter and break the button).
    safe_cfg = dict(button_cfg)
    safe_cfg["mqb_checksum"] = False
    press = apply_mqb_checksum_if_needed(cid, press, safe_cfg)
    release = apply_mqb_checksum_if_needed(cid, release, safe_cfg)
    send_can(cid, press, extended=extended, tag=f"btn:{name}:press")
    time.sleep(max(0.0, int(button_cfg.get("hold_ms", 30)) / 1000.0))
    send_can(cid, release, extended=extended, tag=f"btn:{name}:release")


@socketio.on("press_light")
def ws_press_light(data):
    """Click-fired light test: send ON or OFF payload of the given light. BENCH mode only.
    `name` matches CONFIG.lights[*].name. `state` is "on" or "off"."""
    name = str(data.get("name", ""))
    state_val = str(data.get("state", "")).lower()
    if state_val not in ("on", "off"):
        return
    with state_lock:
        armed = state.armed
        connected = state.connected
        vehicle = state.vehicle_mode
    if vehicle:
        socketio.emit("status", {"error": f"light '{name}' blocked: VEHICLE MODE (bench-only)"})
        return
    if not armed:
        socketio.emit("status", {"error": f"light '{name}' blocked: DISARMED"})
        return
    if not connected:
        socketio.emit("status", {"error": f"light '{name}' blocked: not connected"})
        return
    with config_lock:
        light = next((L for L in config.get("lights", []) if L.get("name") == name), None)
    if not light or int(light.get("id", 0)) == 0:
        socketio.emit("status", {"error": f"light '{name}' blocked: ID is 0x000 (unconfigured)"})
        return
    cid = int(light["id"])
    length = int(light.get("length", 8))
    payload_key = "on_payload_hex" if state_val == "on" else "off_payload_hex"
    payload = parse_hex_bytes(light.get(payload_key, ""), expected_len=length)
    payload = apply_mqb_checksum_if_needed(cid, payload, light)
    extended = bool(light.get("extended", False))
    send_can(cid, payload, extended=extended, tag=f"light:{name}:{state_val}")


@socketio.on("save_config")
def ws_save_config(new_cfg):
    global config
    with config_lock:
        config = new_cfg
        save_config(config)
    socketio.emit("config_saved", {"ok": True})


# Sections that have a periodic broadcast slot with an `enabled` flag the user toggles directly.
TOGGLE_SECTIONS = {"wake", "coolant", "engine_code", "engine_rpm", "speed", "fuel", "gear", "brightness"}


@socketio.on("set_enable")
def ws_set_enable(data):
    """Toggle a single section's enabled flag. Used by the per-function ON/OFF buttons."""
    section = str(data.get("section", ""))
    value = bool(data.get("value", False))
    if section not in TOGGLE_SECTIONS:
        return
    with config_lock:
        if section in config and isinstance(config[section], dict):
            config[section]["enabled"] = value
            # Auto-bundle engine_code with coolant — but ONLY in bench mode. On a real car,
            # the real engine ECU already broadcasts Motor_Code_01; sending our duplicate would
            # conflict. So in vehicle_mode we skip the auto-bundle.
            with state_lock:
                in_vehicle_mode = state.vehicle_mode
            if section == "coolant" and value and "engine_code" in config and not in_vehicle_mode:
                config["engine_code"]["enabled"] = True
            save_config(config)
    socketio.emit("enable_changed", {"section": section, "value": value})
    if section == "coolant" and value:
        socketio.emit("enable_changed", {"section": "engine_code", "value": True})


@socketio.on("reset_config")
def ws_reset_config(_):
    """Wipe saved config.json and reload the in-memory defaults."""
    global config
    with config_lock:
        try:
            CONFIG_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        config = _fresh_default_config()
    socketio.emit("config_reset", {"ok": True})


@socketio.on("wake_once")
def ws_wake_once(_):
    """Send one wake-up frame. BLOCKED in vehicle mode (real gateway already broadcasts Klemmen)."""
    with state_lock:
        armed = state.armed
        connected = state.connected
        vehicle = state.vehicle_mode
    if vehicle:
        socketio.emit("status", {"error": "wake blocked: VEHICLE MODE (bench-only)"})
        return
    if not armed:
        socketio.emit("status", {"error": "wake blocked: master switch is DISARMED"})
        return
    if not connected:
        socketio.emit("status", {"error": "wake blocked: not connected"})
        return
    with config_lock:
        cfg = config["wake"]
    if int(cfg.get("id", 0)) == 0:
        socketio.emit("status", {"error": "wake blocked: ID is 0x000 (unconfigured)"})
        return
    cid = int(cfg["id"])
    length = int(cfg.get("length", 4))
    payload = parse_hex_bytes(cfg.get("payload_hex", ""), expected_len=length)
    payload = apply_mqb_checksum_if_needed(cid, payload, cfg)
    send_can(cid, payload, extended=bool(cfg.get("extended")), tag="wake:once")


@socketio.on("cluster_ping")
def ws_cluster_ping(_):
    """Send a one-shot UDS ReadDataByIdentifier(cluster.did) to the cluster."""
    with config_lock:
        ccfg = config["cluster_ping"]
    payload = build_uds_read_did_payload(int(ccfg["did"]))
    send_can(int(ccfg["request_id"]), payload, tag="cluster:ping")


@socketio.on("engine_temp_read")
def ws_engine_temp_read(_):
    """Send a one-shot UDS read for the engine ECU coolant temp DID."""
    with config_lock:
        ecfg = config["engine_temp"]
    payload = build_uds_read_did_payload(int(ecfg["did"]))
    send_can(int(ecfg["request_id"]), payload, tag="uds:read_engine_temp")


@socketio.on("engine_temp_auto")
def ws_engine_temp_auto(data):
    """Toggle the engine-temp auto poller. Persists to config.json."""
    enabled = bool(data.get("enabled", False))
    with config_lock:
        config["engine_temp"]["auto_poll"] = enabled
        save_config(config)
    socketio.emit("engine_temp_auto_changed", {"enabled": enabled})


@socketio.on("scanner_set")
def ws_scanner_set(data):
    """Switch the scanner to a new (id, data, label). Pass id=0 to stop scanning."""
    cid = int(str(data.get("id", 0)), 0)
    data_hex = str(data.get("data", ""))
    label = str(data.get("label", ""))
    with state_lock:
        state.scanner_id = cid
        state.scanner_data_hex = data_hex
        state.scanner_label = label
    socketio.emit("scanner_changed", {"id": cid, "data": data_hex, "label": label})


@socketio.on("send_raw")
def ws_send_raw(data):
    """One-shot raw frame. BLOCKED in vehicle mode."""
    try:
        with state_lock:
            vehicle = state.vehicle_mode
        if vehicle:
            socketio.emit("status", {"error": "raw send blocked: VEHICLE MODE (bench-only feature)"})
            return
        cid = int(str(data.get("id", "0")), 0)
        payload = parse_hex_bytes(data.get("data", ""))
        ext = bool(data.get("extended", False))
        send_can(cid, payload, extended=ext, tag="raw")
    except Exception as e:
        socketio.emit("status", {"error": f"send_raw failed: {e}"})


@socketio.on("set_raw_periodic")
def ws_set_raw_periodic(data):
    """Configure the periodic raw broadcast. enabled=False to stop."""
    try:
        with state_lock:
            state.raw_periodic_id = int(str(data.get("id", "0")), 0)
            state.raw_periodic_data_hex = str(data.get("data", ""))
            state.raw_periodic_extended = bool(data.get("extended", False))
            state.raw_periodic_rate_hz = max(0.1, min(50.0, float(data.get("rate_hz", 5.0))))
            state.raw_periodic_enabled = bool(data.get("enabled", False))
        socketio.emit("raw_periodic_changed", {
            "id": state.raw_periodic_id,
            "data": state.raw_periodic_data_hex,
            "rate_hz": state.raw_periodic_rate_hz,
            "enabled": state.raw_periodic_enabled,
        })
    except Exception as e:
        socketio.emit("status", {"error": f"set_raw_periodic failed: {e}"})


def raw_periodic_loop():
    """Send a user-configured frame periodically. BENCH mode only — blocked in vehicle mode."""
    while True:
        with state_lock:
            enabled = state.raw_periodic_enabled
            cid = state.raw_periodic_id
            data_hex = state.raw_periodic_data_hex
            ext = state.raw_periodic_extended
            rate_hz = state.raw_periodic_rate_hz
            armed = state.armed
            connected = state.connected
            vehicle = state.vehicle_mode
        if armed and connected and enabled and cid != 0 and not vehicle:
            payload = parse_hex_bytes(data_hex)
            send_can(cid, payload, extended=ext, tag=f"raw:{rate_hz:.1f}Hz")
        time.sleep(max(0.02, 1.0 / max(0.1, rate_hz)))


# ---------- Boot ----------

def main():
    threading.Thread(target=reader_loop, daemon=True).start()
    threading.Thread(target=coolant_loop, daemon=True).start()
    threading.Thread(target=gear_loop, daemon=True).start()
    threading.Thread(target=uds_poll_loop, daemon=True).start()
    threading.Thread(target=engine_temp_poll_loop, daemon=True).start()
    threading.Thread(target=wake_loop, daemon=True).start()
    threading.Thread(target=brightness_loop, daemon=True).start()
    threading.Thread(target=engine_code_loop, daemon=True).start()
    threading.Thread(target=engine_rpm_loop, daemon=True).start()
    threading.Thread(target=speed_loop, daemon=True).start()
    threading.Thread(target=system_context_loop, daemon=True).start()
    threading.Thread(target=raw_periodic_loop, daemon=True).start()
    threading.Thread(target=scanner_loop, daemon=True).start()
    print("Open http://127.0.0.1:5000/")
    socketio.run(app, host="127.0.0.1", port=5000, debug=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
