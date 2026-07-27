#!/usr/bin/env python3
# Analyze SavvyCAN capture -> replay table for bench cluster.
import csv, statistics, sys

CSV = r"C:/Users/AntoineLagrandeur/BOT32/DATA input from CAR/OFF to start cluster.csv"
OUT = r"C:/Users/AntoineLagrandeur/MK7 cluster/analysis/replay_report.md"

rows = []  # (ts_us, idhex, ext, dlc, [bytes])
with open(CSV, newline='') as f:
    r = csv.reader(f)
    header = next(r)
    for line in r:
        if len(line) < 6:
            continue
        try:
            ts = int(line[0])
        except ValueError:
            continue
        idhex = line[1].lstrip('0') or '0'
        idhex = idhex.upper().rjust(3, '0')
        ext = (line[2].strip().lower() == 'true')
        try:
            dlc = int(line[5])
        except ValueError:
            dlc = 0
        data = []
        for i in range(6, 6+8):
            if i < len(line) and line[i].strip() != '':
                data.append(line[i].strip().upper())
        rows.append((ts, idhex, ext, dlc, data))

if not rows:
    open(OUT,'w').write("NO ROWS PARSED\n")
    sys.exit(0)

t0 = rows[0][0]
t_end = rows[-1][0]
span_us = t_end - t0

# Split
ids11 = {}
for ts, idhex, ext, dlc, data in rows:
    if ext:
        continue
    ids11.setdefault(idhex, []).append((ts, dlc, data))

n11 = sum(len(v) for v in ids11.values())
n29 = sum(1 for r in rows if r[2])

# late window = last 10% by time
late_start = t_end - int(span_us*0.10)

def median(xs):
    return statistics.median(xs) if xs else None

