// =====================================================================
//  config.h  —  Émetteur AMOLED (Waveshare ESP32-S3-Touch-AMOLED-1.8)
//  Brochage matériel + protocole ESP-NOW partagé avec le récepteur.
//  Toutes les valeurs sont confirmées sur le BSP officiel Waveshare.
// =====================================================================
#pragma once
#include <Arduino.h>

// ---------- Écran AMOLED SH8601 (QSPI) ----------
#define LCD_WIDTH    368
#define LCD_HEIGHT   448
#define LCD_CS       12
#define LCD_SCLK     11
#define LCD_SDIO0    4
#define LCD_SDIO1    5
#define LCD_SDIO2    6
#define LCD_SDIO3    7
// Le RESET du LCD n'est PAS câblé sur un GPIO (reset logiciel) -> on passe -1.

// ---------- Bus I2C (tactile FT3168 + expandeur TCA9554) ----------
#define I2C_SDA      15
#define I2C_SCL      14
#define I2C_FREQ_HZ  400000
#define TOUCH_INT    21
#define FT3168_ADDR  0x38      // contrôleur tactile capacitif FocalTech
#define TCA9554_ADDR 0x20      // expandeur d'I/O (adresse 000)

// ---------- Boutons physiques ----------
#define BOOT_PIN     0         // bouton BOOT : GPIO0, actif BAS
#define PWR_EXIO_BIT 4         // bouton PWR : EXIO4 de l'expandeur, actif HAUT

// ---------- Protocole ESP-NOW (identique côté récepteur) ----------
#define ESPNOW_MAGIC    0xA5
#define ESPNOW_VERSION  1
#define CMD_OFF         0
#define CMD_ON          1

// Trame ENVOYÉE par l'émetteur -> récepteur
typedef struct __attribute__((packed)) {
  uint8_t  magic;            // ESPNOW_MAGIC
  uint8_t  version;          // ESPNOW_VERSION
  uint8_t  command;          // CMD_ON / CMD_OFF
  uint8_t  relay_active_high;// 1 = relais actif HAUT, 0 = actif BAS
  uint16_t seq;              // compteur de séquence
} relay_cmd_t;

// Trame d'ACQUITTEMENT renvoyée par le récepteur -> émetteur (en broadcast)
typedef struct __attribute__((packed)) {
  uint8_t  magic;            // ESPNOW_MAGIC
  uint8_t  version;          // ESPNOW_VERSION
  uint8_t  state;            // état RÉEL du relais (0 = OFF, 1 = ON)
  uint8_t  active_high;      // logique appliquée
  uint16_t seq;              // écho de la séquence reçue
} relay_ack_t;
