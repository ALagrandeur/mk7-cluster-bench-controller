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
def frames(cid,conds):
    out=[]
    for s in conds:
        out+=[data for (c,data) in logs[s] if c==cid]
    return out

def make_crc8(poly,init,xorout,refin,refout):
    def reflect8(b):
        r=0
        for i in range(8):
            if b&(1<<i): r|=1<<(7-i)
        return r
    def crc(data):
        c=init
        for b in data:
            if refin: b=reflect8(b)
            c^=b
            for _ in range(8):
                c=((c<<1)^poly)&0xFF if (c&0x80) else ((c<<1)&0xFF)
        if refout: c=reflect8(c)
        return c^xorout
    return crc

POLYS=[0x2F,0x1D,0x07,0x39,0x9B,0xD5,0x4D,0x15,0xCB,0x31,0x8D,0x49,0xDB,0xE7,0x5B,0x9C,0x12,0x1A]
INITS=[0xFF,0x00]
XORS=[0xFF,0x00]
REFS=[(False,False),(True,True)]
# input constructions: function(data, did) -> list of bytes for CRC
def constr(name):
    if name=="DID+D2..D8": return lambda dd,did:[did]+list(dd[1:8])
    if name=="D2..D8+DID": return lambda dd,did:list(dd[1:8])+[did]
    if name=="DID+D3..D8": return lambda dd,did:[did]+list(dd[2:8])
    if name=="D3..D8+DID": return lambda dd,did:list(dd[2:8])+[did]
    if name=="DID+D1..D8(D1=0)": return lambda dd,did:[did]+[0]+list(dd[1:8])
    if name=="D2..D8":        return lambda dd,did:list(dd[1:8])  # DID via init only (did ignored)
CNAMES=["DID+D2..D8","D2..D8+DID","DID+D3..D8","D3..D8+DID","DID+D1..D8(D1=0)"]

def solve_did(crc, build, frs):
    # frs: list of frames; group by counter D2&0xF; find DID per counter that makes crc==D1 for all
    groups={}
    for f in frs: groups.setdefault(f[1]&0x0F,[]).append(f)
    table=[None]*16
    for cnt,fl in groups.items():
        sols=[did for did in range(256) if all(crc(build(f,did))==f[0] for f in fl)]
        if len(sols)==1: table[cnt]=sols[0]
        elif len(sols)>1: table[cnt]=-1
        else: return None
    return table

t116=frames(0x116,["IDLE","KEYON"])
t0A7=frames(0x0A7,["IDLE"])[:400]
t120=frames(0x120,["IDLE"])  # sanity: known-good

print("Searching CRC config that reconstructs 0x116 AND validates on 0x0A7...")
winners=[]
for poly in POLYS:
    for init in INITS:
        for xorout in XORS:
            for refin,refout in REFS:
                crc=make_crc8(poly,init,xorout,refin,refout)
                for cn in CNAMES:
                    build=constr(cn)
                    tb=solve_did(crc,build,t116)
                    if tb is None: continue
                    # validate same config reconstructs 0x0A7 (varying payload) cleanly
                    tb2=solve_did(crc,build,t0A7)
                    if tb2 is None: continue
                    winners.append((poly,init,xorout,refin,refout,cn,tb,tb2))

print(f"\n{len(winners)} config(s) reconstruct BOTH 0x116 and 0x0A7:\n")
for poly,init,xorout,refin,refout,cn,tb,tb2 in winners:
    d116=" ".join("%02X"%x if isinstance(x,int) and x>=0 else "M?" for x in tb)
    d0a7=" ".join("%02X"%x if isinstance(x,int) and x>=0 else "M?" for x in tb2)
    print(f"poly=0x{poly:02X} init=0x{init:02X} xor=0x{xorout:02X} refin={refin} refout={refout} build={cn}")
    print(f"    0x116 DataID/cnt: {d116}")
    print(f"    0x0A7 DataID/cnt: {d0a7}")

# sanity print known-good 0x120 with default AUTOSAR to confirm cracker logic
crc_std=make_crc8(0x2F,0xFF,0xFF,False,False)
tb120=solve_did(crc_std,constr("DID+D2..D8"),t120)
print("\nsanity 0x120 (std AUTOSAR DID+D2..D8):", " ".join("%02X"%x for x in tb120) if tb120 else "FAIL")
