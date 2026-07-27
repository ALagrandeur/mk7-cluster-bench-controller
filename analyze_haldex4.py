# -*- coding: utf-8 -*-
import os
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
allframes=collections=__import__("collections").defaultdict(list)
for s,_ in [(s,f) for f,s in FILES]:
    for c,data in logs[s]:
        allframes[c].append(data)

def crc8(data):  # AUTOSAR 0x2F / FF / FF
    c=0xFF
    for b in data:
        c^=b
        for _ in range(8):
            c=((c<<1)^0x2F)&0xFF if (c&0x80) else ((c<<1)&0xFF)
    return c^0xFF

def cs_append(dd,did):   # CONFIRMED formula: D2..D8 then DID
    return crc8(list(dd[1:8])+[did])

# extract DataID table for an ID across all frames (append formula), report match rate
def extract(cid):
    frs=allframes[cid]
    groups={}
    for f in frs: groups.setdefault(f[1]&0x0F,[]).append(f)
    table=[None]*16
    for cnt in range(16):
        fl=groups.get(cnt,[])
        if not fl: continue
        sols=[did for did in range(256) if all(cs_append(f,did)==f[0] for f in fl)]
        table[cnt]=sols[0] if len(sols)==1 else (-1 if sols else None)
    # verify match rate with the unique table
    ok=0; tot=0
    for f in frs:
        cnt=f[1]&0x0F
        if isinstance(table[cnt],int) and table[cnt]>=0:
            tot+=1
            if cs_append(f,table[cnt])==f[0]: ok+=1
    return table,ok,tot,len(frs)

REF={
 0x08A:[0xD4]*16,
 0x0A7:[0xD2,0x3D,0xCD,0x28,0x4C,0x14,0x22,0x4B,0x24,0xAC,0xFA,0x55,0x66,0x80,0x0D,0x6C],
 0x0A8:[0x52,0x8C,0x50,0xEE,0x4F,0xA6,0xCC,0xCF,0x7D,0x2F,0x98,0x6B,0x27,0x41,0x9F,0x93],
 0x106:[0x07]*16, 0x116:[0xAC]*16,
 0x0FD:[0xB4,0xEF,0xF8,0x49,0x1E,0xE5,0xC2,0xC0,0x97,0x19,0x3C,0xC9,0xF1,0x98,0xD6,0x61],
 0x101:[0xAA]*16, 0x086:[0x86]*16,
}
print("=== FINAL: DataID tables from YOUR bus (CRC = AUTOSAR over D2..D8+DID) ===")
for cid in [0x08A,0x0A7,0x0A8,0x116,0x106,0x0FD,0x101,0x086,0x121,0x0AD,0x0B1,0x118]:
    table,ok,tot,n=extract(cid)
    disp=" ".join("%02X"%x if isinstance(x,int) and x>=0 else ("M" if x==-1 else "?") for x in table)
    rate = (100.0*ok/tot) if tot else 0
    refnote=""
    if cid in REF:
        m=all((not isinstance(table[i],int)) or table[i]<0 or table[i]==REF[cid][i] for i in range(16))
        refnote = "  [matches known VW table]" if m else "  [DIFFERS from ref!]"
    print(f"0x{cid:03X}: {disp}")
    print(f"        match {ok}/{tot} ({rate:.1f}%) of {n} frames{refnote}")

# Cross-check: does the OLD (prepend) formula match anything?
def cs_prepend(dd,did): return crc8([did]+list(dd[1:8]))
print("\n=== Sanity: PREPEND (our current firmware) vs APPEND on 0x0A7 ===")
frs=allframes[0x0A7]
tabA=REF[0x0A7]
ok_pre=sum(1 for f in frs if cs_prepend(f,tabA[f[1]&0x0F])==f[0])
ok_app=sum(1 for f in frs if cs_append(f,tabA[f[1]&0x0F])==f[0])
print(f"0x0A7 with VW table: PREPEND match {ok_pre}/{len(frs)} | APPEND match {ok_app}/{len(frs)}")
