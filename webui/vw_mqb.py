"""
VW MQB-platform CAN message helpers: CRC8H2F-based custom checksum + 4-bit rolling counter.

Direct port of the algorithm used by comma.ai openpilot/opendbc for VW MQB cars
(https://github.com/commaai/opendbc, files: opendbc/car/crc.py and opendbc/car/volkswagen/mqbcan.py).
This is production code that runs on real MQB cars in openpilot — solid reference.

Why this matters for the MK7 cluster bench:
- Many MQB broadcasts (Klemmen_Status_01 / wake-up, Motor_14 / coolant temp, GRA_ACC_01 / steering
  buttons, Getriebe_11 / gear, etc.) carry a 1-byte custom checksum at byte 0 and a 4-bit counter
  in the low nibble of byte 1. The cluster validates both and silently drops frames that don't match.
- Without correct counter+checksum, the wake-up message is ignored and the cluster stays asleep.
"""

from __future__ import annotations

# -------- CRC8H2F lookup table (polynomial 0x2F, no init/xor) --------

def _gen_crc8h2f_table() -> list[int]:
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x2F) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
        table.append(crc)
    return table


CRC8H2F = _gen_crc8h2f_table()


# -------- Per-message constants used by the MQB checksum --------
#
# 16 entries per ID = one constant per counter value (0..15). Source: opendbc/car/volkswagen/mqbcan.py
# Subset relevant to this project. Add entries here if you need other MQB messages.

VOLKSWAGEN_MQB_MEB_CONSTANTS: dict[int, list[int]] = {
    # 0xAD = 173  : Getriebe_11 (gear position from TCM)
    0xAD: [0x3F, 0x69, 0x39, 0xDC, 0x94, 0xF9, 0x14, 0x64,
           0xD8, 0x6A, 0x34, 0xCE, 0xA2, 0x55, 0xB5, 0x2C],
    # 0x12B = 299 : GRA_ACC_01 (cruise + steering wheel buttons)
    0x12B: [0x6A, 0x38, 0xB4, 0x27, 0x22, 0xEF, 0xE1, 0xBB,
            0xF8, 0x80, 0x84, 0x49, 0xC7, 0x9E, 0x1E, 0x2B],
    # 0x3BE = 958 : Motor_14 (engine status incl. coolant temp on many MQB)
    0x3BE: [0x1F, 0x28, 0xC6, 0x85, 0xE6, 0xF8, 0xB0, 0x19,
            0x5B, 0x64, 0x35, 0x21, 0xE4, 0xF7, 0x9C, 0x24],
    # 0x3C0 = 960 : Klemmen_Status_01 (terminal status — THE wake-up message)
    0x3C0: [0xC3] * 16,
    # 0x3D5 = 981 : Licht_Anf_01 (light request)
    0x3D5: [0xC5, 0x39, 0xC7, 0xF9, 0x92, 0xD8, 0x24, 0xCE,
            0xF1, 0xB5, 0x7A, 0xC4, 0xBC, 0x60, 0xE3, 0xD1],
    # ---- Constants from r00li/CarCluster (tested on Golf 7 MQB cluster) ----
    # 0x40  = 64  : Airbag_01 (airbag controller heartbeat)
    0x40: [0x40] * 16,
    # 0x101 = 257 : ESP_02
    0x101: [0xAA] * 16,
    # 0x116 = 278 : ESP_10
    0x116: [0xAC] * 16,
    # 0x31B = 795 : ESP_24 (cluster speed/distance)
    0x31B: [0x67, 0x8A, 0xAE, 0x22, 0x4D, 0xD0, 0x51, 0x80,
            0x5C, 0xB9, 0xCE, 0x1E, 0xDF, 0x02, 0x2D, 0xD4],
    # 0x31E = 798 : TSK_07 (engine torque coordinator heartbeat)
    0x31E: [0x78, 0x68, 0x3A, 0x31, 0x16, 0x08, 0x4F, 0xDE,
            0xF7, 0x35, 0x19, 0xE6, 0x28, 0x2F, 0x59, 0x82],
    # 0x30F = 783 : SWA_01 (lane change assist)
    0x30F: [0x0C] * 16,
    # 0x32A = 810 : LH_EPS_01 (electric power steering)
    0x32A: [0x29] * 16,
    # 0x394 = 916 : WBA_03 (gear position display)
    0x394: [0x47, 0x94, 0x92, 0x6A, 0x67, 0xB5, 0x0D, 0x38,
            0xE3, 0x8A, 0x5D, 0xB4, 0x54, 0xAB, 0xAE, 0x27],
    # 0x641 = 1601 : Motor_Code_01 (engine code/version heartbeat — REQUIRED for cluster to trust engine messages)
    0x641: [0x47] * 16,
}


