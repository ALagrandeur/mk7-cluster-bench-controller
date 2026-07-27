// =====================================================================
//  hw_display.h  —  Init AMOLED + LVGL + tactile, luminosité
// =====================================================================
#pragma once
#include <Arduino.h>

void display_init();                       // Wire + Arduino_GFX + LVGL + tactile
void display_set_brightness(uint8_t b);    // 0..255 (registre SH8601 0x51)

// Lecture brute du tactile FT3168 (utilisée par l'indev LVGL).
// Retourne true si un appui est détecté.
bool ft3168_read(int16_t &x, int16_t &y);

// Lecture du registre d'entrée de l'expandeur TCA9554 (port 0x00).
// Retourne true si la lecture I2C a réussi.
bool tca9554_read_input(uint8_t &value);
