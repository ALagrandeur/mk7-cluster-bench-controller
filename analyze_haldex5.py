# -*- coding: utf-8 -*-
import os, collections
ALT  = r"C:\Users\AntoineLagrandeur\OneDrive - ÉNERSERV INC\Bureau"
BASE = r"C:\Users\AntoineLagrandeur\OneDrive - ENERSERV INC\Bureau"
d = ALT if os.path.isdir(ALT) else BASE
FILES=[("KEY ON ENGINE OFF.csv","KEYON"),("IDLE.csv","IDLE"),("run.csv","RUN"),("run2.csv","RUN2")]
def load(path):
    rows=[]
    with open(path,"r",encoding="utf-8",errors="replace") as fh:
        for line in fh:
            if line.startswith("Time"): continue
            p=line.strip().split(",")
            if len(p)<6: continue
            try: cid=int(p[1],16)
            except: continue
            data=[int(p[i],16) if i<len(p) and p[i].strip() else 0 for i in range(6,14)]
            rows.append((cid,data))
    return rows
logs={s:load(os.path.join(d,f)) for f,s in FILES}
SHORT=["KEYON","IDLE","RUN","RUN2"]
def F(cid,s): return [data for (c,data) in logs[s] if c==cid]

# ---- 0x0B2 wheel speed: decode 4x LE16, show range per condition ----
print("=== 0x0B2 (ESP_19 wheel speed) decoded as 4x uint16 LE, scale test ===")
for s in SHORT:
    frs=F(0x0B2,s)
    if not frs: continue
    def u16(f,o): return f[o]|(f[o+1]<<8)
    w=[[u16(f,o) for o in (0,2,4,6)] for f in frs]
    mx=[max(x[i] for x in w) for i in range(4)]
    mn=[min(x[i] for x in w) for i in range(4)]
    # sample a mid frame
    sample=frs[len(frs)//2]
    print(f"{s:6s} raw max per wheel {mx}  min {mn}")
    print(f"        sample bytes: {' '.join('%02X'%b for b in sample)}  -> LE16 {[u16(sample,o) for o in (0,2,4,6)]}")
# infer scale: at a known cruising speed, raw*scale=kmh. print RUN2 max raw to guess.

# ---- 0x118 pump/status: structure ----
print("\n=== 0x118 (Haldex->car engagement/state) ===")
for s in ["IDLE","RUN2"]:
    frs=F(0x118,s)
    print(f"-- {s}: {len(frs)} frames, first 12:")
    for f in frs[:12]:
        print("   "+" ".join("%02X"%b for b in f))
    # distinct values per byte
    for b in range(8):
        vals=sorted(set(f[b] for f in frs))
        if len(vals)<=8:
            print(f"   D{b+1} distinct: {[ '%02X'%v for v in vals]}")
        else:
            print(f"   D{b+1} range: {min(vals):#04x}..{max(vals):#04x} ({len(vals)} vals)")

# ---- lock-demand baseline bytes across conditions ----
print("\n=== Demand-byte baseline (what the car NATURALLY sends; we must match when transparent) ===")
def byte_stats(cid, idx):
    out={}
    for s in SHORT:
        frs=F(cid,s)
        if not frs: out[s]="-"; continue
        vals=collections.Counter(f[idx] for f in frs)
        common=vals.most_common(3)
        out[s]=",".join("%02X(%d%%)"%(v,100*c//len(frs)) for v,c in common)
    return out
for cid,idxs,name in [(0x08A,[7],"ESP_14 D8=BR_Vorg_Allrad_Max"),
                      (0x0A7,[6,7],"MOTOR_11 D7,D8"),
                      (0x0A8,[7],"MOTOR_12 D8"),
                      (0x116,[7],"ESP_10 D8"),
                      (0x106,[3,7],"ESP_05 D4,D8")]:
    print(f"0x{cid:03X} {name}")
    for i in idxs:
        st=byte_stats(cid,i)
        print(f"    D{i+1}: KEYON {st['KEYON']:>14} | IDLE {st['IDLE']:>14} | RUN {st['RUN']:>14} | RUN2 {st['RUN2']:>14}")
