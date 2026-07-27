// =====================================================================
//  ui.h  —  Interface graphique LVGL (style iOS)
// =====================================================================
#pragma once
#include <Arduino.h>

void ui_init();    // construit les écrans et le groupe de navigation
void ui_tick();    // rafraîchit les indicateurs d'état (appeler ~3 Hz)

// Événements boutons physiques (voir hw_buttons.cpp)
void ui_on_ok();   // BOOT court  -> valider l'élément focalisé
void ui_on_next(); // BOOT long   -> élément suivant
void ui_on_back(); // PWR court   -> retour
