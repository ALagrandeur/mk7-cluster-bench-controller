# -*- coding: utf-8 -*-
import os, collections
ALT=r"C:\Users\AntoineLagrandeur\OneDrive - ÉNERSERV INC\Bureau"
BASE=r"C:\Users\AntoineLagrandeur\OneDrive - ENERSERV INC\Bureau"
d=ALT if os.path.isdir(ALT) else BASE
rows=[]
for line in open(os.path.join(d,"run3.csv"),encoding="utf-8",errors="replace"):
    if line.startswith("Time"):continue
    x=line.strip().split(",")
    if len(x)<6:continue
    try: ts=int(x[0]); cid=int(x[1],16)
    except: continue
    rows.append((ts,cid,[int(x[i],16) if i<len(x) and x[i].strip() else 0 for i in range(6,14)]))
t0=rows[0][0]; dur=(rows[-1][0]-t0)/1e6
def sec(ts):return (ts-t0)/1e6
def u16(f,o): return f[o]|(f[o+1]<<8)
def F(cid): return [(sec(ts),dd) for ts,c,dd in rows if c==cid]

# A. sanity CRC (append) still 100% on key frames
def crc8(data):
    c=0xFF
    for b in data:
        c^=b
        for _ in range(8): c=((c<<1)^0x2F)&0xFF if (c&0x80) else ((c<<1)&0xFF)
    return c^0xFF
SEQ={0x08A:[0xD4]*16,
 0x0A7:[0xD2,0x3D,0xCD,0x28,0x4C,0x14,0x22,0x4B,0x24,0xAC,0xFA,0x55,0x66,0x80,0x0D,0x6C],
 0x0A8:[0x52,0x8C,0x50,0xEE,0x4F,0xA6,0xCC,0xCF,0x7D,0x2F,0x98,0x6B,0x27,0x41,0x9F,0x93],
 0x116:[0xAC]*16,0x106:[0x07]*16}
print(f"run3.csv: {len(rows)} trames, {dur:.1f}s")
print("A. Sanity CRC (append) sur run3:")
for cid,seq in SEQ.items():
    fr=[dd for ts,c,dd in rows if c==cid]
    ok=sum(1 for f in fr if crc8(list(f[1:8])+[seq[f[1]&0x0F]])==f[0])
    print(f"   0x{cid:03X}: {ok}/{len(fr)} {'OK' if ok==len(fr) else 'MISMATCH'}")

# B. engagement timeline -> find launch windows
eng=F(0x118)
print(f"\nB. Engagement 0x118 D3 — max global = 0x{max(d[2] for _,d in eng):02X}")
# bucket 0.5s, print only buckets with engagement>0x30
buck={}
for t,d in eng: buck.setdefault(round(t*2)/2,[]).append(d[2])
windows=[]
prev=-9
for b in sorted(buck):
    v=max(buck[b])
    if v>=0x60:
        if b-prev>1.5: windows.append([b,b,v])
        else: windows[-1][1]=b; windows[-1][2]=max(windows[-1][2],v)
        prev=b
print(f"   {len(windows)} fenetre(s) d'engagement fort (>=0x60):")
for w in windows: print(f"     t={w[0]:.1f}..{w[1]:.1f}s  max=0x{w[2]:02X}")

# C+D. For each strong window, correlate engagement with torque 0x0A7 D7 + slip
def win(series,a,b): return [(t,d) for t,d in series if a<=t<=b]
m11=F(0x0A7); esp14=F(0x08A); b2=F(0x0B2); fd=F(0x0FD); ped=F(0x121); m12=F(0x0A8); e10=F(0x116)
for wi,w in enumerate(windows,1):
    a,b=w[0]-1.0,w[1]+1.0
    print(f"\n=== Lancement #{wi}  t={a:.1f}..{b:.1f}s ===")
    e=win(eng,a,b)
    print("  0x118 D3 engagement: "+" ".join("%02X"%d[2] for _,d in e[::max(1,len(e)//24)]))
    t7=win(m11,a,b)
    print("  0x0A7 D7 (couple)  : "+" ".join("%02X"%d[6] for _,d in t7[::max(1,len(t7)//24)]))
    print("  0x0A7 D6           : "+" ".join("%02X"%d[5] for _,d in t7[::max(1,len(t7)//24)]))
    e14=win(esp14,a,b)
    print(f"  0x08A D8 (plafond) : min=0x{min(d[7] for _,d in e14):02X} max=0x{max(d[7] for _,d in e14):02X}")
    t12=win(m12,a,b); print(f"  0x0A8 D7 max=0x{max(d[6] for _,d in t12):02X} D8 max=0x{max(d[7] for _,d in t12):02X}")
    t10=win(e10,a,b); print(f"  0x116 D8 range 0x{min(d[7] for _,d in t10):02X}-0x{max(d[7] for _,d in t10):02X}")
    # slip: front (off4,6) vs rear (off0,2)
    bb=win(b2,a,b)
    if bb:
        rear=[ (u16(d,0)+u16(d,2))//2 for _,d in bb]
        front=[(u16(d,4)+u16(d,6))//2 for _,d in bb]
        slipmax=max(f-r for f,r in zip(front,rear))
        print(f"  0x0B2 slip avant-arriere max = {slipmax} (front>rear sur gravier?)  front_max={max(front)} rear_max={max(rear)}")
    pp=win(ped,a,b); print(f"  0x121 D3 pedale max=0x{max(d[2] for _,d in pp):02X}")
    sp=win(fd,a,b); print(f"  0x0FD vitesse max~{max(u16(d,4) for _,d in sp)//100} km/h")

# E. global correlation engagement vs 0x0A7 D7 (what torque -> what engagement)
print("\n=== CORRELATION globale: pour atteindre engagement E, couple 0x0A7 D7 etait ? ===")
# align by nearest timestamp (both ~10ms..)
import bisect
m11t=[t for t,_ in m11]; m11v=[d[6] for _,d in m11]
bins=collections.defaultdict(list)
for t,d in eng:
    i=bisect.bisect_left(m11t,t)
    if 0<i<len(m11t): bins[d[2]//0x20*0x20].append(m11v[min(i,len(m11v)-1)])
for k in sorted(bins):
    vs=bins[k]; vs.sort()
    print(f"  engagement 0x{k:02X}-0x{k+0x1F:02X}: 0x0A7 D7 median=0x{vs[len(vs)//2]:02X} (n={len(vs)})")
