// =====================================================================
//  Emetteur_AMOLED — Télécommande relais 12V (style iOS)
//  Carte : Waveshare ESP32-S3-Touch-AMOLED-1.8 (SH8601 + FT3168)
//
//  - Interface tactile LVGL (boutons ON / OFF)
//  - Section Réglages : luminosité, canal ESP-NOW, logique du relais, Wi-Fi
//  - Boutons physiques : BOOT = OK,  PWR = Retour
//  - Communication ESP-NOW en broadcast vers le récepteur (Recepteur_Relais)
//
//  Réglages carte (Arduino IDE) :
//    Carte         : "ESP32S3 Dev Module"
//    PSRAM         : "OPI PSRAM"
//    Flash Size    : "16MB (128Mb)"
//    Partition     : "16M Flash (3MB APP/9.9MB FATFS)"
//    USB CDC On Boot: "Enabled"
//
//  IMPORTANT : copier lv_conf.h (fourni) dans Documents/Arduino/libraries/
// =====================================================================
#include <Arduino.h>
#include <lvgl.h>
#include "config.h"
#include "app_settings.h"
#include "hw_display.h"
#include "hw_buttons.h"
#include "net_espnow.h"
#include "ui.h"

void setup() {
  Serial.begin(115200);

  settings_load();          // NVS
  display_init();           // Wire + AMOLED + LVGL + tactile
  buttons_init();           // BOOT + PWR
  ui_init();                // écrans LVGL

  lv_timer_handler();       // 1er rendu
  display_set_brightness(g_settings.brightness);

  espnow_init();            // Wi-Fi + ESP-NOW broadcast
}

void loop() {
  static uint32_t lastUi = 0;
  lv_timer_handler();       // moteur LVGL
  buttons_update();         // BOOT / PWR

  if (millis() - lastUi > 300) {  // rafraîchit les indicateurs ~3 Hz
    lastUi = millis();
    ui_tick();
  }
  delay(5);
}