def mqb_checksum(address: int, data: bytes | bytearray) -> int:
    """
    Compute the VW MQB custom checksum for byte 0 of a CAN frame.
    Direct port of `volkswagen_mqb_meb_checksum` from openpilot/opendbc.

    The checksum byte itself sits at index 0; the counter (4-bit) is in the low nibble of byte 1.
    """
    if len(data) < 2:
        raise ValueError("payload too short for MQB checksum (need at least 2 bytes)")
    crc = 0xFF
    for i in range(1, len(data)):           # skip byte 0 (which IS the checksum)
        crc ^= data[i]
        crc = CRC8H2F[crc]
    counter = data[1] & 0x0F
    const_table = VOLKSWAGEN_MQB_MEB_CONSTANTS.get(address)
    if const_table:
        crc ^= const_table[counter]
        crc = CRC8H2F[crc]
    return crc ^ 0xFF


def has_mqb_checksum(address: int) -> bool:
    """True if the given CAN ID is known to use the MQB counter+checksum scheme."""
    return address in VOLKSWAGEN_MQB_MEB_CONSTANTS


def apply_counter_and_checksum(address: int, payload: bytes, counter: int) -> bytes:
    """
    Take a payload, write the 4-bit counter into the low nibble of byte 1,
    compute the MQB checksum, and write it into byte 0. Returns a new bytes.

    `counter` is taken modulo 16. Caller is responsible for incrementing between frames.
    """
    if len(payload) < 2:
        raise ValueError("payload too short")
    out = bytearray(payload)
    out[1] = (out[1] & 0xF0) | (counter & 0x0F)
    out[0] = 0x00                            # zero out before computing
    out[0] = mqb_checksum(address, out)
    return bytes(out)


# -------- Self-test: verify against a known-good frame --------
# When we get real captured frames from the user's CAN log, add them as test vectors here.
# For now this just sanity-checks the CRC table generation and the algorithm's shape.

if __name__ == "__main__":
    assert len(CRC8H2F) == 256
    # Check a couple of entries against the openpilot reference.
    # CRC8H2F[0x00] = 0x00, CRC8H2F[0x01] should be the polynomial bits
    assert CRC8H2F[0] == 0
    # Sanity: applying counter+checksum twice with the same counter yields the same byte
    payload = bytes([0x00, 0x00, 0x02, 0x00])  # Klemmen_Status_01 with Kl.15 bit set, counter=0
    f1 = apply_counter_and_checksum(0x3C0, payload, 0)
    f2 = apply_counter_and_checksum(0x3C0, payload, 0)
    assert f1 == f2
    # Different counter -> different checksum (because the constant changes... well, not for 0x3C0
    # which uses 0xC3 for all 16 — but the counter nibble itself changes byte 1)
    f3 = apply_counter_and_checksum(0x3C0, payload, 5)
    assert f3[1] & 0x0F == 5
    print(f"Klemmen_Status_01 counter=0 Kl.15: {f1.hex()}")
    print(f"Klemmen_Status_01 counter=5 Kl.15: {f3.hex()}")
    print("Self-test passed.")
