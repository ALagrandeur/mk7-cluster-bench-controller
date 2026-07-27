// =====================================================================
//  hw_buttons.h  —  Boutons BOOT (OK) et PWR (Retour)
//    BOOT court  -> OK / valider l'élément en surbrillance
//    BOOT long   -> déplacer la surbrillance vers l'élément suivant
//    PWR  court  -> Retour
//    (PWR long >6 s = extinction matérielle, géré par la carte)
// =====================================================================
#pragma once
#include <Arduino.h>

void buttons_init();
void buttons_update();   // à appeler souvent depuis loop()
