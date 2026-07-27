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
PULLS=[(72.74,73.34),(74.34,75.39),(76.69,77.79),(78.94,80.04),(81.49,82.49)]

def at(cid):
    return [(sec(ts),dd) for ts,c,dd in rows if c==cid]
eng=at(0x118)   # D3 engagement
def win(series,a,b): return [(t,dd) for t,dd in series if a<=t<=b]

print("Per-pull rear-axle engagement (0x118 D3 = Haldex pump %, native 100ms):\n")
for i,(pa,pb) in enumerate(PULLS,1):
    base=[dd[2] for t,dd in win(eng,pa-0.6,pa-0.05)]   # just before pull
    during=[dd[2] for t,dd in win(eng,pa,pb+0.2)]      # during pull(+brief after)
    b0=max(base) if base else 0
    dmin=min(during) if during else 0
    dmax=max(during) if during else 0
    trace=" ".join("%02X"%dd[2] for t,dd in win(eng,pa-0.3,pb+0.3))
    cut = "CUT to 0x%02X"%dmin if dmin< max(1,b0*0.6) else "no clear cut"
    print(f"  pull #{i} {pa:.2f}-{pb:.2f}s | before~0x{b0:02X}  during[min 0x{dmin:02X}..max 0x{dmax:02X}]  -> {cut}")
    print(f"        D3 trace: {trace}")

# Also: torque request 0x0A7 D7 per pull (engine torque to driveline)
print("\nPer-pull engine torque request (0x0A7 D7):")
m11=at(0x0A7)
for i,(pa,pb) in enumerate(PULLS,1):
    base=[dd[6] for t,dd in win(m11,pa-0.6,pa-0.05)]
    during=[dd[6] for t,dd in win(m11,pa,pb+0.2)]
    b0=max(base) if base else 0; dmin=min(during) if during else 0
    print(f"  pull #{i}: before~0x{b0:02X}  during min=0x{dmin:02X}  {'(dip)' if dmin<b0*0.6 else ''}")
