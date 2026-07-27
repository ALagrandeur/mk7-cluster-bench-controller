# -*- coding: utf-8 -*-
import os, statistics, collections
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
PULLS=[(72.74,73.34),(74.34,75.39),(76.69,77.79),(78.94,80.04),(81.49,82.49)]
def in_pull(t):
    return any(pa-0.05<=t<=pb+0.25 for pa,pb in PULLS)

series=collections.defaultdict(list)
for ts,c,dd in rows:
    s=sec(ts)
    if 69<=s<=86: series[c].append((s,dd))

print("DATA bytes (D3-D8 only) that drop DURING pulls and are stable OTHERWISE:")
res=[]
for cid,s in series.items():
    if len(s)<15: continue
    for b in range(2,8):   # D3..D8 only (skip D1 CRC, D2 counter)
        out=[dd[b] for t,dd in s if not in_pull(t)]
        if not out: continue
        base=statistics.median(out)
        out_lo=sum(1 for v in out if v<=base*0.5 and (base-v)>=8)   # spurious dips outside pulls
        if base<16 or max(out)-min(out)<8: continue
        hits=0; mins=[]
        for pa,pb in PULLS:
            dur=[dd[b] for t,dd in s if pa-0.05<=t<=pb+0.25]
            if not dur: continue
            dm=min(dur); mins.append(dm)
            if dm<=base*0.5 and (base-dm)>=8: hits+=1
        spec = out_lo/max(1,len(out))   # fraction of outside samples that are 'low'
        if hits>=4 and spec<0.15:
            res.append((hits,spec,cid,b,base,mins))
res.sort(key=lambda r:(-r[0],r[1]))
for hits,spec,cid,b,base,mins in res:
    print(f"  0x{cid:03X} D{b+1}: {hits}/5 pulls dip | baseline~0x{int(base):02X} | per-pull min={['%02X'%m for m in mins]} | outside-low {spec*100:.0f}%")
if not res: print("  (no clean data-byte signal -> the cut shows mainly on engagement 0x118 D3)")

# focused: 0x0A8 D4 and 0x0A8 D7 traces around each pull
for cid,bi,nm in [(0x0A8,3,"0x0A8 D4"),(0x0A8,6,"0x0A8 D7")]:
    s=series[cid]
    print(f"\n{nm} per pull:")
    for i,(pa,pb) in enumerate(PULLS,1):
        tr=[dd[bi] for t,dd in s if pa-0.3<=t<=pb+0.3]
        print(f"  #{i}: "+" ".join("%02X"%v for v in tr))
