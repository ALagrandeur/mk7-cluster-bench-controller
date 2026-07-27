# Télécommande relais 12V — ESP32-S3 AMOLED ↔ ESP32

Interface tactile **style iOS** sur une carte **Waveshare ESP32-S3-Touch-AMOLED-1.8**
qui envoie des commandes **ON / OFF** en **ESP-NOW (broadcast)** à un second ESP32
(DevKit standard) pilotant un **relais 12V** à distance.

```
┌─────────────────────────┐        ESP-NOW (2.4 GHz)        ┌──────────────────────┐
│  ÉMETTEUR (AMOLED 1.8")  │  ····· broadcast FF:FF:… ·····> │  RÉCEPTEUR (DevKit)  │
│  Boutons ON/OFF + UI     │ <···· accusé (état relais) ···· │  Relais 12V (GPIO4)  │
└─────────────────────────┘                                 └──────────────────────┘
```

---

## 1. Contenu

| Dossier | Rôle |
|---|---|
| `Emetteur_AMOLED/` | Firmware de la carte AMOLED (interface + envoi des commandes) |
| `Recepteur_Relais/` | Firmware de l'ESP32 qui actionne le relais |
| `lv_conf.h` | Configuration LVGL **à copier dans le dossier `libraries`** |

---

## 2. Librairies (Arduino IDE)

Dans **Outils → Gérer les bibliothèques**, installer :

| Librairie | Version |
|---|---|
| **GFX Library for Arduino** (moononournation) | **1.4.9** |
| **lvgl** | **8.4.0** |

Et le **cœur ESP32** (Gestionnaire de cartes) : **esp32 by Espressif ≥ 3.0.6**
(URL à ajouter dans *Préférences* si absent :
`https://espressif.github.io/arduino-esp32/package_esp32_index.json`)

### ⚠️ Étape obligatoire : `lv_conf.h`
Copier le fichier **`lv_conf.h`** (fourni à la racine de ce dossier) dans :

```
Documents/Arduino/libraries/lv_conf.h
```

…c.-à-d. **à côté** du dossier `lvgl`, *pas à l'intérieur*. Sans ça, LVGL ne compile pas.

---

## 3. Réglages carte

### Émetteur (AMOLED 1.8")
- Carte : **ESP32S3 Dev Module**
- **PSRAM : OPI PSRAM**
- Flash Size : **16MB (128Mb)**
- Partition Scheme : **16M Flash (3MB APP/9.9MB FATFS)**
- USB CDC On Boot : **Enabled**

### Récepteur (DevKit)
- Carte : **ESP32 Dev Module** (réglages par défaut)

> Les deux téléversements se font normalement (USB-C / micro-USB).

---

## 4. Câblage du récepteur (relais)

| ESP32 (récepteur) | Module relais |
|---|---|
| GPIO **4** | IN (signal) |
| 5V (ou 3V3 selon le module) | VCC |
| GND | GND |

- Le **12V** de puissance passe par les bornes **COM / NO** du relais (côté charge),
  **jamais** par l'ESP32.
- Si le module relais a un cavalier **JD-VCC**, alimente sa partie bobine en 5V.
- La **masse (GND)** de l'alim ESP32 et celle de l'alim 12V doivent être **communes**
  uniquement si nécessaire pour ton montage ; le contact du relais lui est isolé.

> GPIO et LED d'état sont modifiables en haut de `Recepteur_Relais.ino`
> (`RELAY_PIN`, `STATUS_LED`).

---

## 5. Utilisation

### Écran d'accueil
- **Gros bouton vert ON** / **rouge OFF** → envoient la commande au relais.
- **Pilule d'état** : « Récepteur connecté » (vert) dès qu'un accusé est reçu,
  sinon « Hors ligne ».
- **Roue crantée** (haut-droite) → ouvre les **Réglages**.

### Réglages
- **Luminosité** : curseur (registre matériel SH8601, 10–255).
- **Canal ESP-NOW** : `−` / `+` (1–13). **Doit être identique** au récepteur.
- **Logique relais** : **BAS** (actif LOW) ou **HAUT** (actif HIGH). Le choix est
  transmis dans chaque commande → le récepteur s'adapte automatiquement.
- **Wi-Fi** : activer + SSID + mot de passe (clavier tactile). *Optionnel* ;
  un changement Wi-Fi nécessite un redémarrage.

### Boutons physiques
| Bouton | Action |
|---|---|
| **BOOT** (appui court) | **OK** — valide l'élément en surbrillance |
| **BOOT** (appui long) | passe à l'élément **suivant** (navigation sans le tactile) |
| **PWR** (appui court) | **Retour** |
| **PWR** (appui long > 6 s) | extinction matérielle (géré par la carte) |

> L'écran est **tactile** : tu peux tout faire au doigt, les boutons sont un complément.

---

## 6. Canal & appairage

- Communication en **broadcast** : **aucun appairage**. Tout récepteur sur le **même
  canal** reçoit la commande.
- Le récepteur écoute sur `ESPNOW_CHANNEL` (défaut **1**, en haut du `.ino`).
  S'il faut changer, mets **le même canal** des deux côtés.
- Si tu actives le **Wi-Fi** sur l'émetteur, le canal ESP-NOW devient celui de ta box ;
  règle alors le récepteur sur ce canal (ou laisse le Wi-Fi désactivé pour garder le
  canal fixe).

---

## 7. Dépannage

| Symptôme | Piste |
|---|---|
| Écran noir / rien ne s'affiche | Vérifier PSRAM = **OPI PSRAM** et que `lv_conf.h` est bien dans `libraries/`. |
| Couleurs inversées/bizarres | Passer `LV_COLOR_16_SWAP` à `0` dans `lv_conf.h` (et inversement). |
| Image décalée sur le bord | Ajuster les offsets du constructeur `Arduino_SH8601` dans `hw_display.cpp`. |
| Tactile décalé/inversé | Inverser X ou Y dans `ft3168_read()` (`x = LCD_WIDTH-1-x`, etc.). |
| Le relais s'active à l'envers | Changer **Logique relais** (BAS/HAUT) dans les réglages. |
| « Hors ligne » en permanence | Même **canal** des deux côtés ? Récepteur alimenté ? Distance/obstacles ? |
| Erreur compile `lv_conf.h` introuvable | Le fichier doit être dans `Documents/Arduino/libraries/`, pas dans le sketch. |
| Récepteur : signature `on_recv` | Cœur esp32 **≥ 3.0**. Pour un cœur 2.x, ancienne signature `(const uint8_t*mac,…)`. |

---

## 8. Sécurité

- Le relais commute du **12V** : respecte le calibre (courant) de ton relais et de tes fils.
- Au démarrage, le récepteur force le relais sur **OFF** (`DEFAULT_ACTIVE_HIGH`).
- En broadcast, n'importe quel émetteur sur le canal peut commander le relais : si tu veux
  sécuriser, on pourra ajouter le chiffrement ESP-NOW (PMK/LMK) ou un appairage MAC.
