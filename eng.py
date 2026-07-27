# -*- coding: utf-8 -*-
import os, collections
ALT=r"C:\Users\AntoineLagrandeur\OneDrive - ÉNERSERV INC\Bureau"
BASE=r"C:\Users\AntoineLagrandeur\OneDrive - ENERSERV INC\Bureau"
d=ALT if os.path.isdir(ALT) else BASE
def load(p):
    r=[]
    for line in open(os.path.join(d,p),encoding="utf-8",errors="replace"):
        if line.startswith("Time"):continue
        x=line.strip().split(",")
        if len(x)<6:continue
        try: ts=int(x[0]); cid=int(x[1],16)
        except: continue
        r.append((ts,cid,[int(x[i],16) if i<len(x) and x[i].strip() else 0 for i in range(6,14)]))
    return r
for fn in ["run.csv","run2.csv"]:
    rows=load(fn); t0=rows[0][0]
    e=[((ts-t0)/1e6,dd[2]) for ts,c,dd in rows if c==0x118]
    hi=[(t,v) for t,v in e if v>=0xC0]
    # histogram buckets
    buck=collections.Counter()
    for t,v in e:
        buck[ (v//0x20)*0x20 ]+=1
    print(f"\n{fn}: {len(e)} trames 0x118, engagement>=0xC0 sur {len(hi)} trames")
    print("  histogramme D3:", " ".join(f"0x{k:02X}:{buck[k]}" for k in sorted(buck)))
    if hi:
        print(f"  fenetre forte engagement: t={hi[0][0]:.1f}..{hi[-1][0]:.1f}s, max=0x{max(v for _,v in e):02X}")
        # longest run >=0xC0
        seg=[]; cur=None
        for t,v in e:
            if v>=0xC0:
                if cur is None: cur=[t,t]
                else: cur[1]=t
            else:
                if cur: seg.append(cur); cur=None
        if cur: seg.append(cur)
        seg.sort(key=lambda s:s[1]-s[0],reverse=True)
        print(f"  plus longue plage >=0xC0: {seg[0][1]-seg[0][0]:.2f}s" if seg else "  (pics isoles)")
