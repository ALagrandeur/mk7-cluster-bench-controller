# 🖥️➡️💻 Migration vers un nouvel ordinateur

Guide pour reprendre **tous les projets** (Golf MK7, Westfalia, manette AMOLED, outils) sur
un PC neuf. Tout le **code + doc** est sur GitHub. Seules quelques données locales (captures
CAN, mémoire Claude) doivent être copiées à la main — elles sont volontairement **hors
GitHub** (VIN / données sensibles).

Dernière mise à jour : 2026-10-12 (versions et liste des dépôts). Guide initial : 2026-07-27.

La carte complète « véhicule → appareil → dépôt » est en tête du [`README.md`](README.md).

---

## 1. Cloner les dépôts

### Les 4 dépôts principaux

```bash
# mk7-cluster-bench-controller — banc du combiné MK7 (dormant), analyses, DBC,
# AMOLED_Remote (legacy) et ce guide — PUBLIC (ce dépôt)
git clone https://github.com/ALagrandeur/mk7-cluster-bench-controller.git

# BOT32 — Golf : firmware ESP Main (jauge boost, données live, UI web, effacement des
# codes moteur, commande des modes Haldex) — PUBLIC
git clone https://github.com/ALagrandeur/BOT32.git

# BOT32-HALDEX — Golf : ESP32-CAN-X2 en série sur le bus Haldex (modes STOCK / FWD / 50-50) — PRIVÉ
git clone https://github.com/ALagrandeur/BOT32-HALDEX.git

# Remote32 — Westfalia (X2 émetteur Microsquirt + écran rond P4) et manette universelle
# AMOLED 1.8" — PRIVÉ
git clone https://github.com/ALagrandeur/Remote32.git
```

> Pour les dépôts **privés** (BOT32-HALDEX, Remote32) : sur le nouveau PC, connecte-toi
> à GitHub (`gh auth login` ou identifiants) sinon le clone échouera.

### Dépôts annexes (pas nécessaires pour travailler)

