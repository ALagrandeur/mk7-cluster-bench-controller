# -*- coding: utf-8 -*-
import os, bisect, statistics
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
t0=rows[0][0]
def sec(ts):return (ts-t0)/1e6
def u16(f,o): return f[o]|(f[o+1]<<8)
def F(cid): return [(sec(ts),dd) for ts,c,dd in rows if c==cid]
eng=F(0x118); m11=F(0x0A7); b2=F(0x0B2); m12=F(0x0A8)

def nearest(series,t):
    ts=[x[0] for x in series]; i=bisect.bisect_left(ts,t)
    i=min(max(i,0),len(series)-1); return series[i][1]

# For each engagement level bucket, gather concurrent torque & slip
import collections
buckets=collections.defaultdict(lambda:{'d6':[],'d7':[],'slip':[],'m12d8':[]})
for t,d in eng:
    lvl=d[2]
    k = 'FULL(>=E0)' if lvl>=0xE0 else ('HIGH(A0-DF)' if lvl>=0xA0 else ('MID(40-9F)' if lvl>=0x40 else 'LOW(<40)'))
    m=nearest(m11,t); wf=nearest(b2,t); mm=nearest(m12,t)
    rear=(u16(wf,0)+u16(wf,2))//2; front=(u16(wf,4)+u16(wf,6))//2
    buckets[k]['d6'].append(m[5]); buckets[k]['d7'].append(m[6])
    buckets[k]['slip'].append(front-rear); buckets[k]['m12d8'].append(mm[7])

def stat(v):
    v=sorted(v); n=len(v)
    return f"med0x{v[n//2]:02X} p90 0x{v[int(n*0.9)]:02X} (n={n})" if n else "-"
print("Pour chaque niveau d'engagement 0x118 D3, valeurs concomitantes:\n")
for k in ['FULL(>=E0)','HIGH(A0-DF)','MID(40-9F)','LOW(<40)']:
    b=buckets[k]
    if not b['d7']: continue
    sl=sorted(b['slip'])
    print(f"  {k:12s}: 0x0A7 D6 {stat(b['d6'])} | D7 {stat(b['d7'])} | 0x0A8 D8 {stat(b['m12d8'])}")
    print(f"  {'':12s}  slip avant-arriere med={sl[len(sl)//2]} p90={sl[int(len(sl)*0.9)]} max={max(sl)}")

# Is 0x0A7 D6/D7 a counter/mux? check if low nibble cycles
d7vals=[d[6] for _,d in m11[:200]]
print("\n0x0A7 D7 premiers echantillons:", " ".join("%02X"%v for v in d7vals[:20]))
print("0x0A7 D6 premiers echantillons:", " ".join("%02X"%d[5] for _,d in m11[:20]))
# distinct count to gauge if it's smooth or random
print(f"0x0A7 D7: {len(set(d[6] for _,d in m11))} valeurs distinctes / {len(m11)} trames")
