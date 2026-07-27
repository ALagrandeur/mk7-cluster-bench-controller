#include "app_settings.h"
#include <Preferences.h>

AppSettings g_settings;
static Preferences prefs;

void settings_load() {
  prefs.begin("amoled", true);          // lecture seule
  g_settings.brightness      = prefs.getUChar("bri", 200);
  g_settings.espnowChannel   = prefs.getUChar("ch", 1);
  g_settings.relayActiveHigh = prefs.getUChar("rah", 0);  // actif BAS par défaut
  g_settings.wifiEnabled     = prefs.getBool("wen", false);
  String ssid = prefs.getString("ssid", "");
  String pass = prefs.getString("pass", "");
  prefs.end();

  // garde-fous
  if (g_settings.brightness < 10)               g_settings.brightness = 10;
  if (g_settings.espnowChannel < 1 ||
      g_settings.espnowChannel > 13)            g_settings.espnowChannel = 1;
  if (g_settings.relayActiveHigh > 1)           g_settings.relayActiveHigh = 0;

  ssid.toCharArray(g_settings.wifiSsid, sizeof(g_settings.wifiSsid));
  pass.toCharArray(g_settings.wifiPass, sizeof(g_settings.wifiPass));
}

void settings_save() {
  prefs.begin("amoled", false);         // lecture/écriture
  prefs.putUChar("bri", g_settings.brightness);
  prefs.putUChar("ch",  g_settings.espnowChannel);
  prefs.putUChar("rah", g_settings.relayActiveHigh);
  prefs.putBool ("wen", g_settings.wifiEnabled);
  prefs.putString("ssid", g_settings.wifiSsid);
  prefs.putString("pass", g_settings.wifiPass);
  prefs.end();
}
