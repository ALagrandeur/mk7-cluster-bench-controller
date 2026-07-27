// =====================================================================
//  lv_conf.h  —  Configuration LVGL 8.4 pour ESP32-S3-Touch-AMOLED-1.8
//
//  >>> COPIER CE FICHIER DANS :  Documents/Arduino/libraries/lv_conf.h
//      (à côté du dossier "lvgl", PAS à l'intérieur)
//
//  Les options non listées ici gardent leurs valeurs par défaut LVGL.
// =====================================================================
#ifndef LV_CONF_H
#define LV_CONF_H

#include <stdint.h>

// ---- Couleur ----
#define LV_COLOR_DEPTH      16
#define LV_COLOR_16_SWAP    1     // requis pour l'AMOLED QSPI (octets big-endian)

// ---- Mémoire (utilise malloc système, PSRAM disponible) ----
#define LV_MEM_CUSTOM       1

// ---- Base de temps : millis() d'Arduino ----
#define LV_TICK_CUSTOM                  1
#define LV_TICK_CUSTOM_INCLUDE          "Arduino.h"
#define LV_TICK_CUSTOM_SYS_TIME_EXPR    (millis())

// ---- Rafraîchissement ----
#define LV_DISP_DEF_REFR_PERIOD   16
#define LV_INDEV_DEF_READ_PERIOD  16

// ---- Polices (style iOS : tailles 14/16/20/28) ----
#define LV_FONT_MONTSERRAT_14   1
#define LV_FONT_MONTSERRAT_16   1
#define LV_FONT_MONTSERRAT_20   1
#define LV_FONT_MONTSERRAT_28   1
#define LV_FONT_DEFAULT         &lv_font_montserrat_16

// ---- Thème ----
#define LV_USE_THEME_DEFAULT    1
#define LV_THEME_DEFAULT_DARK   1

// ---- Widgets utilisés (clavier + champ texte) ----
#define LV_USE_KEYBOARD         1
#define LV_USE_TEXTAREA         1

#endif // LV_CONF_H
