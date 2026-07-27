# -*- coding: utf-8 -*-
import os, collections

BASE = r"C:\Users\AntoineLagrandeur\OneDrive - ENERSERV INC\Bureau"
# OneDrive accent: try both spellings
ALT  = r"C:\Users\AntoineLagrandeur\OneDrive - ÉNERSERV INC\Bureau"
def base_dir():
    for d in (BASE, ALT):
        if os.path.isdir(d): return d
    # fall back: search user dir
    return BASE

FILES = ["KEY ON ENGINE OFF.csv", "IDLE.csv", "run.csv", "run2.csv"]
SHORT = ["KEYON", "IDLE", "RUN", "RUN2"]

def load(path):
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        first = True
        for line in fh:
            if first:
                first = False
                if line.startswith("Time"): continue
            p = line.strip().split(",")
            if len(p) < 6: continue
            try:
                ts = int(p[0]); cid = int(p[1], 16); ln = int(p[5])
            except ValueError:
                continue
            data = []
            for i in range(6, 6+8):
                if i < len(p) and p[i].strip() != "":
                    try: data.append(int(p[i], 16))
                    except ValueError: data.append(0)
                else:
                    data.append(0)
            rows.append((ts, cid, ln, data))
    return rows

d = base_dir()
logs = {}
for f, s in zip(FILES, SHORT):
    fp = os.path.join(d, f)
    logs[s] = load(fp)
    print(f"loaded {s:6s} {len(logs[s]):7d} frames from {f}")

# ---------- 1. INVENTORY ----------
print("\n=== INVENTORY: frame count per ID per condition ===")
ids = set()
counts = {s: collections.Counter() for s in SHORT}
spans = {s: {} for s in SHORT}   # id -> (first_ts,last_ts,n) for period
for s in SHORT:
    for ts, cid, ln, data in logs[s]:
        ids.add(cid); counts[s][cid]+=1
        if cid not in spans[s]: spans[s][cid]=[ts,ts,0]
        spans[s][cid][1]=ts; spans[s][cid][2]+=1
print(f"{'ID':>5} | {'KEYON':>6} {'IDLE':>6} {'RUN':>6} {'RUN2':>6} | period_ms(IDLE)")
for cid in sorted(ids):
    line=f"0x{cid:03X} |"
    for s in SHORT:
        line+=f" {counts[s].get(cid,0):6d}"
    # period in IDLE
    per=""
    sp=spans["IDLE"].get(cid)
    if sp and sp[2]>2:
        per=f" {((sp[1]-sp[0])/1000.0)/(sp[2]-1):8.1f}"
    print(line+" |"+per)

# ---------- CRC ----------
def crc8_autosar(data):
    crc=0xFF
    for b in data:
        crc^=b
        for _ in range(8):
            crc=((crc<<1)^0x2F)&0xFF if (crc&0x80) else ((crc<<1)&0xFF)
    return crc^0xFF

def calc_cs(data, didseq):
    cnt=data[1]&0x0F
    crc_in=[didseq[cnt]]+list(data[1:8])
    return crc8_autosar(crc_in)

# OpenHaldex reference DataID tables (what our X2 uses)
REF = {
 0x08A:[0xD4]*16,
 0x0A7:[0xD2,0x3D,0xCD,0x28,0x4C,0x14,0x22,0x4B,0x24,0xAC,0xFA,0x55,0x66,0x80,0x0D,0x6C],
 0x0A8:[0x52,0x8C,0x50,0xEE,0x4F,0xA6,0xCC,0xCF,0x7D,0x2F,0x98,0x6B,0x27,0x41,0x9F,0x93],
 0x106:[0x07]*16,
 0x116:[0x05]*16,      # candidate A
 0x0AD:[0x3F,0x69,0x39,0xDC,0x94,0xF9,0x14,0x64,0xD8,0x6A,0x34,0xCE,0xA2,0x55,0xB5,0x2C],
 0x0FD:[0xB4,0xEF,0xF8,0x49,0x1E,0xE5,0xC2,0xC0,0x97,0x19,0x3C,0xC9,0xF1,0x98,0xD6,0x61],
 0x121:[0xE9,0x65,0xAE,0x6B,0x7B,0x35,0xE5,0x5F,0x4E,0xC7,0x86,0xA2,0xBB,0xDD,0xEB,0xB4],
 0x101:[0xAA]*16,
 0x086:[0x86]*16,
}

# ---------- 2. CRC RECONSTRUCTION (brute force the real DataID per counter) ----------
# gather all frames per ID across all logs
byid=collections.defaultdict(list)
for s in SHORT:
    for ts,cid,ln,data in logs[s]:
        byid[cid].append(data)

def reconstruct(cid):
    frames=byid[cid]
    table=[None]*16
    ok_counter=[0]*16
    tot_counter=[0]*16
    for cnt in range(16):
        fr=[fdata for fdata in frames if (fdata[1]&0x0F)==cnt]
        tot_counter[cnt]=len(fr)
        if not fr: continue
        sol=[]
        for did in range(256):
            good=True
            for fdata in fr:
                if crc8_autosar([did]+list(fdata[1:8]))!=fdata[0]:
                    good=False;break
            if good: sol.append(did)
        if len(sol)==1: table[cnt]=sol[0]
        elif len(sol)>1: table[cnt]=("multi",sol[:6])
        # count matches for reference if known
    return table,tot_counter

print("\n=== CRC / DataID RECONSTRUCTION (brute-forced from YOUR bus) ===")
TARGETS=[0x08A,0x0A7,0x0A8,0x106,0x116,0x0AD,0x0FD,0x121,0x101,0x086,0x118,0x107,0x09F,0x120,0x11D,0x11E,0x101,0x135]
for cid in TARGETS:
    if cid not in byid:
        continue
    table,tot=reconstruct(cid)
    # is it constant?
    realvals=[t for t in table if isinstance(t,int)]
    constant = len(set(realvals))==1 and len(realvals)>=1
    refd=REF.get(cid)
    # compare with ref
    cmp=""
    if refd:
        match=all((table[i] is None) or (isinstance(table[i],int) and table[i]==refd[i]) for i in range(16))
        cmp = "== REF OK" if match else "!! DIFFERS from REF"
    disp=[("%02X"%t if isinstance(t,int) else ("?" if t is None else "M")) for t in table]
    print(f"0x{cid:03X} n={len(byid[cid]):6d} const={constant} {cmp}")
    print(f"      real DataID/counter: {' '.join(disp)}")
    if refd:
        print(f"      ref  DataID/counter: {' '.join('%02X'%x for x in refd)}")

# special: 0x116 test both candidates explicitly
if 0x116 in byid:
    fr=byid[0x116]
    for cand,name in ((0x05,"A=0x05"),(0xAC,"B=0xAC")):
        ok=sum(1 for f in fr if crc8_autosar([cand]+list(f[1:8]))==f[0])
        print(f"  0x116 candidate {name}: {ok}/{len(fr)} CRC match")

print("\nDONE part1")
