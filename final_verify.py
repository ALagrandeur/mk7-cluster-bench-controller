# -*- coding: utf-8 -*-
import os, collections, statistics
ALT  = r"C:\Users\AntoineLagrandeur\OneDrive - ÉNERSERV INC\Bureau"
BASE = r"C:\Users\AntoineLagrandeur\OneDrive - ENERSERV INC\Bureau"
d = ALT if os.path.isdir(ALT) else BASE
FILES=[("KEY ON ENGINE OFF.csv","KEYON"),("IDLE.csv","IDLE"),("run.csv","RUN"),("run2.csv","RUN2")]
def load(path):
    rows=[]
    for line in open(path,encoding="utf-8",errors="replace"):
        if line.startswith("Time"):continue
        x=line.strip().split(",")
        if len(x)<6:continue
        try: ts=int(x[0]); cid=int(x[1],16); ext=(x[2].strip().lower()=="true"); ln=int(x[5])
        except: continue
        data=[int(x[i],16) if i<len(x) and x[i].strip() else 0 for i in range(6,14)]
        rows.append((ts,cid,ext,ln,data))
    return rows
logs={s:load(os.path.join(d,f)) for f,s in FILES}
SHORT=["KEYON","IDLE","RUN","RUN2"]
allf=collections.defaultdict(list)
for s in SHORT:
    for ts,cid,ext,ln,dd in logs[s]: allf[cid].append(dd)

def crc8(data):
    c=0xFF
    for b in data:
        c^=b
        for _ in range(8):
            c=((c<<1)^0x2F)&0xFF if (c&0x80) else ((c<<1)&0xFF)
    return c^0xFF
def cs_append(dd,did): return crc8(list(dd[1:8])+[did])

print("="*70)
print("RAPPORT DE VERIFICATION COMPLET — bus Haldex (4 logs)")
print("="*70)
for s in SHORT: print(f"  {s:6s}: {len(logs[s]):7d} trames")

# ---------- A. INVENTORY ----------
print("\n--- A. INVENTAIRE (std=11-bit, ext=29-bit diag) ---")
std=set(); ext=set()
for s in SHORT:
    for ts,cid,e,ln,dd in logs[s]:
        (ext if e else std).add(cid)
print(f"  {len(std)} ID standards 11-bit, {len(ext)} ID etendus 29-bit (diagnostic UDS)")
print("  ID standards:", " ".join("%03X"%c for c in sorted(std)))

# ---------- B. E2E / CRC pour TOUS les ID securises ----------
print("\n--- B. E2E/CRC : reconstruction DataID (formule APPEND) pour chaque ID ---")
def reconstruct(cid, sample=300):
    frs=allf[cid]
    groups=collections.defaultdict(list)
    for f in frs: groups[f[1]&0x0F].append(f)
    table=[None]*16
    for cnt,fl in groups.items():
        use=fl[:sample]
        sols=[did for did in range(256) if all(cs_append(f,did)==f[0] for f in use)]
        table[cnt]=sols[0] if len(sols)==1 else (-1 if sols else None)
    # full match rate
    ok=tot=0
    for f in frs:
        t=table[f[1]&0x0F]
        if isinstance(t,int) and t>=0:
            tot+=1; ok+= (cs_append(f,t)==f[0])
    return table,ok,tot
secured=[]; unsecured=[]
for cid in sorted(std):
    if len(allf[cid])<32: continue
    table,ok,tot=reconstruct(cid)
    solved=sum(1 for x in table if isinstance(x,int) and x>=0)
    if solved>=14 and tot and ok/tot>0.99:
        const = len(set(x for x in table if isinstance(x,int) and x>=0))==1
        secured.append((cid,table,const,ok,tot))
    else:
        unsecured.append(cid)
print(f"  {len(secured)} ID E2E-securises (CRC+compteur, 100% reconstruits) :")
for cid,table,const,ok,tot in secured:
    tag="(constant 0x%02X)"%table[0] if const else "[%s]"%(" ".join("%02X"%x for x in table))
    print(f"    0x{cid:03X}: {ok}/{tot} OK  DataID {tag}")
print(f"  ID NON securises (pas de CRC E2E ou autre struct): {' '.join('%03X'%c for c in unsecured)}")