results = []
for idhex, lst in ids11.items():
    lst.sort()
    ts_list = [x[0] for x in lst]
    deltas = [ (ts_list[i]-ts_list[i-1]) for i in range(1, len(ts_list)) ]
    med_dt = median(deltas)  # us
    cnt = len(lst)
    # late samples
    late = [x for x in lst if x[0] >= late_start]
    if not late:
        late = lst[-5:]
    # representative late payload = the most common late payload string, else last
    from collections import Counter
    payload_strs = [' '.join(x[2]) for x in late]
    common = Counter(payload_strs).most_common(1)[0]
    rep_payload = common[0]
    rep_dlc = late[-1][1]
    # variability across late window
    distinct_late = len(set(payload_strs))
    last_payload = ' '.join(lst[-1][2])

    # CRC+counter heuristic: examine ALL frames in late window (or last up to 60)
    sample = lst[-min(len(lst),80):]
    b0 = [x[2][0] for x in sample if len(x[2])>=1]
    b1 = [x[2][1] for x in sample if len(x[2])>=2]
    b0_distinct = len(set(b0))
    # counter = low nibble of byte1
    cnt_nibbles = []
    for v in b1:
        try:
            cnt_nibbles.append(int(v,16) & 0x0F)
        except ValueError:
            pass
    nib_distinct = len(set(cnt_nibbles))
    # check rolling 0..15 behaviour: count how many consecutive increments (mod16)
    inc_ok = 0
    inc_tot = 0
    for i in range(1,len(cnt_nibbles)):
        inc_tot += 1
        if (cnt_nibbles[i] - cnt_nibbles[i-1]) % 16 == 1:
            inc_ok += 1
    inc_ratio = (inc_ok/inc_tot) if inc_tot else 0
    crc_counter = (b0_distinct >= max(4, len(sample)//4)) and (nib_distinct >= 6) and (inc_ratio >= 0.5)

    results.append({
        'id': idhex, 'count': cnt, 'med_dt_us': med_dt,
        'rep_payload': rep_payload, 'rep_dlc': rep_dlc,
        'distinct_late': distinct_late, 'last_payload': last_payload,
        'b0_distinct': b0_distinct, 'nib_distinct': nib_distinct,
        'inc_ratio': inc_ratio, 'crc_counter': crc_counter,
        'first_ts': ts_list[0], 'last_ts': ts_list[-1],
        'sample_n': len(sample),
    })

# sort by frequency (count desc)
results.sort(key=lambda d: d['count'], reverse=True)

# Known MQB ID name map (best-effort, MQB platform 500k powertrain CAN)
NAMES = {
 '040':'Airbag_01 (airbag/SRS status)',
 '0FD':'ESP_21 (ESP/ABS dynamics)',
 '101':'ESP_02',
 '103':'ESP_05',
 '106':'ESP_10 / brake',
 '116':'ESP_19 (wheel/ABS)',
 '0AD':'ESP family',
 '0AE':'ESP family',
 '107':'Motor_xx (RPM/engine - bench-confirmed RPM)',
 '10B':'Motor_07? (engine status)',
 '120':'ESP_22?',
 '12B':'?',
 '146':'?',
 '147':'?',
 '14C':'?',
 '187':'EV/motor?',
 '17F':'Getriebe/trans?',
 '1A0':'ESP_15? / speed',
 '1AB':'?',
 '30B':'Kombi_01 / KOMBI status (telltale data)',
 '320':'Lenkhilfe / EPS steering assist',
 '32A':'EPB_01? steering/EPS column (bench sends)',
 '395':'?',
 '391':'?',
 '3C0':'Klemmen_Status_01 (terminal/ignition)',
 '3D0':'?',
 '3DC':'Kombi/diag?',
 '3E5':'Gateway?',
 '3F1':'?',
 '5A0':'?',
 '5BF':'?',
 '5DF':'?',
 '5E1':'?',
 '485':'?',
 '484':'?',
 '391':'?',
 '6B2':'?',
 '641':'(bench)',
 '647':'(bench coolant override bundle)',
 '65D':'(bench)',
 '31E':'(bench)',
 '583':'?',
 '50F':'?',
 '52D':'?',
 '5E8':'?',
}

BENCH = set(['3C0','641','107','647','040','106','116','65D','31E','32A'])

def hz(dt_us):
    if not dt_us or dt_us<=0: return 0
    return 1e6/dt_us

with open(OUT,'w',encoding='utf-8') as o:
    o.write("# OFF-to-start capture -> bench replay analysis\n\n")
    o.write(f"- Total rows parsed: {len(rows)}\n")
    o.write(f"- Capture span: {span_us/1e6:.3f} s\n")
    o.write(f"- 11-bit frames: {n11}  | 29-bit frames: {n29}\n")
    o.write(f"- Distinct 11-bit IDs: {len(ids11)}\n")
    o.write(f"- Late window (steady-state) = last 10% of time = [{late_start} .. {t_end}] us ({span_us*0.10/1e6:.3f} s)\n\n")

    o.write("## Replay table (11-bit periodic, sorted by frequency)\n\n")
    o.write("| ID | count | period(ms) | ~Hz | DLC | steady payload (late 10%) | late variability | CRC+ctr? | name guess | in bench? |\n")
    o.write("|----|------:|-----------:|----:|---:|----------------------------|------------------|----------|------------|-----------|\n")
    for d in results:
        idn = d['id']
        pms = (d['med_dt_us']/1000.0) if d['med_dt_us'] else None
        pms_s = f"{pms:.1f}" if pms is not None else "n/a(1 frame)"
        hz_s = f"{hz(d['med_dt_us']):.1f}" if d['med_dt_us'] else "-"
        var = "static" if d['distinct_late']<=1 else f"{d['distinct_late']} variants"
        crc = "CRC+counter" if d['crc_counter'] else "static/other"
        nm = NAMES.get(idn, 'unknown')
        inbench = "YES" if idn in BENCH else "no"
        o.write(f"| 0x{idn} | {d['count']} | {pms_s} | {hz_s} | {d['rep_dlc']} | `{d['rep_payload']}` | {var} | {crc} | {nm} | {inbench} |\n")

    # Missing from bench
    present_periodic = [d['id'] for d in results if d['count']>=5]  # periodic-ish
    missing = [d for d in results if d['id'] not in BENCH and d['count']>=5]
    o.write("\n## MISSING FROM BENCH (periodic 11-bit IDs present in capture but NOT in bench TX list)\n\n")
    o.write("bench currently sends: " + ", ".join("0x"+b for b in sorted(BENCH)) + "\n\n")
    o.write("| ID | period(ms) | ~Hz | steady payload | CRC+ctr? | name guess |\n")
    o.write("|----|-----------:|----:|----------------|----------|------------|\n")
    for d in missing:
        idn=d['id']
        pms = (d['med_dt_us']/1000.0) if d['med_dt_us'] else None
        pms_s = f"{pms:.1f}" if pms is not None else "n/a"
        hz_s = f"{hz(d['med_dt_us']):.1f}" if d['med_dt_us'] else "-"
        crc = "CRC+counter" if d['crc_counter'] else "static"
        o.write(f"| 0x{idn} | {pms_s} | {hz_s} | `{d['rep_payload']}` | {crc} | {NAMES.get(idn,'unknown')} |\n")

    # bench IDs present / absent in capture
    o.write("\n## Bench TX IDs cross-check\n\n")
    cap_ids = set(ids11.keys())
    for b in sorted(BENCH):
        o.write(f"- 0x{b}: {'present in capture' if b in cap_ids else 'NOT in capture'}\n")

    o.write("\n## Raw per-ID detail (counter diagnostics)\n\n")
    o.write("| ID | count | med_dt_us | b0_distinct | nib_distinct | inc_ratio | sample_n |\n")
    o.write("|----|------:|----------:|------------:|-------------:|----------:|---------:|\n")
    for d in results:
        md = f"{d['med_dt_us']}" if d['med_dt_us'] is not None else "-"
        o.write(f"| 0x{d['id']} | {d['count']} | {md} | {d['b0_distinct']} | {d['nib_distinct']} | {d['inc_ratio']:.2f} | {d['sample_n']} |\n")

print("WROTE", OUT)
