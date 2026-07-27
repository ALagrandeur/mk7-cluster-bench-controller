# 🖥️➡️💻 Migration vers un nouvel ordinateur

Guide pour reprendre **tout le projet MK7** sur un PC neuf. Tout le **code + doc** est
sur GitHub. Seules quelques données locales (captures CAN, mémoire Claude) doivent être
copiées à la main — elles sont volontairement **hors GitHub** (VIN / données sensibles).

Dernière mise à jour : 2026-07-27.

---

## 1. Cloner les 4 dépôts

```bash
# Hub — analyses, DBC, AMOLED_Remote (ce dépôt)
git clone https://github.com/ALagrandeur/mk7-cluster-bench-controller.git

# BOT32 — firmware ESP32 principal (jauge boost, UI web, contrôle mode Haldex) — PUBLIC
git clone https://github.com/ALagrandeur/BOT32.git

# BOT32-HALDEX — X2 (ESP32-CAN-X2) MITM CAN qui force le couplage Haldex — PRIVÉ
git clone https://github.com/ALagrandeur/BOT32-HALDEX.git

# Remote32 — dashboard Microsquirt / P4 (2 branches actives, voir plus bas) — PRIVÉ
git clone https://github.com/ALagrandeur/Remote32.git
```

> Pour les dépôts **privés** (BOT32-HALDEX, Remote32) : sur le nouveau PC, connecte-toi
> à GitHub (`gh auth login` ou identifiants) sinon le clone échouera.

### Branches actives par dépôt

| Dépôt | Branche à utiliser | Contenu |
|---|---|---|
| mk7-cluster-bench-controller | `main` | scripts d'analyse, DBC, `AMOLED_Remote/` |
| BOT32 | `master` | firmware ESP32 Main (v4.5.0) |
| BOT32-HALDEX | `main` | firmware X2 MITM (v3.0.0) |
| Remote32 | `master` **et** `recepteur-p4` | master = AMOLED 1.8" ; recepteur-p4 = **version P4 IDF active** |

```bash
# Remote32 : les deux branches sont poussées. Pour la version P4 active :
cd Remote32 && git checkout recepteur-p4
```

---

## 2. Outils à installer sur le nouveau PC

- **Arduino IDE** (ou `arduino-cli`) + **paquet cartes ESP32** (Espressif) — pour BOT32,
  BOT32-HALDEX, Remote32/master, AMOLED_Remote.
- **ESP-IDF 5.5.4** — uniquement pour `Remote32` branche `recepteur-p4` (dashboard P4,
  LVGL 9.5). La puce est **rév v1.0 → `SELECTS_REV_LESS_V3`**.
- **SavvyCAN** — visualiser/rejouer les captures CAN.
- **VCDS** (ou OBDeleven) — lecture des DID Haldex, calibration température.
- Bibliothèques Arduino : **LVGL**, **GFX_Library_for_Arduino ≥ 1.5.0** (PAS 1.4.9 —
  manque le driver SH8601), **AXP2101** (batterie), lib **MCP2515** (côté Haldex X2).

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

Repères des derniers commits au moment de la migration :
- BOT32 : `0c0a4c5` (v4.5.0 + backup migration)
- BOT32-HALDEX : `8a79a6a` (v3.0.0)
- Remote32 : `master 6a2deae`, `recepteur-p4 f9d5775`
- mk7-cluster : voir `git log` (contient ce fichier)

---

## 5. État du projet (résumé)

- **Jauge boost sur cadran température** : ✅ fonctionne.
- **UI web mobile** (boutons volant, diagnostics, mode Haldex) : ✅.
- **Haldex 3 modes** confirmés en voiture : **STOCK**, **FWD**, **50/50**.
  - 50/50 tient **~95 % à toutes les vitesses** (spoof « immobile + ralenti »).
  - Température embrayage affichée (DID `0x2BF1`, `temp_C = data[5]×2.7 − 241.5`),
    **affichage seul** — la protection thermique native du Haldex suffit (v4.5.0).

Détails complets : `BOT32/ÉTAT_DU_PROJET.md` et les `docs/` de chaque dépôt.