| Dépôt | Visibilité | Statut |
|---|---|---|
| [OpenHaldex-C6-perso](https://github.com/ALagrandeur/OpenHaldex-C6-perso) | privé | copie non modifiée d'OpenHaldex-C6 (upstream V6.01.0), référence seulement, utilisée par aucun appareil |
| [MK7BoostGauge](https://github.com/ALagrandeur/MK7BoostGauge) | — | archivé : ancêtre de BOT32 (Raspberry Pi) |

### Branches à utiliser

| Dépôt | Branche | Contenu |
|---|---|---|
| mk7-cluster-bench-controller | `main` | webui de banc, `can_ids/`, `analysis/`, `AMOLED_Remote/` (legacy) |
| BOT32 | `master` | firmware ESP Main **v4.6.0** + webui (dernière version confirmée en voiture : v4.5.0) |
| BOT32-HALDEX | `main` | firmware X2 Haldex **v3.0.0** |
| Remote32 | `master` **seulement** | `Emetteur_CAN_X2`, `Recepteur_P4_IDF` (version finale **P4-IDF v1.4**, fusionnée dans master), `Recepteur_AMOLED` |

> Remote32 : il n'y a plus besoin de changer de branche. La version P4-IDF v1.4 a été
> fusionnée dans `master` (commit `1dc4bf0`, 2026-08-30). Les branches `recepteur-p4` et
> `final/p4-idf-v1.4` existent encore sur GitHub, mais `master` contient tout.

---

## 2. Outils à installer sur le nouveau PC

- **Arduino IDE** (ou `arduino-cli`) + **paquet cartes ESP32** (Espressif) — pour BOT32,
  BOT32-HALDEX, Remote32 (`Emetteur_CAN_X2`, `Recepteur_AMOLED`) et AMOLED_Remote (legacy).
  La version du cœur conseillée diffère selon le projet : voir le README de chaque dépôt
  (Remote32 : ≥ 3.0.6 ; BOT32-HALDEX : cœur 2.x ou ≥ 3.3.x, échec attendu sur 3.0–3.2,
  version exacte à confirmer).
- **ESP-IDF 5.5.4** — uniquement pour `Remote32/Recepteur_P4_IDF` (dashboard P4, LVGL 9.5,
  versions figées dans `main/idf_component.yml`). La puce est **rév v1.0 →
  `SELECTS_REV_LESS_V3`** (déjà dans `sdkconfig.defaults`).
- **Python 3** — pour la webui de banc de ce dépôt (`pip install -r webui/requirements.txt`)
  et la webui de BOT32.
- **SavvyCAN** — visualiser/rejouer les captures CAN.
- **VCDS** (ou OBDeleven) — lecture des DID Haldex, calibration température.
- **ESP32RET** (collin80) — seulement pour la webui de banc : firmware tiers à flasher sur
  l'ESP32 du banc, à re-télécharger depuis GitHub (pas dans ce dépôt).

Bibliothèques Arduino, par projet :

| Projet | Bibliothèques |
|---|---|
| BOT32 | **ACAN2515** (Pierre Molinaro, ≥ 2.1.x), **ArduinoJson 7.x** |
| BOT32-HALDEX | **MCP_CAN** de coryjfowler (`mcp_can`) + pilote TWAI intégré au cœur |
| Remote32 / Recepteur_AMOLED | **GFX Library for Arduino ≥ 1.5.0** (testé 1.6.6 ; **pas la 1.4.9**, qui n'a pas le pilote SH8601), **lvgl 8.4.0** + `lv_conf.h` dans `Documents/Arduino/libraries/`, **XPowersLib** (PMIC AXP2101 / batterie) |
| AMOLED_Remote (legacy) | écrit pour GFX 1.4.9 + lvgl 8.4.0 ; ne compile probablement plus avec aucune version de GFX (à confirmer) — voir son README |

Détails matériel/pilotes par sous-projet : voir le `README.md` de chaque dépôt.

---

## 3. ⚠️ À copier À LA MAIN (hors GitHub — OneDrive / disque externe)

Ces éléments sont **gitignore volontairement** (VIN / données perso / spécifiques au PC).
Ils NE seront PAS clonés. Copie-les via OneDrive ou une clé USB **avant** de formater :

| Élément | Emplacement actuel | Taille | Pourquoi hors Git |
|---|---|---|---|
| Captures CAN BOT32 | `BOT32/DATA input from CAR/*.csv` | 34 Mo | peut contenir le VIN |
| Captures CAN X2 | `BOT32-HALDEX/INPUT FROM CAR SAVVYCAN/*.csv` | 24 Mo | peut contenir le VIN |
| Config UI locale | `BOT32/webui/config.json` *(commitée)* + `mk7-cluster/webui/config.json` | — | IDs CAN édités |
| **Mémoire Claude** | `~/.claude/projects/C--Users-AntoineLagrandeur-MK7-cluster/memory/` | 161 Ko | ne se synchronise pas automatiquement |
| Réf. OpenHaldex | `mk7-cluster/analysis/openhaldex_fork/` | ~87 Mo | code tiers, jamais redistribué |
| ESP32RET | `mk7-cluster/ESP32RET_Updater/` | — | firmware tiers (re-télécharger depuis collin80/ESP32RET) |

> `mk7-cluster/` = le dossier local de **ce dépôt**. Son nom varie selon les fichiers :
> « MK7 cluster » (chemins codés en dur dans `analysis/replay_analyze.py` et
> `BOT32/tools/derive_bench_frames.py`) ou « MK7-cluster » (`BOT32/CLAUDE.md`, dossier de
> lancement de Claude Code). Garde le même nom sur le nouveau PC si tu veux que ces scripts
> et la mémoire Claude retrouvent leurs chemins.

> Réf. OpenHaldex : une copie existe aussi sur GitHub (OpenHaldex-C6-perso, privé, V6.01.0).
> Que la copie locale soit la même version reste **à confirmer**.

> Les notes sur le contenu de chaque capture sont dans `BOT32/DATA input from CAR/Explications.txt`
> (celle-là **est** sur GitHub, sans VIN).

### La mémoire Claude
Le dossier `memory/` (profil, décisions, IDs CAN confirmés, formules) est **local à ce PC**.
Copie-le sur le nouveau PC au même chemin `~/.claude/projects/.../memory/` pour que Claude
Code retrouve tout le contexte. Le savoir essentiel est **aussi** dans les README/docs des
dépôts (notamment `project_confirmed_can_ids`), donc rien n'est perdu même sans ce dossier.

---

## 4. Vérification rapide sur le nouveau PC

```bash
# Dans chaque dépôt cloné : doit afficher "nothing to commit, working tree clean"
git status
git log --oneline -1     # dernier commit connu
```

Repères des derniers commits connus (2026-10-12) :
- BOT32 `master` : `6d0cb02` (v4.6.0, 2026-10-11)
- BOT32-HALDEX `main` : `8a79a6a` (v3.0.0)
- Remote32 `master` : `1dc4bf0` (fusion de la version finale P4-IDF v1.4, 2026-08-30)
- mk7-cluster-bench-controller `main` : voir `git log` (contient ce fichier)

---

## 5. État du projet (résumé)

### Golf MK7 Alltrack 2017 (BOT32 + BOT32-HALDEX)

- **Jauge boost sur cadran température** : ✅ fonctionne.
- **UI web mobile** (boutons volant, diagnostics, mode Haldex) : ✅.
- **Haldex 3 modes** confirmés en voiture : **STOCK**, **FWD**, **50/50**.
  - 50/50 tient **~95 % à toutes les vitesses** (spoof « immobile + ralenti »).
  - Température embrayage affichée (DID `0x2BF1`, `temp_C = data[5]×2.7 − 241.5`),
    **affichage seul** — la protection thermique native du Haldex suffit (v4.5.0).
- **Effacement des codes moteur** : bouton de l'UI web (cellulaire + PC) ajouté en v4.6.0,
  pas encore confirmé en voiture (v4.5.0 reste la dernière version confirmée en voiture).

### Westfalia (Remote32)

- **ESP32-CAN-X2** (`Emetteur_CAN_X2`) : lit le CAN du Microsquirt et diffuse les données
  (ESP-NOW + WiFi/UDP).
- **Écran rond ESP32-P4 3.4"** (`Recepteur_P4_IDF`) : tableau de bord à cadrans, **version
  finale v1.4**.

### Les deux véhicules

- **Manette universelle ESP32-S3 AMOLED 1.8"** (`Remote32/Recepteur_AMOLED`) : cadrans
  Westfalia + mode Golf (modes Haldex).

### Outils et références

- **Banc du combiné** (ce dépôt) : dormant ; BOT32 a son propre mode banc.
- `AMOLED_Remote/` (ce dépôt) : **legacy**, ancêtre de `Remote32/Recepteur_AMOLED`.
- OpenHaldex-C6-perso : référence non utilisée. MK7BoostGauge : archivé.

Détails complets : `BOT32/ÉTAT_DU_PROJET.md`, le `README.md` de Remote32 et les `docs/` de
chaque dépôt.
