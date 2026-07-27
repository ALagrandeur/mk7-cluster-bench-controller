#include "hw_buttons.h"
#include "config.h"
#include "hw_display.h"   // tca9554_read_input()
#include "ui.h"           // ui_on_ok / ui_on_next / ui_on_back

#define LONG_PRESS_MS   600
#define DEBOUNCE_MS     30
#define POLL_MS         15

struct Btn {
  bool     pressed;       // état debouncé
  bool     longFired;     // l'appui long a déjà été émis
  uint32_t changeMs;      // dernier changement brut
  uint32_t pressMs;       // début de l'appui debouncé
  bool     rawLast;       // dernier état brut
};

static Btn boot = {false,false,0,0,false};
static Btn pwr  = {false,false,0,0,false};
static uint32_t lastPollMs = 0;

static bool read_boot_raw() { return digitalRead(BOOT_PIN) == LOW; }   // actif BAS

static bool read_pwr_raw() {
  uint8_t v;
  if (!tca9554_read_input(v)) return false;
  return (v >> PWR_EXIO_BIT) & 0x01;                                   // actif HAUT
}

void buttons_init() {
  pinMode(BOOT_PIN, INPUT_PULLUP);
}

// Met à jour un bouton et déclenche les callbacks (court / long).
static void process(Btn &b, bool raw, void (*onShort)(), void (*onLong)()) {
  uint32_t now = millis();

  if (raw != b.rawLast) { b.rawLast = raw; b.changeMs = now; }

  // changement stable -> on adopte le nouvel état
  if ((now - b.changeMs) >= DEBOUNCE_MS && raw != b.pressed) {
    b.pressed = raw;
    if (b.pressed) {            // front descendant -> appui
      b.pressMs   = now;
      b.longFired = false;
    } else {                    // relâché
      if (!b.longFired && onShort) onShort();   // appui court validé au relâché
    }
  }

  // appui long pendant le maintien
  if (b.pressed && !b.longFired && (now - b.pressMs) >= LONG_PRESS_MS) {
    b.longFired = true;
    if (onLong) onLong();
  }
}

void buttons_update() {
  uint32_t now = millis();
  if (now - lastPollMs < POLL_MS) return;
  lastPollMs = now;

  process(boot, read_boot_raw(), ui_on_ok,   ui_on_next);
  process(pwr,  read_pwr_raw(),  ui_on_back,  nullptr);
}
