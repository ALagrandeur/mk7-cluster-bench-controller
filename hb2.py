# -*- coding: utf-8 -*-
import os
ALT=r"C:\Users\AntoineLagrandeur\OneDrive - ÉNERSERV INC\Bureau"
BASE=r"C:\Users\AntoineLagrandeur\OneDrive - ENERSERV INC\Bureau"
d=ALT if os.path.isdir(ALT) else BASE
rows=[]
for line in open(os.path.join(d,"run2.csv"),encoding="utf-8",errors="replace"):
    if line.startswith("Time"):continue
    x=line.strip().split(",")
    if len(x)<6:continue
    try: ts=int(x[0]); cid=int(x[1],16)
    except: continue
    rows.append((ts,cid,[int(x[i],16) if i<len(x) and x[i].strip() else 0 for i in range(6,14)]))
t0=rows[0][0]
def sec(ts):return (ts-t0)/1e6
PULLS=[72.74,74.34,76.69,78.94,81.49]

# build per-ID time series in window 70..85s
def series(cid):
    return [(sec(ts),dd) for ts,cid2,dd in rows if cid2==cid and 70.0<=sec(ts)<=85.0]

# For each candidate signal, auto-count "dip bursts" (drops well below its window median)
import statistics
def analyze(cid, idx, name, drop_is_low=True):
    s=series(cid)
    if not s: print(f"  {name}: absent"); return
    vals=[dd[idx] for _,dd in s]
    med=statistics.median(vals)
    mx=max(vals); mn=min(vals)
    # threshold: a "cut" = value drops to <= 40% of median (or near 0)
    thr=med*0.5
    bursts=[]
    for t,dd in s:
        v=dd[idx]
        if v<=thr:
            if not bursts or t-bursts[-1][1]>0.4: bursts.append([t,t,v,v])
            else: bursts[-1][1]=t; bursts[-1][2]=min(bursts[-1][2],v)
    print(f"  {name} (D{idx+1}): median=0x{int(med):02X} range[0x{mn:02X}..0x{mx:02X}]  -> {len(bursts)} dip-burst(s)")
    for b in bursts:
        # nearest pull
        near=min(PULLS,key=lambda p:abs(p-b[0]))
        dt=b[0]-near
        print(f"       t={b[0]:6.2f}..{b[1]:5.2f}s  min=0x{b[2]:02X}   (pull {near:.2f}s, d{dt:+.2f}s)")

print("Candidate torque/engagement signals in 70-85s window, dip detection vs 5 pulls:")
analyze(0x118,2,"0x118 pump engagement")      # D3
analyze(0x0A7,6,"0x0A7 Motor_11 torque")      # D7
analyze(0x0A7,7,"0x0A7 Motor_11 torque2")     # D8
analyze(0x0A8,7,"0x0A8 Motor_12")             # D8
analyze(0x116,7,"0x116 ESP_10")               # D8
analyze(0x0A8,2,"0x0A8 D3")                   # D3
analyze(0x0A8,3,"0x0A8 D4")                   # D4

# Direct snapshot: 0x118 D3 sampled every ~0.25s across the window, mark pulls
print("\n=== 0x118 D3 (engagement) timeline 70-85s (each '.' ~ a sample) ===")
s=series(0x118)
line=""
labels=""
buckets={}
for t,dd in s:
    b=round(t*2)/2  # 0.5s buckets
    buckets.setdefault(b,[]).append(dd[2])
for b in sorted(buckets):
    v=max(buckets[b])
    c='#' if v>0x40 else ('+' if v>0x10 else ('.' if v>0 else '_'))
    mark='P' if any(abs(b-p)<0.3 for p in PULLS) else ' '
    print(f"  t={b:5.1f}s  D3max=0x{v:02X}  {c}   {mark}")
