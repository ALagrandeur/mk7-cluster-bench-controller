#!/usr/bin/env python3
"""
Identify hazard CAN signal in brake+trans.csv

The log captured ~69s with hazards toggled ON/OFF 3 times.
Looking for a CAN ID where a SPECIFIC BIT toggles exactly 6 times
(3 rising edges + 3 falling edges).
"""
import csv
from collections import defaultdict, Counter
from pathlib import Path

CSV = Path(r"C:\Users\AntoineLagrandeur\OneDrive - ÉNERSERV INC\Bureau\brake + trans.csv")

# Load all frames
frames = []
with CSV.open() as f:
    rd = csv.reader(f)
    next(rd)  # header
    for row in rd:
        if len(row) < 14:
            continue
        try:
            ts   = int(row[0])
            cid  = int(row[1], 16)
            ext  = row[2].strip().lower() == "true"
            ln   = int(row[5])
            data = [int(row[6+i], 16) for i in range(ln)]
        except Exception:
            continue
        frames.append((ts, cid, ext, ln, data))

print(f"Loaded {len(frames)} frames")
t_first = frames[0][0]
t_last  = frames[-1][0]
print(f"Span: {(t_last-t_first)/1_000_000:.1f}s")

# Group payloads by ID, ignoring counter/CRC noise by tracking byte-by-byte transitions
by_id = defaultdict(list)
for (ts, cid, ext, ln, data) in frames:
    key = (cid, ext)
    by_id[key].append((ts, tuple(data)))

# For each ID, count bit-level transitions per byte
# A "transition" = bit value changes from previous frame of same ID
print("\n=== Searching for IDs with bits that toggle exactly 6 times (3xON + 3xOFF) ===\n")

candidates = []
for (cid, ext), seq in by_id.items():
    if len(seq) < 6:
        continue
    # Some IDs have variable DLC; use the minimum length seen
    ln = min(len(s[1]) for s in seq)
    if ln == 0:
        continue
    # For each (byte_index, bit_index), count transitions
    for b in range(ln):
        for bit in range(8):
            transitions = 0
            prev = (seq[0][1][b] >> bit) & 1
            edges = []
            for (ts, data) in seq[1:]:
                if b >= len(data):
                    continue
                cur = (data[b] >> bit) & 1
                if cur != prev:
                    transitions += 1
                    edges.append((ts, prev, cur))
                    prev = cur
            if transitions == 6:
                candidates.append((cid, ext, b, bit, edges))

print(f"Found {len(candidates)} (ID,byte,bit) combos with EXACTLY 6 transitions\n")

# Print top candidates with their edge timestamps
for (cid, ext, b, bit, edges) in candidates[:40]:
    tag = "EXT" if ext else "STD"
    print(f"  ID 0x{cid:03X} [{tag}] byte[{b}] bit[{bit}]:")
    for (ts, p, c) in edges:
        rel = (ts - t_first) / 1_000_000
        print(f"     t={rel:6.2f}s  {p}->{c}")
    print()

# Also report the hazard candidates we know about: 0x366, 0x484, 0x65A
print("\n=== TARGETED ANALYSIS of 0x366 (BLINKMODI_02), 0x484, 0x65A (BCM_01) ===\n")
for target in [0x366, 0x484, 0x65A, 0x3DA, 0x585, 0x5E1]:
    hits = by_id.get((target, False), [])
    if not hits:
        continue
    # Show all unique payloads with first-seen relative time
    seen = {}
    for (ts, data) in hits:
        if data not in seen:
            seen[data] = (ts - t_first) / 1_000_000
    print(f"--- ID 0x{target:03X}  ({len(hits)} frames, {len(seen)} unique payloads) ---")
    for payload, t_rel in sorted(seen.items(), key=lambda kv: kv[1]):
        hex_str = " ".join(f"{b:02X}" for b in payload)
        print(f"   t={t_rel:6.2f}s  {hex_str}")
    print()
