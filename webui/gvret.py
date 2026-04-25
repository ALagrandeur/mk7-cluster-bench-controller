"""
GVRET binary serial protocol used by ESP32RET (Collin Kidder).
Reference: https://github.com/collin80/ESP32RET

Frame format for sending a CAN frame to the device:
    0xF1, 0x00,
    ID_b0, ID_b1, ID_b2, ID_b3,   # 32-bit ID, little-endian. Bit 31 (0x80 of ID_b3) = extended flag
    BUS,                          # bus number (0 = CAN0, 1 = CAN1, 2 = SWCAN, etc.)
    LEN,                          # payload length (0..8)
    D0..D(LEN-1),                 # payload bytes
    CHECKSUM                      # 8-bit sum of all preceding bytes starting at byte 2 (post header), mod 256

Frame format for received frames from the device (when capture is enabled):
    0xF1, 0x00,
    TIME_b0..b3,                  # 32-bit timestamp microseconds, little-endian
    ID_b0..b3,                    # 32-bit ID, little-endian, bit 31 = extended
    INFO,                         # bits: 0..3 = length, bit 6 = remote, bit 7 = bus number high bit (varies)
    D0..D(LEN-1),
    CHECKSUM

Setup commands (less critical for this project):
    0xF1, 0x09 ... = various setup commands
    0xE7          = enter binary mode (sometimes required from text mode)

Notes:
- Some forks differ slightly. If the cluster sees nothing, double-check by sending the same
  message via SavvyCAN's "Send Frames" tab and capturing the bytes on the wire with a logic
  analyzer or another tool.
- The checksum implementation in some versions of ESP32RET is permissive (accepts 0). We still
  compute it correctly here.
"""

from __future__ import annotations

GVRET_HEADER = 0xF1
CMD_BUILD_CAN_FRAME = 0x00
CMD_TIME_SYNC = 0x01
CMD_GET_DIG_INPUTS = 0x02
CMD_GET_ANALOG_INPUTS = 0x03
CMD_SET_DIG_OUTPUTS = 0x04
CMD_SETUP_CANBUS = 0x05
CMD_GET_CANBUS_PARAMS = 0x06
CMD_GET_DEVICE_INFO = 0x07
CMD_SET_SINGLEWIRE_MODE = 0x08
CMD_KEEPALIVE = 0x09
CMD_SET_SYSTYPE = 0x0A
CMD_ECHO_CAN_FRAME = 0x0B
CMD_ENABLE_BINARY_MODE = 0xE7  # sent as raw byte (no 0xF1 prefix) to switch into binary


def _checksum(data: bytes) -> int:
    """8-bit sum checksum used by GVRET, mod 256."""
    s = 0
    for b in data:
        s = (s + b) & 0xFF
    return s


def build_can_frame(can_id: int, data: bytes, bus: int = 0, extended: bool | None = None) -> bytes:
    """
    Build the bytes to send a CAN frame through ESP32RET.

    can_id: 11-bit (standard) or 29-bit (extended) CAN identifier
    data:   payload, 0..8 bytes
    bus:    bus number (0 = CAN0)
    extended: True/False to force, None to auto-detect (extended if id > 0x7FF)
    """
    if not (0 <= can_id <= 0x1FFFFFFF):
        raise ValueError(f"CAN ID out of range: 0x{can_id:X}")
    if len(data) > 8:
        raise ValueError(f"CAN payload too long: {len(data)} bytes")
    if extended is None:
        extended = can_id > 0x7FF

    id_field = can_id & 0x1FFFFFFF
    if extended:
        id_field |= 0x80000000

    body = bytearray()
    body.append(id_field & 0xFF)
    body.append((id_field >> 8) & 0xFF)
    body.append((id_field >> 16) & 0xFF)
    body.append((id_field >> 24) & 0xFF)
    body.append(bus & 0xFF)
    body.append(len(data))
    body.extend(data)
    body.append(_checksum(body))

    return bytes([GVRET_HEADER, CMD_BUILD_CAN_FRAME]) + bytes(body)


