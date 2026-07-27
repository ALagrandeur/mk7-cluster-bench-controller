// =====================================================================
//  Recepteur_Relais — ESP32 (DevKit standard)
//  Reçoit les commandes ON/OFF en ESP-NOW (broadcast) et pilote un relais 12V.
//  La logique du relais (actif HAUT / actif BAS) est imposée par l'émetteur
//  dans chaque trame (réglée depuis l'interface AMOLED).
//
//  Réglages carte (Arduino IDE) : "ESP32 Dev Module"
//  Cœur esp32 : version >= 3.0.0 (signature ESP-NOW moderne).
//
//  >>> Le CANAL doit être IDENTIQUE à celui réglé sur l'émetteur (def. 1).
// =====================================================================
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

// ---------------- Configuration ----------------
#define RELAY_PIN        4      // GPIO pilotant le relais
#define STATUS_LED       2      // LED embarquée (état du lien)
#define ESPNOW_CHANNEL   1      // DOIT correspondre à l'émetteur
#define DEFAULT_ACTIVE_HIGH 0   // état du relais avant la 1ère trame (0 = actif BAS)

// ---------------- Protocole (identique à l'émetteur) ----------------
#define ESPNOW_MAGIC    0xA5
#define ESPNOW_VERSION  1
#define CMD_OFF         0
#define CMD_ON          1

typedef struct __attribute__((packed)) {
  uint8_t  magic;
  uint8_t  version;
  uint8_t  command;
  uint8_t  relay_active_high;
  uint16_t seq;
} relay_cmd_t;

typedef struct __attribute__((packed)) {
  uint8_t  magic;
  uint8_t  version;
  uint8_t  state;
  uint8_t  active_high;
  uint16_t seq;
} relay_ack_t;

static const uint8_t BROADCAST[6] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};

static bool     g_relayOn     = false;
static uint8_t  g_activeHigh  = DEFAULT_ACTIVE_HIGH;
static uint32_t g_lastRxMs    = 0;

// ---------------- Application physique du relais ----------------
static void apply_relay() {
  // ON  -> niveau actif ;  OFF -> niveau inactif
  bool level = g_relayOn ? (g_activeHigh ? HIGH : LOW)
                         : (g_activeHigh ? LOW  : HIGH);
  digitalWrite(RELAY_PIN, level);
}

// ---------------- Envoi d'un accusé (broadcast) ----------------
static void send_ack(uint16_t seq) {
  relay_ack_t ack;
  ack.magic       = ESPNOW_MAGIC;
  ack.version     = ESPNOW_VERSION;
  ack.state       = g_relayOn ? 1 : 0;
  ack.active_high = g_activeHigh;
  ack.seq         = seq;
  esp_now_send(BROADCAST, (uint8_t *)&ack, sizeof(ack));
}

// ---------------- Réception (cœur esp32 >= 3.x) ----------------
static void on_recv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  (void)info;
  if (len != (int)sizeof(relay_cmd_t)) return;
  const relay_cmd_t *m = (const relay_cmd_t *)data;
  if (m->magic != ESPNOW_MAGIC || m->version != ESPNOW_VERSION) return;

  g_activeHigh = m->relay_active_high ? 1 : 0;
  g_relayOn    = (m->command == CMD_ON);
  apply_relay();
  g_lastRxMs   = millis();

  send_ack(m->seq);

  Serial.printf("RX cmd=%s actif=%s\n",
                g_relayOn ? "ON" : "OFF",
                g_activeHigh ? "HAUT" : "BAS");
}

static void add_broadcast_peer() {
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BROADCAST, 6);
  peer.channel = ESPNOW_CHANNEL;
  peer.encrypt = false;
  esp_now_add_peer(&peer);
}

void setup() {
  Serial.begin(115200);

  pinMode(RELAY_PIN, OUTPUT);
  pinMode(STATUS_LED, OUTPUT);
  g_relayOn = false;
  apply_relay();                 // relais OFF au démarrage

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Erreur init ESP-NOW");
    while (true) { digitalWrite(STATUS_LED, !digitalRead(STATUS_LED)); delay(120); }
  }
  esp_now_register_recv_cb(on_recv);
  add_broadcast_peer();

  Serial.print("Recepteur pret. MAC : ");
  Serial.println(WiFi.macAddress());
}

void loop() {
  // LED : allumée si une trame a été reçue dans les 3 dernières secondes
  bool linked = (millis() - g_lastRxMs) < 3000 && g_lastRxMs != 0;
  digitalWrite(STATUS_LED, linked ? HIGH : LOW);
  delay(50);
}
