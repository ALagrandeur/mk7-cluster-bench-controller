# VW MQB / MK7 CAN ID Reference

> ## ⚠️ Convention de fiabilité
>
> Ce document distingue 3 niveaux de confiance :
>
> - 🟢 **CONFIRMÉ** — observé directement dans un log de **ce véhicule** (Golf Alltrack 2017).
> - 🟡 **DOCUMENTÉ** — provient d'une source publique fiable (openDBC, openpilot) mais pas vérifié
>   sur ce véhicule. Année/option peut différer.
> - 🔴 **DEVINÉ** — extrapolation/placeholder. **NE PAS UTILISER** sans validation.
>
> Sources : [openDBC vw_mqb_2010.dbc](https://github.com/commaai/opendbc/blob/master/opendbc/dbc/vw_mqb_2010.dbc),
> [openpilot VW selfdrive](https://github.com/commaai/openpilot/tree/master/selfdrive/car/volkswagen),
> forums Ross-Tech, captures personnelles.
>
> Tous les IDs sont sur le **Powertrain CAN @ 500 kbps** (Antrieb-CAN) sauf indication.

---

## Pour ton projet (priorité haute)

### Cluster wake-up (CRITIQUE pour le bench)

#### 1. Le wake principal est HARDWARE

Sur cluster **5G1 920 740B** (MK7 highline Alltrack 2017, connecteur 18 broches), le mécanisme
de wake principal est **Klemme 15** = +12V sur pin 16. Sans cette alimentation:
- Cluster en sleep profond, écran noir
- N'écoute pas le CAN
- Ne répond pas aux UDS
- Aucun message bus ne le réveille

**Pinout 18 broches (typique highline MK7)**:

| Pin | Signal | État |
|---|---|---|
| 1 | Kl.30 (+12V batterie) | requis |
| 10 | Kl.31 (GND) | requis |
| **16** | **Kl.15 (+12V allumage)** | **CRITIQUE pour wake** |
| 17 | CAN-H Powertrain | requis pour data |
| 18 | CAN-L Powertrain | requis pour data |

Sur bench: bridge pin 1 ↔ pin 16 = "ignition permanently ON".

#### 2. CAN heartbeat = Kombi_01 (0x30B)

Une fois Kl.15 alimentée et le cluster réveillé, on envoie un heartbeat CAN pour empêcher les
warnings "no comms" et garder le cluster opérationnel.

🟢 **Source: openDBC vw_mqb.dbc** (maintenu en production par comma.ai pour openpilot):

```
BO_ 779 Kombi_01: 8 Gateway_MQB              ← ID 0x30B, 8 bytes, gateway → cluster
 SG_ KBI_ABS_Lampe         : 0|1@1+   → byte 0 bit 0 (lampe ABS)
 SG_ KBI_ESP_Lampe         : 1|1@1+   → byte 0 bit 1 (lampe ESP)
 SG_ KBI_BKL_Lampe         : 2|1@1+   → byte 0 bit 2 (lampe frein)
 SG_ KBI_Airbag_Lampe      : 3|1@1+   → byte 0 bit 3 (lampe airbag)
 SG_ KBI_Lenkung_Lampe     : 5|1@1+   → byte 0 bit 5 (lampe direction)
 SG_ Kombi_01_BZ           : 8|4@1+   → byte 1 nibble bas (counter 0..15)
 SG_ KBI_Anzeigestatus_GRA : 13|2@1+  → byte 1 (cruise display state)
 SG_ KBI_Tankwarnung       : 16|1@1+  → byte 2 bit 0 (low fuel warning)
 SG_ KBI_Oeldruckwarnung   : 22|1@1+  → byte 2 bit 6 (oil pressure warning)
 SG_ KBI_V_Digital         : 24|9@1+  → bytes 3-4 (digital speed display)
 SG_ KBI_angez_Geschw      : 48|10@1+ → bytes 6-7 (analog speed display, 0.32 km/h/bit)
 ... (autres signaux: ACC status, MFA unit, LDW errors, Variante USA, etc.)
```

**Payload pour notre heartbeat** = `00 00 00 00 00 00 00 00`:
- byte 0 = aucune lampe témoin allumée
- byte 1 nibble bas = counter (auto-géré par le serveur)
- tout le reste = neutre (pas de cruise, vitesse digitale=0, etc.)

**Pas de checksum personnalisé**: 0x30B n'est PAS dans `VOLKSWAGEN_MQB_MEB_CONSTANTS`.
Le byte 0 contient des données réelles (lampes), pas un checksum. Notre webui ne fait
qu'incrémenter le counter au byte 1 nibble bas.

**Frames résultantes envoyées** (counter incrémente):

| Counter | Frame |
|---|---|
| 1 | `00 01 00 00 00 00 00 00` |
| 2 | `00 02 00 00 00 00 00 00` |
| 3 | `00 03 00 00 00 00 00 00` |
| ... | ... |

Doit être envoyé en continu à ~10 Hz pendant que le cluster est utilisé.

#### Pourquoi PAS Klemmen_Status_01 (0x3C0)?

J'avais initialement recommandé `0x3C0 / Klemmen_Status_01` comme wake. **C'était faux** —
relecture attentive du DBC:

```
BO_ 960 Klemmen_Status_01: 4 Gateway_MQB
 SG_ ZAS_Kl_15 : 17|1@1+ ... receivers: Airbag_MQB, BMS_MQB, Motor_*_MQB
                                         ↑ PAS le cluster
```

`Klemmen_Status_01` réveille **engine ECU + airbag + battery management**, pas le cluster.
Sur la voiture complète, c'est utile en parallèle de Kombi_01 (parce que ces ECUs broadcastent
ensuite des messages que le cluster lit). Sur bench cluster-seul, ça ne fait rien d'utile.

#### Si le heartbeat Kombi_01 ne suffit pas

Plus complexe à implémenter (à faire seulement si nécessaire après essai):
- **AUTOSAR Network Management** (NM) frames — chaque ECU émet sa frame NM périodiquement
  (~500ms). Le cluster surveille la présence des autres ECUs sur le bus.
- **Klemmen_Status_01** (0x3C0) en parallèle — pour réveiller engine/airbag virtuels
- **Motor_14** (0x3BE) en parallèle — pour faire croire au cluster qu'il y a un moteur

Ces messages additionnels sont déjà supportés par notre framework (juste activer + configurer
dans la section Coolant ou via le Raw CAN sender).

### Coolant temperature broadcast → notre boost gauge

🔴 **DEVINÉ — aucun ID confirmé pour ce véhicule.** Méthode pour identifier:

1. Sur la voiture qui tourne, sniffer 30s du Powertrain CAN avec SavvyCAN (Live Mode).
2. Filtrer les IDs dont un byte varie de façon monotone quand le moteur chauffe (cold start → warm).
3. Croiser avec [openDBC vw_mqb_2010.dbc](https://github.com/commaai/opendbc/blob/master/opendbc/dbc/vw_mqb_2010.dbc)
   pour identifier le nom (Motor_xx).
4. **Validation finale** : envoyer une valeur précise sur l'ID candidat, puller `0x22D0` sur le cluster
   (cf. section "Cluster ping" plus bas), vérifier que la lecture concorde.

Candidats à éliminer en premier (mention dans la communauté MQB, pas vérifié):
- 🟡 0x3BE / Motor_14 — souvent cité, byte 1 candidat, formule `°C = byte * 0.75 - 48`
- 🟡 0x288 / Motor_06
- 🔴 0x3D2 / Motor_18 — peu probable sur MK7

### Gear position (P/R/N/D/S)

🔴 **DEVINÉ — non confirmé pour ce véhicule.** Méthode:

1. Sniffer le Powertrain CAN en bougeant le sélecteur P→R→N→D→S une position à la fois.
2. Le message dont un nibble change à chaque changement = le bon ID.

Candidats:
- 🟡 0x3DC / Getriebe_11 — TCM DSG, byte 5, nibble bas, valeurs `5=P 6=R 7=N 8=D 9=S` souvent observées
- 🟡 0x540 / Getriebe_02
- 🟡 0x187 / EV_Gearshift (hybrides/eGolf seulement)

### Steering wheel buttons (MFL / GRA)

🔴 **DEVINÉ — non confirmé pour ce véhicule.** Méthode:

1. Sniffer en pressant **un bouton à la fois**, identifier le message dont le contenu change exactement
   pendant la pression.
2. Différents groupes de boutons (cruise, MFL nav, voice) peuvent vivre sur des IDs différents — sniffer
   chaque bouton physiquement.

Candidats:
- 🟡 0x12B / GRA_ACC_01 — cruise + MFL sur certains MQB
- 🟡 0x65D / ORU_01
- 🟡 0x5BF — sur Comfort CAN selon modèles (pas accessible sur Powertrain direct)

> ⚠️ **Piège MQB connu**: `GRA_ACC_01` (et plusieurs messages MQB) embarquent un **counter 4 bits**
> qui doit incrémenter à chaque frame, ET un **checksum 8 bits** custom VW (pas un XOR simple).
> Si après identification de l'ID les boutons ne réagissent pas, c'est presque sûrement à cause de ça.
> L'algorithme exact est dans [openpilot/selfdrive/car/volkswagen/mqbcan.py](https://github.com/commaai/openpilot/tree/master/selfdrive/car/volkswagen) — ~30 lignes Python à porter dans le webui le moment venu.

---

## Autres IDs MQB Powertrain CAN couramment vus

| ID      | Nom              | Contenu                                     |
|---------|------------------|---------------------------------------------|
| 0x040   | Airbag_01        | Status airbag                                |
| 0x086   | LWI_01           | Steering wheel angle sensor                  |
| 0x0FC   | ESP_20           | ESP status                                   |
| 0x0FD   | ESP_21           | ESP frein                                    |
| 0x101   | ESP_05           | Yaw rate, lateral accel                      |
| 0x10B   | ESP_10           | ESP misc                                     |
| 0x121   | ESP_19           | Wheel speeds (4 roues)                       |
| 0x122   | ESP_02           | Brake pressure                               |
| 0x126   | HCA_01           | Heading Control Assist                       |
| 0x12B   | GRA_ACC_01       | Cruise / steering wheel buttons              |
| 0x130   | ACC_06           | Adaptive cruise                              |
| 0x14D   | ACC_10           | ACC hold                                     |
| 0x186   | Motor_16         | Engine RPM (souvent ici sur MQB)             |
| 0x1A0   | ESP_33           | Long. accel                                  |
| 0x1AB   | HCA_04           | Lane assist                                  |
| 0x30C   | ACC_02           | ACC engagement                               |
| 0x320   | Motor_03         | Engine status                                |
| 0x3C0   | Klemmen_Status_01| Terminal/ignition (15, 50, etc.)             |
| 0x3C7   | Motor_14 (var.)  | Variant containing engine temp on some MY    |
| 0x3D5   | Licht_Anf_01     | Light request (BCM → cluster)                |
| 0x3DA   | Gateway_72       | Gateway status                               |
| 0x3DC   | Getriebe_11      | Gear position (DSG/auto)                     |
| 0x3E5   | Kombi_03         | **Cluster → bus** (TX from cluster, info)    |
| 0x40C   | Motor_03         | Motor status alt                             |
| 0x440   | Bremse_X         | Brake variant                                |
| 0x4A0   | Motor_misc       | Motor misc                                   |
| 0x520   | Motor_06 / GRA_Neu | Cruise control older                       |
| 0x571   | Battery_01       | Battery voltage                              |
| 0x572   | Airbag_02        | Airbag                                       |
| 0x575   | Einheiten_01     | Units (km/h vs mph, °C vs °F)                |
| 0x585   | Airbag_03        | Airbag misc                                  |
| 0x65D   | ORU_01           | Online update / MFL                          |
| 0x6B2   | TSK_06           | Travel assist                                |
| 0x6CF   | EPS_01           | Electric power steering                      |

---

## Diagnostic / UDS (ISO 14229)

| ID      | Direction       | Note                                          |
|---------|------------------|-----------------------------------------------|
| **0x714** | tester → cluster | Cluster (J285) diagnostic request — **confirmé Alltrack 2017** |
| **0x77E** | cluster → tester | Cluster diagnostic response — **confirmé Alltrack 2017**       |
| 0x7E0   | tester → ECU     | Engine ECU req                                |
| 0x7E8   | ECU → tester     | Engine ECU resp                               |
| 0x7DF   | tester → all     | OBD-II functional broadcast                   |

**Astuce aliveness cluster** : envoyer à `0x714` la requête `03 22 22 D0 00 00 00 00`
(ReadDataByIdentifier sur DID 0x22D0). Si le cluster répond sur `0x77E` avec `04 62 22 D0 XX`,
le bus/baud est bon et le cluster est en vie. C'est notre meilleur ping.

### DIDs UDS confirmés (Engine ECU @ 0x7E0 / 0x7E8)

Confirmés à partir de logs OBD-II Alltrack 2017 (avril 2026).

| DID     | Nom (VW)            | Format réponse                            | Note                                |
|---------|---------------------|--------------------------------------------|-------------------------------------|
| **0x39C0** | Saugrohrdruck (MAP)              | 2 bytes big-endian, **mbar absolus** | `bar_absolu = (B1*256 + B2) / 1000` |
| **0x202C** | Kühlmitteltemperatur (réelle)    | 2 bytes big-endian, **0.1 °C**       | `°C = (B1*256 + B2) * 0.1`. Confirmé : raw 0x03B1 (945) = 94.5°C |

### Broadcasts CAN confirmés sur le bench (5G1 920 740B)

| ID | Message | Byte/effet | Test confirmant |
|---|---|---|---|
| **0x3C0** | Klemmen_Status_01 | 4 bytes, byte 2 = 0x03, MQB CRC+counter — réveille le cluster (avec Kl.15 hardware) | Avril 2026 — cluster s'allume |
| **0x107** | Motor_04 | byte 3 = `0xED` → tachymètre RPM à fond | Avril 2026 — aiguille RPM max |

### 🎯 Coolant gauge: SOLUTION trouvée via r00li/CarCluster

Le projet [r00li/CarCluster](https://github.com/r00li/CarCluster) (testé en production sur Golf 7 MQB) confirme:

**ID = 0x647 (Motor_09)**, **byte 0 = mapped coolant**, formule **linéaire**:
```
byte_0 = map(temp_C, 50, 130, 0x80, 0xED)
```
- 50°C → 0x80
- 90°C → 0xB6 (centre)
- 130°C → 0xED (max rouge)

**Bytes 1-7 OBLIGATOIRES**: `{0xFD, 0xFF, 0x7F, 0x00, 0x00, 0x00, 0xC1}` — le cluster rejette si ce sont des zéros.

**Frame complète** pour 90°C:
```
0x647   B6 FD FF 7F 00 00 00 C1
```

**Doit être envoyé en parallèle** avec **Motor_Code_01 (0x641)** + **Motor_04 (0x107)** comme contexte "engine ECU alive". L'envoyer seul ne suffit pas. Cycle 50ms (20 Hz).

C'est pourquoi nos premiers tests `0x647 ED 00 00 00 00 00 00 00` ne marchaient pas:
- Bytes 1-7 = 0 → message rejeté
- Pas de Motor_Code_01 / Motor_04 simultané → cluster ne croit pas qu'un moteur tourne

→ Voir le DBC complet généré dans [`vw_mk7_cluster.dbc`](vw_mk7_cluster.dbc).

### DIDs UDS confirmés (Cluster @ 0x714 / 0x77E)

| DID     | Nom probable        | Format réponse                            | Note                                |
|---------|---------------------|--------------------------------------------|-------------------------------------|
| **0x22D0** | Engine coolant temp (affichée) | 1 byte | byte=0x77 (119) → 90°C affichés. Formule probable: `°C = byte * 0.75` (89.25 arrondi à 90) ou `°C = byte − 29`. **À reconfirmer avec plusieurs températures.** |
| 0x0600  | Coding / serial / VIN block    | 23 bytes (multi-frame ISO-TP) | À explorer.                         |

**Test d'aliveness cluster** :
```
TX 0x714  03 22 22 D0 00 00 00 00     # ReadDataByIdentifier(0x22D0)
RX 0x77E  04 62 22 D0 XX AA AA AA     # XX = byte temperature
```
Si on reçoit la réponse, le cluster est vivant et le baudrate est correct.

### ⚠️ Zone neutre du cluster (gauge damping)

**Important pour notre projet boost gauge.** Le cluster MQB applique une zone neutre sur le gauge
de température : tant que la **vraie** température (engine ECU `0x202C`) est entre **~80°C et ~110°C**,
l'aiguille reste plantée au centre ("90°C") sans bouger. Confirmé empiriquement :

| Source                      | Valeur lue       |
|-----------------------------|------------------|
| Engine ECU réel (DID 0x202C) | 94.5°C           |
| Cluster affiché (DID 0x22D0) | 90°C (immobile)  |

**Implication** : pour utiliser le gauge comme boost gauge, le mapping doit **éviter** la zone
80-110°C. Mapper la plage de boost vers 50-130°C (en sautant la zone neutre) garantit que
l'aiguille bouge proportionnellement.

**Méthode de calibration empirique** : envoyer sur le broadcast Motor_xx (ou via raw sender) des
valeurs de byte croissantes (`0x40`, `0x60`, `0x80`, `0xA0`, `0xC0`, `0xE0`) une par une et
observer où l'aiguille décolle des butées de la zone neutre. Les deux seuils trouvés définissent
la plage utile.

Exemple de séquence observée à ~10 Hz:

```
TX 0x7E0  03 22 39 C0 00 00 00 00      # ReadDataByIdentifier(0x39C0)
RX 0x7E8  05 62 39 C0 01 D6 AA AA      # 0x01D6 = 470 mbar = 0.470 bar absolu (vacuum d'idle)
                       └─┬─┘
                       valeur
```

**Plages physiques attendues**:
- Idle gros vacuum: ~0.3 bar absolu (300 mbar)
- Cruise lent: ~0.5–0.7 bar absolu
- Atmosphérique (clé sur ON, moteur off): ~1.0 bar absolu
- Boost normal (Alltrack): 1.5–2.0 bar absolu
- Boost max overboost: ~2.5 bar absolu

DIDs voisins probables (à confirmer):
- `0x39C1` — Atmosphärendruck (pression ambiante, pour calculer le boost relatif)
- `0x3434` — Saugrohrdruck Sollwert (consigne MAP)
- `0xF40B` — Intake manifold pressure (PID OBD-II 0x0B mappé en DID UDS)

---

## Pinout du connecteur cluster MK7 (à confirmer sur ton modèle)

Le cluster MK7 utilise typiquement un connecteur **32 broches** avec deux séries de broches CAN.
**Brochage standard MQB cluster** (à vérifier avec multimètre + ohmmètre — pinout exact dans le ELSAWin/erWin
manual) :

| Pin | Fonction                |
|-----|--------------------------|
| 1   | Tension batterie (+12V Klemme 30) |
| 2   | Masse (Klemme 31) |
| 3   | Klemme 15 (allumage) |
| 16  | CAN High — Powertrain |
| 17  | CAN Low — Powertrain |
| 18  | CAN High — Infotainment (si présent) |
| 19  | CAN Low — Infotainment (si présent) |
| ... | (LIN, K-line, illumination) |

> ⚠️ Confirmer avec le **schéma électrique exact pour Golf Alltrack 2017** (VAG ELSAWin / Bentley manual).
> Les pinouts varient entre 8V0, 5G0, 5Q0... ces préfixes correspondent à différents clusters.

**Comment retrouver les broches CAN sans schéma** :
1. Avec un multimètre en mode résistance, mesurer entre paires de broches **non connectées à 12V/GND** quand
   le cluster est éteint. La paire CAN_H/CAN_L aura ~60Ω entre elles (deux résistances de terminaison de 120Ω en parallèle).
2. Une fois alimenté, CAN_H idle ≈ 2.5V, CAN_L idle ≈ 2.5V, écart ~0V au repos, ~2V actif.
3. À l'oscilloscope, on voit clairement les transitions complémentaires.

---

## Liens utiles

- **openDBC vw_mqb_2010.dbc** : https://github.com/commaai/opendbc/blob/master/opendbc/dbc/vw_mqb_2010.dbc
  (le fichier de référence le plus complet, aligné MQB 2010+)
- **ESP32RET** : https://github.com/collin80/ESP32RET
- **SavvyCAN** : https://www.savvycan.com/
- **Ross-Tech wiki** : http://wiki.ross-tech.com/wiki/index.php/Category:VW (par module / fonction)
- **Forum mk7gti.com / golfmk7.com** : recherches sur "CAN bus cluster" donnent souvent des dumps complets.
