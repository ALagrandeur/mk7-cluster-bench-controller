// =====================================================================
//  app_settings.h  —  Réglages persistants (NVS / Preferences)
// =====================================================================
#pragma once
#include <Arduino.h>

struct AppSettings {
  uint8_t  brightness;      // 10..255
  uint8_t  espnowChannel;   // 1..13  (doit correspondre au récepteur)
  uint8_t  relayActiveHigh; // 0 = actif BAS, 1 = actif HAUT
  bool     wifiEnabled;     // se connecter au Wi-Fi au démarrage
  char     wifiSsid[33];
  char     wifiPass[65];
};

extern AppSettings g_settings;

void settings_load();   // charge depuis NVS (valeurs par défaut si vide)
void settings_save();   // écrit la structure courante en NVS