def _bus_config_word(speed: int, enabled: bool, listen_only: bool) -> int:
    """
    Encode a single ESP32RET CAN-bus config as a 32-bit word (matches gvret_comm.cpp parser):
      bit 31 (0x80000000) = "extended status mode" — flags present
      bit 30 (0x40000000) = enabled
      bit 29 (0x20000000) = listen only
      bits 0..19         = speed in bps (mask 0xFFFFF, capped at 1 Mbps by device)
    """
    if speed <= 0:
        return 0  # 0 disables this bus
    word = 0x80000000  # signal that flags are present
    if enabled:
        word |= 0x40000000
    if listen_only:
        word |= 0x20000000
    word |= speed & 0xFFFFF
    return word & 0xFFFFFFFF


def build_setup_canbus(bus0_speed: int = 500000, bus1_speed: int = 0,
                       bus0_enabled: bool = True, bus0_listen_only: bool = False,
                       bus1_enabled: bool = False, bus1_listen_only: bool = False) -> bytes:
    """
    Configure both CAN buses on the ESP32RET device.

    The device parses 8 bytes after `0xF1 0x05`: 4 bytes for bus0 (LE), then 4 bytes for bus1.
    Each 4-byte word encodes speed + enabled/listen-only flags (see _bus_config_word).

    Defaults: bus 0 enabled at 500 kbps, bus 1 disabled (typical bench setup).
    """
    word0 = _bus_config_word(bus0_speed, bus0_enabled, bus0_listen_only)
    word1 = _bus_config_word(bus1_speed, bus1_enabled, bus1_listen_only)
    body = bytearray()
    body += word0.to_bytes(4, "little")
    body += word1.to_bytes(4, "little")
    return bytes([GVRET_HEADER, CMD_SETUP_CANBUS]) + bytes(body)


def build_keepalive() -> bytes:
    return bytes([GVRET_HEADER, CMD_KEEPALIVE])


# -------- Receive-side parser (best-effort, used for the live frame log) --------

class GvretParser:
    """
    Streaming parser for ESP32RET output. Hand bytes via feed(); yields parsed frames as dicts.
    Resilient: on any framing error it resyncs by searching for the next 0xF1 header.
    """

    def __init__(self) -> None:
        self.buf = bytearray()

    def feed(self, chunk: bytes):
        self.buf.extend(chunk)
        while True:
            frame, consumed = self._try_parse()
            if frame is None and consumed == 0:
                return
            if consumed:
                del self.buf[:consumed]
            if frame is not None:
                yield frame

    def _try_parse(self):
        # Find header
        idx = self.buf.find(GVRET_HEADER)
        if idx < 0:
            n = len(self.buf)
            self.buf.clear()
            return None, n
        if idx > 0:
            return None, idx  # drop noise before header

        if len(self.buf) < 2:
            return None, 0
        cmd = self.buf[1]

        if cmd != CMD_BUILD_CAN_FRAME:
            # Unknown / unhandled command — drop just the header byte to resync.
            return None, 1

        # Need at least header(2) + time(4) + id(4) + info(1) = 11 bytes before data
        if len(self.buf) < 11:
            return None, 0

        time_us = int.from_bytes(self.buf[2:6], "little")
        raw_id = int.from_bytes(self.buf[6:10], "little")
        extended = bool(raw_id & 0x80000000)
        can_id = raw_id & 0x1FFFFFFF
        info = self.buf[10]
        length = info & 0x0F
        bus = (info >> 4) & 0x0F

        total = 11 + length + 1  # +1 checksum byte
        if len(self.buf) < total:
            return None, 0

        data = bytes(self.buf[11:11 + length])
        # checksum byte ignored for robustness

        return {
            "time_us": time_us,
            "id": can_id,
            "extended": extended,
            "bus": bus,
            "data": data,
        }, total
