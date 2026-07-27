#include "net_espnow.h"
#include "config.h"
#include "app_settings.h"
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

static const uint8_t BROADCAST[6] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};

static volatile bool     s_relayState   = false;
static volatile uint32_t s_lastAckMs    = 0;
static uint16_t          s_seq          = 0;
static uint8_t           s_wifiStatus   = 0;   // 0 off,1 connexion,2 ok,3 échec

// ---------- Réception des ACK (core esp32 >= 3.x) ----------
static void on_recv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len != (int)sizeof(relay_ack_t)) return;
  const relay_ack_t *ack = (const relay_ack_t *)data;
  if (ack->magic != ESPNOW_MAGIC || ack->version != ESPNOW_VERSION) return;
  s_relayState = (ack->state != 0);
  s_lastAckMs  = millis();
}

static void add_broadcast_peer(uint8_t channel) {
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BROADCAST, 6);
  peer.channel = channel;     // 0 = canal courant ; on force le canal réglé
  peer.encrypt = false;
  esp_now_del_peer(BROADCAST); // au cas où on réinitialise
  esp_now_add_peer(&peer);
}

void espnow_init() {
  WiFi.mode(WIFI_STA);

  uint8_t channel = g_settings.espnowChannel;

  if (g_settings.wifiEnabled && strlen(g_settings.wifiSsid) > 0) {
    // Wi-Fi station : le canal sera imposé par la box. ESP-NOW suit ce canal.
    s_wifiStatus = 1;
    WiFi.begin(g_settings.wifiSsid, g_settings.wifiPass);
    uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < 8000) delay(100);
    if (WiFi.status() == WL_CONNECTED) {
      s_wifiStatus = 2;
      channel = WiFi.channel();        // ESP-NOW DOIT utiliser ce canal
    } else {
      s_wifiStatus = 3;
      WiFi.disconnect();
      esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);  // repli : canal réglé
    }
  } else {
    // Pas de Wi-Fi : on fixe nous-mêmes le canal ESP-NOW.
    WiFi.disconnect();
    esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
  }

  if (esp_now_init() != ESP_OK) return;
  esp_now_register_recv_cb(on_recv);
  add_broadcast_peer(channel);
}

void espnow_apply_channel(uint8_t ch) {
  // N'a d'effet que si on n'est PAS connecté en Wi-Fi station
  // (sinon le canal est imposé par la box).
  if (s_wifiStatus == 2) return;
  esp_wifi_set_channel(ch, WIFI_SECOND_CHAN_NONE);
  add_broadcast_peer(ch);
}

void espnow_send_command(uint8_t cmd) {
  relay_cmd_t msg;
  msg.magic            = ESPNOW_MAGIC;
  msg.version          = ESPNOW_VERSION;
  msg.command          = cmd;
  msg.relay_active_high = g_settings.relayActiveHigh;
  msg.seq              = ++s_seq;
  // 3 envois rapides : compense une perte de paquet sans accusé fiable.
  for (int i = 0; i < 3; i++) {
    esp_now_send(BROADCAST, (uint8_t *)&msg, sizeof(msg));
    delay(4);
  }
}

bool espnow_link_online() {
  return (millis() - s_lastAckMs) < 3000 && s_lastAckMs != 0;
}

bool espnow_relay_state() { return s_relayState; }

uint8_t espnow_wifi_status() { return s_wifiStatus; }
