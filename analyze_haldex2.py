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
            try: ts=int(p[0]); cid=int(p[1],16); ln=int(p[5])
            except: continue
            data=[]
            for i in range(6,14):
                v=p[i].strip() if i<len(p) else ""
                data.append(int(v,16) if v else 0)
            rows.append((ts,cid,data))
    return rows

logs={s:load(os.path.join(d,f)) for f,s in FILES}

def crc8_autosar(data):
    crc=0xFF
    for b in data:
        crc^=b
        for _ in range(8):
            crc=((crc<<1)^0x2F)&0xFF if (crc&0x80) else ((crc<<1)&0xFF)
    return crc^0xFF

# consecutive frames of an ID within one file (preserve order)
def seq(cid, cond="IDLE", n=18):
    return [data for (ts,c,data) in logs[cond] if c==cid][:n]

print("=== SAMPLE consecutive frames (IDLE) — eyeball counter & CRC ===")
for cid in [0x0A7,0x0A8,0x08A,0x116,0x106,0x120,0x0FD,0x101]:
    print(f"\n0x{cid:03X}:")
    for fr in seq(cid):
        print("   "+" ".join("%02X"%b for b in fr))

# Auto-detect counter byte: which byte position increments by +1 mod 16 (low nibble)
# between consecutive frames most of the time?
def detect_counter(cid):
    frames=[data for (ts,c,data) in logs["IDLE"] if c==cid]
    if len(frames)<20:
        frames=[data for (ts,c,data) in logs["RUN2"] if c==cid]
    best=None
    for pos in range(8):
        for mode,desc in ((0,"lownib"),(1,"hinib"),(2,"fullmod16")):
            inc=0; tot=0
            for i in range(1,len(frames)):
                if mode==0: a=frames[i-1][pos]&0x0F; b=frames[i][pos]&0x0F
                elif mode==1: a=frames[i-1][pos]>>4; b=frames[i][pos]>>4
                else: a=frames[i-1][pos]&0xFF; b=frames[i][pos]&0xFF
                tot+=1
                if (a+1)%16==(b%16 if mode<2 else (b)%16): inc+=1
            r=inc/max(1,tot)
            if best is None or r>best[0]:
                best=(r,pos,desc)
    return best

print("\n=== AUTO-DETECTED alive-counter position ===")
det={}
for cid in [0x0A7,0x0A8,0x08A,0x116,0x106,0x120,0x0FD,0x101,0x086,0x0AD,0x121,0x118]:
    r,pos,desc=detect_counter(cid)
    det[cid]=(pos,desc)
    print(f"0x{cid:03X}: counter at D{pos+1} {desc} (consistency {r*100:.0f}%)")

# Brute force DataID per counter using detected counter byte/nibble, CRC at byte0
def reconstruct(cid):
    pos,desc=det[cid]
    frames=[data for (ts,c,data) in logs["IDLE"]+logs["RUN"]+logs["RUN2"]+logs["KEYON"] if c==cid]
    def cnt_of(fr):
        if desc=="lownib": return fr[pos]&0x0F
        if desc=="hinib": return fr[pos]>>4
        return fr[pos]&0x0F
    table=[None]*16
    for cnt in range(16):
        fr=[f for f in frames if cnt_of(f)==cnt]
        if not fr: continue
        sol=[]
        for did in range(256):
            if all(crc8_autosar([did]+list(f[1:8]))==f[0] for f in fr):
                sol.append(did)
        if len(sol)==1: table[cnt]=sol[0]
        elif len(sol)>1: table[cnt]=-1  # multi
    return table

print("\n=== DataID reconstruction with detected counter (CRC over [DID,D2..D8], CRC=D1) ===")
for cid in [0x0A7,0x0A8,0x08A,0x116,0x106,0x120,0x0FD,0x101,0x121,0x0AD,0x086]:
    t=reconstruct(cid)
    disp=" ".join(("%02X"%x if isinstance(x,int) and x>=0 else ("M" if x==-1 else "?")) for x in t)
    nfound=sum(1 for x in t if isinstance(x,int) and x>=0)
    print(f"0x{cid:03X}: [{disp}]  ({nfound}/16 solved)")