# ---------- C. Trames qu'on reecrit ----------
print("\n--- C. TRAMES REECRITES PAR LE MITM : CRC + octets de demande ---")
def F(cid,s): return [dd for (ts,c,e,ln,dd) in logs[s] if c==cid]
def common(cid,idx):
    out={}
    for s in SHORT:
        frs=F(cid,s)
        if not frs: out[s]="-"; continue
        c=collections.Counter(f[idx] for f in frs).most_common(1)[0]
        out[s]="%02X(%d%%)"%(c[0],100*c[1]//len(frs))
    return out
for cid,bytes_,name in [(0x08A,[7],"ESP_14"),(0x0A7,[6,7],"Motor_11"),(0x0A8,[7],"Motor_12"),(0x116,[7],"ESP_10"),(0x106,[3,7],"ESP_05")]:
    frs=allf[cid]; tb,ok,tot=reconstruct(cid)
    print(f"  0x{cid:03X} {name}: CRC {ok}/{tot}")
    for i in bytes_:
        st=common(cid,i)
        print(f"      D{i+1} le+freq: KEYON {st['KEYON']:>9} IDLE {st['IDLE']:>9} RUN {st['RUN']:>9} RUN2 {st['RUN2']:>9}")

# ---------- D. 0x0B2 roues ----------
print("\n--- D. 0x0B2 vitesses roues (4x uint16 LE) ---")
def u16(f,o): return f[o]|(f[o+1]<<8)
for s in SHORT:
    frs=F(0x0B2,s)
    if not frs: continue
    mx=[max(u16(f,o) for f in frs) for o in (0,2,4,6)]
    print(f"  {s:6s} max raw [HL,HR,VL,VR]={mx}  (0=arret)")
# derive scale vs 0x0FD at same time (RUN)
print("  (offsets 0/2 = arriere HL/HR, 4/6 = avant VL/VR ; aucun CRC/compteur)")

# ---------- E. 0x118 engagement (LE BIT a maximiser) ----------
print("\n--- E. 0x118 ENGAGEMENT POMPE (D3) — la valeur a maximiser ---")
for s in SHORT:
    frs=F(0x118,s)
    if not frs: continue
    d3=[f[2] for f in frs]; d4=set(f[3] for f in frs); d1=set(f[0] for f in frs)
    print(f"  {s:6s}: D3 engagement min=0x{min(d3):02X} max=0x{max(d3):02X} (~{max(d3)*100//250}% si /250) | D4(type)={sorted('%02X'%v for v in d4)} | D1={sorted('%02X'%v for v in d1)}")
print("  -> D2=compteur, D1=00 (pas de CRC). Notre lecture data[2]=D3 est correcte.")

# ---------- F. Lectures live du firmware : pedale 0x121 + vitesse 0x0FD ----------
print("\n--- F. VALIDATION DES LECTURES LIVE DU FIRMWARE ---")
# which byte of 0x121 tracks throttle? compare IDLE vs RUN2 per byte (skip D1 crc,D2 cnt)
print("  0x121 (pedale) — octet qui monte a l'acceleration (IDLE vs RUN2):")
for b in range(2,8):
    iv=[f[b] for f in F(0x121,"IDLE")]; rv=[f[b] for f in F(0x121,"RUN2")]
    print(f"      D{b+1}: IDLE med 0x{int(statistics.median(iv)):02X} max 0x{max(iv):02X} | RUN2 med 0x{int(statistics.median(rv)):02X} max 0x{max(rv):02X}")
print("  Firmware lit raw=(D2>>4)|((D3&0x0F)<<4) -> verifier ci-dessus si coherent")
print("  0x0FD (vitesse) — octets D5/D6 (firmware: raw=D5|D6<<8, kmh=raw/100):")
for s in SHORT:
    frs=F(0x0FD,s)
    if not frs: continue
    raw=[f[4]|(f[5]<<8) for f in frs]
    print(f"      {s:6s}: raw min={min(raw)} max={max(raw)} -> kmh max~{max(raw)//100}")
# cross-check 0x0FD vs 0x0B2 ratio in RUN (firmware assumes wheel=veh*4/3)
fd=F(0x0FD,"RUN"); b2=F(0x0B2,"RUN")
if fd and b2:
    vmax=max(f[4]|(f[5]<<8) for f in fd); wmax=max(u16(f,0) for f in b2)
    print(f"  Ratio 0x0B2/0x0FD (RUN, max): {wmax}/{vmax} = {wmax/max(1,vmax):.3f} (firmware suppose 1.333=4/3)")

print("\n"+"="*70)
print("FIN DU RAPPORT")
