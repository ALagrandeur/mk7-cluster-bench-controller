# -*- coding: utf-8 -*-
import os, statistics
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

ids=set(c for _,c,_ in rows)
import collections
series=collections.defaultdict(list)
for ts,c,dd in rows:
    s=sec(ts)
    if 69<=s<=86: series[c].append((s,dd))

print("Signals that DROP during pull windows (>=3 of 5 pulls), excluding counters:")
hits=[]
for cid in ids:
    s=series.get(cid,[])
    if len(s)<20: continue
    for b in range(8):
        vals=[dd[b] for _,dd in s]
        med=statistics.median(vals); mx=max(vals); mn=min(vals)
        if mx-mn<8 or med<8: continue          # ignore near-constant / tiny
        # skip alive counters: low nibble cycling -> high variance but not a 'signal'
        # heuristic: counter if all 16 low-nibble values appear
        if len(set(v&0x0F for v in vals))>=15 and (mx>>4)==(med//16): pass
        cnt=0; detail=[]
        for pa,pb in PULLS:
            base=[dd[b] for t,dd in s if pa-0.7<=t<pa-0.05]
            dur =[dd[b] for t,dd in s if pa<=t<=pb+0.2]
            if not base or not dur: detail.append("-"); continue
            b0=max(base); dm=min(dur)
            if dm <= b0*0.5 and (b0-dm)>=8:
                cnt+=1; detail.append("v")
            else: detail.append(".")
        if cnt>=3:
            hits.append((cnt,cid,b,med,mn,mx,"".join(detail)))
hits.sort(reverse=True)
for cnt,cid,b,med,mn,mx,det in hits:
    print(f"  0x{cid:03X} D{b+1}: {cnt}/5 pulls  [{det}]  median0x{int(med):02X} range0x{mn:02X}-0x{mx:02X}")
if not hits: print("  (none with >=3/5)")
