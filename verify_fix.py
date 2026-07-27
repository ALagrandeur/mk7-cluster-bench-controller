# -*- coding: utf-8 -*-
import os
ALT=r"C:\Users\AntoineLagrandeur\OneDrive - ÉNERSERV INC\Bureau"
BASE=r"C:\Users\AntoineLagrandeur\OneDrive - ENERSERV INC\Bureau"
d=ALT if os.path.isdir(ALT) else BASE
FILES=["KEY ON ENGINE OFF.csv","IDLE.csv","run.csv","run2.csv"]
def load(p):
    r=[]
    for line in open(os.path.join(d,p),encoding="utf-8",errors="replace"):
        if line.startswith("Time"):continue
        x=line.strip().split(",")
        if len(x)<6:continue
        try:cid=int(x[1],16)
        except:continue
        r.append((cid,[int(x[i],16) if i<len(x) and x[i].strip() else 0 for i in range(6,14)]))
    return r
allf=[]
for f in FILES: allf+=load(f)

# ---- replicate the CORRECTED C firmware exactly ----
def crc8(data):
    c=0xFF
    for b in data:
        c^=b
        for _ in range(8):
            c=((c<<1)^0x2F)&0xFF if (c&0x80) else ((c<<1)&0xFF)
    return c^0xFF
ESP10=0xAC
SEQ={
 0x08A:[0xD4]*16,
 0x0A7:[0xD2,0x3D,0xCD,0x28,0x4C,0x14,0x22,0x4B,0x24,0xAC,0xFA,0x55,0x66,0x80,0x0D,0x6C],
 0x0A8:[0x52,0x8C,0x50,0xEE,0x4F,0xA6,0xCC,0xCF,0x7D,0x2F,0x98,0x6B,0x27,0x41,0x9F,0x93],
 0x116:[ESP10]*16,
 0x106:[0x07]*16,
}
def refresh_crc(cid,data):   # mirror of vw_mqb_refresh_crc (append order)
    seq=SEQ.get(cid)
    if not seq: return None
    cnt=data[1]&0x0F
    crc_in=[data[i+1] for i in range(7)]+[seq[cnt]]
    return crc8(crc_in)

print("Replicating CORRECTED C firmware on real captured frames:")
for cid in [0x08A,0x0A7,0x0A8,0x116,0x106]:
    frs=[dd for c,dd in allf if c==cid]
    ok=sum(1 for dd in frs if refresh_crc(cid,dd)==dd[0])
    print(f"  0x{cid:03X}: {ok}/{len(frs)}  {'OK 100%' if ok==len(frs) else 'MISMATCH!'}")

# sanity: a simulated FWD rewrite produces a self-consistent frame
ex=[dd for c,dd in allf if c==0x08A][100][:]
print("\nFWD rewrite sanity (0x08A): set D8=0x00, recompute CRC")
print("  before:", " ".join("%02X"%b for b in ex))
ex[7]=0x00; ex[0]=refresh_crc(0x08A,ex)
print("  after :", " ".join("%02X"%b for b in ex), "(D1 recomputed, valid by construction)")
