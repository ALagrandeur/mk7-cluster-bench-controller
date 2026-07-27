// =====================================================================
//  net_espnow.h  —  Liaison ESP-NOW (broadcast) + Wi-Fi optionnel
// =====================================================================
#pragma once
#include <Arduino.h>

void espnow_init();                       // configure Wi-Fi/canal + ESP-NOW
void espnow_send_command(uint8_t cmd);    // CMD_ON / CMD_OFF (broadcast)
void espnow_apply_channel(uint8_t ch);    // change le canal à chaud (si Wi-Fi off)

bool    espnow_link_online();             // true si un ACK reçu récemment
bool    espnow_relay_state();             // dernier état du relais reçu
uint8_t espnow_wifi_status();             // 0=off,1=connexion,2=connecté,3=échec
