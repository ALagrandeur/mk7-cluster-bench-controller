# -*- coding: utf-8 -*-
import os
ALT=r"C:\Users\AntoineLagrandeur\OneDrive - ÉNERSERV INC\Bureau"
BASE=r"C:\Users\AntoineLagrandeur\OneDrive - ENERSERV INC\Bureau"
d=ALT if os.path.isdir(ALT) else BASE
rows=[]
for line in open(os.path.join(d,"run.csv"),encoding="utf-8",errors="replace"):
    if line.startswith("Time"):continue
    x=line.strip().split(",")
    if len(x)<6:continue
    try: ts=int(x[0]); cid=int(x[1],16)
    except: continue
    rows.append((ts,cid,[int(x[i],16) if i<len(x) and x[i].strip() else 0 for i in range(6,14)]))
t0=rows[0][0]
def sec(ts):return (ts-t0)/1e6
def u16(f,o): return f[o]|(f[o+1]<<8)
# windows: REST (engagement~0) vs FULL (engagement>=0xC0, t=11.3..12.4)
def w(cid,a,b): return [dd for ts,c,dd in rows if c==cid and a<=sec(ts)<=b]
REST=(3.0,9.0); FULL=(11.2,12.5)

print("Comparaison REPOS (eng~0) vs ENGAGEMENT PLEIN (0x118 D3>=0xC0):\n")
def cmp_bytes(cid,name,idxs):
    rest=w(cid,*REST); full=w(cid,*FULL)
    print(f"0x{cid:03X} {name}:")
    for i in idxs:
        rv=[f[i] for f in rest]; fv=[f[i] for f in full]
        rr=f"0x{min(rv):02X}-0x{max(rv):02X}" if rv else "-"
        ff=f"0x{min(fv):02X}-0x{max(fv):02X}" if fv else "-"
        chg="  <== CHANGE" if rv and fv and (max(fv)>max(rv)+8 or min(fv)<min(rv)-8) else ""
        print(f"    D{i+1}: repos {rr:>11}  plein {ff:>11}{chg}")

cmp_bytes(0x118,"engagement (D3)",[2])
cmp_bytes(0x08A,"ESP_14 (D5..D8 = limites couple AWD)",[4,5,6,7])
cmp_bytes(0x0A7,"Motor_11 (D6,D7 = couple)",[5,6,7])
cmp_bytes(0x0A8,"Motor_12 (D7,D8)",[6,7])
cmp_bytes(0x116,"ESP_10 (D8)",[7])
cmp_bytes(0x106,"ESP_05 (D4,D8)",[3,7])
# wheel speeds + slip during full engagement
print("\n0x0B2 roues pendant l'engagement plein (avant vs arriere => glissement?):")
for ph,(a,b) in [("repos",REST),("plein",FULL)]:
    fr=w(0x0B2,a,b)
    if not fr: print(f"  {ph}: -"); continue
    # rear=off0,2 ; front=off4,6
    rl=[u16(f,0) for f in fr]; rr=[u16(f,2) for f in fr]; fl=[u16(f,4) for f in fr]; frt=[u16(f,6) for f in fr]
    print(f"  {ph}: AR[{min(rl)}-{max(rl)},{min(rr)}-{max(rr)}]  AV[{min(fl)}-{max(fl)},{min(frt)}-{max(frt)}]")
