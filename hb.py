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
    data=[int(x[i],16) if i<len(x) and x[i].strip() else 0 for i in range(6,14)]
    rows.append((ts,cid,data))
t0=rows[0][0]
def sec(ts): return (ts-t0)/1e6

# 1) Handbrake: 0x30B KOMBI_01 byte[2] bit7 (0x80). Find transitions.
print("=== 0x30B handbrake bit (D3 & 0x80) transitions ===")
last=None; pulls=[]
for ts,cid,dd in rows:
    if cid!=0x30B: continue
    hb=1 if (dd[2]&0x80) else 0
    if last is not None and hb!=last:
        print(f"  t={sec(ts):7.2f}s  {'PULL (engaged)' if hb else 'release'}   D3=0x{dd[2]:02X}")
        if hb: pulls.append(ts)
    last=hb
print(f"  -> {len(pulls)} engage events on 0x30B")

# also scan ALL bytes of 0x30B for any toggling bit (in case handbrake is elsewhere)
print("\n=== 0x30B per-byte distinct values (last 30% of file) ===")
tcut=t0+(rows[-1][0]-t0)*0.70
f30b=[dd for ts,cid,dd in rows if cid==0x30B and ts>=tcut]
for b in range(8):
    vals=sorted(set(x[b] for x in f30b))
    print(f"  D{b+1}: {[ '%02X'%v for v in vals][:12]}{' ...' if len(vals)>12 else ''}")

# 2) Torque-demand cut on 0x08A D8 (BR_Vorg_Allrad_Max, normally 0xFA): find dips
print("\n=== 0x08A D8 (BR_Vorg_Allrad_Max) — values != 0xFA (torque-demand cuts) ===")
events=[]
prev=None
for ts,cid,dd in rows:
    if cid!=0x08A: continue
    v=dd[7]
    if v!=0xFA:
        events.append((sec(ts),v))
# group consecutive cut samples into bursts
bursts=[]
for s,v in events:
    if not bursts or s-bursts[-1][1]>0.4:
        bursts.append([s,s,set([v])])
    else:
        bursts[-1][1]=s; bursts[-1][2].add(v)
for b in bursts:
    print(f"  cut burst t={b[0]:7.2f}..{b[1]:6.2f}s  values={sorted('%02X'%v for v in b[2])}")
print(f"  -> {len(bursts)} distinct cut bursts on 0x08A D8")

# 3) 0x0B2 rear wheels (off 0,2) vs front (off 4,6): rear->0 while front>0 = handbrake lock
print("\n=== 0x0B2: REAR (D1-2,D3-4) drop to 0 while FRONT (D5-6,D7-8) still turning ===")
def u16(f,o): return f[o]|(f[o+1]<<8)
lockev=[]
for ts,cid,dd in rows:
    if cid!=0x0B2: continue
    rl,rr,fl,fr=u16(dd,0),u16(dd,2),u16(dd,4),u16(dd,6)
    if (rl<200 and rr<200) and (fl>800 or fr>800):
        lockev.append((sec(ts),rl,rr,fl,fr))
bursts2=[]
for e in lockev:
    if not bursts2 or e[0]-bursts2[-1][-1]>0.4:
        bursts2.append([e[0],e[0]])
    else:
        bursts2[-1][1]=e[0]
print(f"  {len(lockev)} frames with rear~0 & front turning, grouped into {len(bursts2)} bursts:")
for b in bursts2:
    print(f"     t={b[0]:7.2f}..{b[1]:6.2f}s")
