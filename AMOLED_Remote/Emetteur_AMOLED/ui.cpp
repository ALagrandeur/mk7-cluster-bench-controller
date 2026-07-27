#include "ui.h"
#include "config.h"
#include "app_settings.h"
#include "hw_display.h"
#include "net_espnow.h"
#include <lvgl.h>

// ---------------- Palette iOS (mode sombre) ----------------
#define COL_BG     lv_color_hex(0x000000)
#define COL_CARD   lv_color_hex(0x1C1C1E)
#define COL_CARD2  lv_color_hex(0x2C2C2E)
#define COL_GREEN  lv_color_hex(0x34C759)
#define COL_RED    lv_color_hex(0xFF3B30)
#define COL_BLUE   lv_color_hex(0x0A84FF)
#define COL_GRAY   lv_color_hex(0x8E8E93)
#define COL_WHITE  lv_color_hex(0xFFFFFF)

enum Screen { SCREEN_HOME, SCREEN_SETTINGS };
static Screen     s_screen = SCREEN_HOME;

static lv_obj_t  *scr_home;
static lv_obj_t  *scr_settings;
static lv_group_t*g;

// éléments mis à jour dynamiquement
static lv_obj_t  *home_pill;
static lv_obj_t  *home_pill_lbl;
static lv_obj_t  *home_relay_lbl;
static lv_obj_t  *lbl_channel;
static lv_obj_t  *btn_relay_low, *btn_relay_high;
static lv_obj_t  *btn_wifi;
static lv_obj_t  *kb;

// listes de focus pour la navigation au bouton
static lv_obj_t  *focus_home[4];     static int n_focus_home = 0;
static lv_obj_t  *focus_set[12];     static int n_focus_set  = 0;

static lv_style_t style_focus;

// ---------------------------------------------------------------------
//  Helpers de style
// ---------------------------------------------------------------------
static void make_card(lv_obj_t *o, lv_color_t bg) {
  lv_obj_set_style_bg_color(o, bg, 0);
  lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
  lv_obj_set_style_radius(o, 18, 0);
  lv_obj_set_style_border_width(o, 0, 0);
  lv_obj_set_style_pad_all(o, 14, 0);
}

// Bouton arrondi "pilule" iOS
static lv_obj_t* make_button(lv_obj_t *parent, const char *txt, lv_color_t bg,
                             lv_coord_t w, lv_coord_t h, const lv_font_t *font,
                             lv_event_cb_t cb) {
  lv_obj_t *b = lv_btn_create(parent);
  lv_obj_set_size(b, w, h);
  lv_obj_set_style_bg_color(b, bg, 0);
  lv_obj_set_style_radius(b, h / 2 > 26 ? 26 : h / 2, 0);
  lv_obj_set_style_shadow_width(b, 0, 0);
  lv_obj_set_style_border_width(b, 0, 0);
  lv_obj_add_style(b, &style_focus, LV_STATE_FOCUSED);
  lv_obj_t *l = lv_label_create(b);
  lv_label_set_text(l, txt);
  lv_obj_set_style_text_font(l, font, 0);
  lv_obj_set_style_text_color(l, COL_WHITE, 0);
  lv_obj_center(l);
  if (cb) lv_obj_add_event_cb(b, cb, LV_EVENT_CLICKED, NULL);
  return b;
}

// ---------------------------------------------------------------------
//  Navigation
// ---------------------------------------------------------------------
static void rebuild_group() {
  lv_group_remove_all_objs(g);
  if (s_screen == SCREEN_HOME) {
    for (int i = 0; i < n_focus_home; i++) lv_group_add_obj(g, focus_home[i]);
    if (n_focus_home) lv_group_focus_obj(focus_home[0]);
  } else {
    for (int i = 0; i < n_focus_set; i++) lv_group_add_obj(g, focus_set[i]);
    if (n_focus_set) lv_group_focus_obj(focus_set[0]);
  }
}

static void goto_screen(Screen s) {
  s_screen = s;
  lv_scr_load(s == SCREEN_HOME ? scr_home : scr_settings);
  rebuild_group();
}

// ---------------------------------------------------------------------
//  Callbacks ACCUEIL
// ---------------------------------------------------------------------
static void ev_on(lv_event_t *e)  { (void)e; espnow_send_command(CMD_ON); }
static void ev_off(lv_event_t *e) { (void)e; espnow_send_command(CMD_OFF); }
static void ev_gear(lv_event_t *e){ (void)e; goto_screen(SCREEN_SETTINGS); }

// ---------------------------------------------------------------------
//  Callbacks RÉGLAGES
// ---------------------------------------------------------------------
static void ev_back(lv_event_t *e) { (void)e; settings_save(); goto_screen(SCREEN_HOME); }

static void ev_bright(lv_event_t *e) {
  lv_obj_t *s = lv_event_get_target(e);
  uint8_t v = (uint8_t)lv_slider_get_value(s);
  g_settings.brightness = v;
  display_set_brightness(v);
  if (lv_event_get_code(e) == LV_EVENT_RELEASED) settings_save();
}

static void update_channel_lbl() {
  static char buf[8];
  snprintf(buf, sizeof(buf), "%u", g_settings.espnowChannel);
  lv_label_set_text(lbl_channel, buf);
}
static void ev_ch_minus(lv_event_t *e) {
  (void)e;
  if (g_settings.espnowChannel > 1)  g_settings.espnowChannel--;
  update_channel_lbl(); espnow_apply_channel(g_settings.espnowChannel); settings_save();
}
static void ev_ch_plus(lv_event_t *e) {
  (void)e;
  if (g_settings.espnowChannel < 13) g_settings.espnowChannel++;
  update_channel_lbl(); espnow_apply_channel(g_settings.espnowChannel); settings_save();
}

static void refresh_relay_buttons() {
  bool high = g_settings.relayActiveHigh;
  lv_obj_set_style_bg_color(btn_relay_low,  high ? COL_CARD2 : COL_BLUE, 0);
  lv_obj_set_style_bg_color(btn_relay_high, high ? COL_BLUE  : COL_CARD2, 0);
}
static void ev_relay_low(lv_event_t *e)  { (void)e; g_settings.relayActiveHigh = 0; refresh_relay_buttons(); settings_save(); }
static void ev_relay_high(lv_event_t *e) { (void)e; g_settings.relayActiveHigh = 1; refresh_relay_buttons(); settings_save(); }

static void refresh_wifi_button() {
  lv_obj_t *l = lv_obj_get_child(btn_wifi, 0);
  lv_label_set_text(l, g_settings.wifiEnabled ? "Wi-Fi : Active (redemarrer)"
                                              : "Wi-Fi : Desactive");
  lv_obj_set_style_bg_color(btn_wifi, g_settings.wifiEnabled ? COL_GREEN : COL_CARD2, 0);
}
static void ev_wifi_toggle(lv_event_t *e) {
  (void)e; g_settings.wifiEnabled = !g_settings.wifiEnabled;
  refresh_wifi_button(); settings_save();
}

// clavier : apparaît quand un champ texte est focalisé
static void ev_ta_focus(lv_event_t *e) {
  lv_obj_t *ta = lv_event_get_target(e);
  lv_keyboard_set_textarea(kb, ta);
  lv_obj_clear_flag(kb, LV_OBJ_FLAG_HIDDEN);
}
static void ev_ta_defocus(lv_event_t *e) {
  (void)e;
  lv_keyboard_set_textarea(kb, NULL);
  lv_obj_add_flag(kb, LV_OBJ_FLAG_HIDDEN);
}
static void ev_ta_changed(lv_event_t *e) {
  lv_obj_t *ta = lv_event_get_target(e);
  const char *txt = lv_textarea_get_text(ta);
  if (lv_obj_get_user_data(ta) == (void*)1)        // SSID
    strncpy(g_settings.wifiSsid, txt, sizeof(g_settings.wifiSsid) - 1);
  else                                             // mot de passe
    strncpy(g_settings.wifiPass, txt, sizeof(g_settings.wifiPass) - 1);
}

// ---------------------------------------------------------------------
//  Construction ACCUEIL
// ---------------------------------------------------------------------
static void build_home() {
  scr_home = lv_obj_create(NULL);
  lv_obj_set_style_bg_color(scr_home, COL_BG, 0);
  lv_obj_clear_flag(scr_home, LV_OBJ_FLAG_SCROLLABLE);

  // Titre
  lv_obj_t *title = lv_label_create(scr_home);
  lv_label_set_text(title, "Relais 12V");
  lv_obj_set_style_text_font(title, &lv_font_montserrat_28, 0);
  lv_obj_set_style_text_color(title, COL_WHITE, 0);
  lv_obj_align(title, LV_ALIGN_TOP_LEFT, 20, 24);

  // Roue crantée (réglages) en haut à droite
  lv_obj_t *gear = make_button(scr_home, LV_SYMBOL_SETTINGS, COL_CARD,
                               52, 52, &lv_font_montserrat_20, ev_gear);
  lv_obj_align(gear, LV_ALIGN_TOP_RIGHT, -16, 20);

  // Pilule d'état (liaison)
  home_pill = lv_obj_create(scr_home);
  lv_obj_set_size(home_pill, 200, 40);
  make_card(home_pill, COL_CARD);
  lv_obj_set_style_radius(home_pill, 20, 0);
  lv_obj_clear_flag(home_pill, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_align(home_pill, LV_ALIGN_TOP_MID, 0, 90);
  home_pill_lbl = lv_label_create(home_pill);
  lv_label_set_text(home_pill_lbl, "Recherche...");
  lv_obj_set_style_text_font(home_pill_lbl, &lv_font_montserrat_16, 0);
  lv_obj_set_style_text_color(home_pill_lbl, COL_GRAY, 0);
  lv_obj_center(home_pill_lbl);

  // État du relais
  home_relay_lbl = lv_label_create(scr_home);
  lv_label_set_text(home_relay_lbl, "Relais : --");
  lv_obj_set_style_text_font(home_relay_lbl, &lv_font_montserrat_20, 0);
  lv_obj_set_style_text_color(home_relay_lbl, COL_GRAY, 0);
  lv_obj_align(home_relay_lbl, LV_ALIGN_TOP_MID, 0, 145);

  // Gros boutons ON / OFF
  lv_obj_t *bON  = make_button(scr_home, "ON",  COL_GREEN, 280, 92, &lv_font_montserrat_28, ev_on);
  lv_obj_align(bON, LV_ALIGN_CENTER, 0, 30);
  lv_obj_t *bOFF = make_button(scr_home, "OFF", COL_RED,   280, 92, &lv_font_montserrat_28, ev_off);
  lv_obj_align(bOFF, LV_ALIGN_CENTER, 0, 140);

  n_focus_home = 0;
  focus_home[n_focus_home++] = bON;
  focus_home[n_focus_home++] = bOFF;
  focus_home[n_focus_home++] = gear;
}

// ---------------------------------------------------------------------
//  Construction RÉGLAGES
// ---------------------------------------------------------------------
static lv_obj_t* add_row(lv_obj_t *parent, const char *txt) {
  lv_obj_t *row = lv_obj_create(parent);
  lv_obj_set_width(row, lv_pct(100));
  lv_obj_set_height(row, LV_SIZE_CONTENT);
  make_card(row, COL_CARD);
  lv_obj_clear_flag(row, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_set_flex_flow(row, LV_FLEX_FLOW_ROW);
  lv_obj_set_flex_align(row, LV_FLEX_ALIGN_SPACE_BETWEEN, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
  if (txt) {
    lv_obj_t *l = lv_label_create(row);
    lv_label_set_text(l, txt);
    lv_obj_set_style_text_font(l, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(l, COL_WHITE, 0);
  }
  return row;
}

static void build_settings() {
  scr_settings = lv_obj_create(NULL);
  lv_obj_set_style_bg_color(scr_settings, COL_BG, 0);
  lv_obj_clear_flag(scr_settings, LV_OBJ_FLAG_SCROLLABLE);

  // Barre du haut : Retour + titre
  lv_obj_t *back = make_button(scr_settings, LV_SYMBOL_LEFT " Retour", COL_CARD,
                               130, 46, &lv_font_montserrat_16, ev_back);
  lv_obj_align(back, LV_ALIGN_TOP_LEFT, 14, 14);
  lv_obj_t *title = lv_label_create(scr_settings);
  lv_label_set_text(title, "Reglages");
  lv_obj_set_style_text_font(title, &lv_font_montserrat_20, 0);
  lv_obj_set_style_text_color(title, COL_WHITE, 0);
  lv_obj_align(title, LV_ALIGN_TOP_RIGHT, -20, 24);

  // Conteneur défilable
  lv_obj_t *list = lv_obj_create(scr_settings);
  lv_obj_set_size(list, LCD_WIDTH, LCD_HEIGHT - 74);
  lv_obj_align(list, LV_ALIGN_TOP_MID, 0, 72);
  lv_obj_set_style_bg_color(list, COL_BG, 0);
  lv_obj_set_style_border_width(list, 0, 0);
  lv_obj_set_style_pad_all(list, 14, 0);
  lv_obj_set_flex_flow(list, LV_FLEX_FLOW_COLUMN);
  lv_obj_set_style_pad_row(list, 12, 0);

  n_focus_set = 0;
  focus_set[n_focus_set++] = back;

  // --- Luminosité ---
  lv_obj_t *rowB = add_row(list, "Luminosite");
  lv_obj_t *sld = lv_slider_create(rowB);
  lv_obj_set_width(sld, 150);
  lv_slider_set_range(sld, 10, 255);
  lv_slider_set_value(sld, g_settings.brightness, LV_ANIM_OFF);
  lv_obj_set_style_bg_color(sld, COL_CARD2, LV_PART_MAIN);
  lv_obj_set_style_bg_color(sld, COL_BLUE, LV_PART_INDICATOR);
  lv_obj_set_style_bg_color(sld, COL_WHITE, LV_PART_KNOB);
  lv_obj_add_event_cb(sld, ev_bright, LV_EVENT_VALUE_CHANGED, NULL);
  lv_obj_add_event_cb(sld, ev_bright, LV_EVENT_RELEASED, NULL);

  // --- Canal ESP-NOW ---
  lv_obj_t *rowC = add_row(list, "Canal ESP-NOW");
  lv_obj_t *ctr = lv_obj_create(rowC);
  lv_obj_set_size(ctr, 150, 44);
  lv_obj_set_style_bg_opa(ctr, LV_OPA_0, 0);
  lv_obj_set_style_border_width(ctr, 0, 0);
  lv_obj_set_style_pad_all(ctr, 0, 0);
  lv_obj_clear_flag(ctr, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_set_flex_flow(ctr, LV_FLEX_FLOW_ROW);
  lv_obj_set_flex_align(ctr, LV_FLEX_ALIGN_SPACE_BETWEEN, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
  lv_obj_t *bMinus = make_button(ctr, "-", COL_CARD2, 44, 44, &lv_font_montserrat_20, ev_ch_minus);
  lbl_channel = lv_label_create(ctr);
  lv_obj_set_style_text_font(lbl_channel, &lv_font_montserrat_20, 0);
  lv_obj_set_style_text_color(lbl_channel, COL_WHITE, 0);
  update_channel_lbl();
  lv_obj_t *bPlus = make_button(ctr, "+", COL_CARD2, 44, 44, &lv_font_montserrat_20, ev_ch_plus);
  focus_set[n_focus_set++] = bMinus;
  focus_set[n_focus_set++] = bPlus;

  // --- Logique du relais ---
  lv_obj_t *rowR = add_row(list, "Logique relais");
  lv_obj_t *seg = lv_obj_create(rowR);
  lv_obj_set_size(seg, 170, 44);
  lv_obj_set_style_bg_opa(seg, LV_OPA_0, 0);
  lv_obj_set_style_border_width(seg, 0, 0);
  lv_obj_set_style_pad_all(seg, 0, 0);
  lv_obj_clear_flag(seg, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_set_flex_flow(seg, LV_FLEX_FLOW_ROW);
  lv_obj_set_flex_align(seg, LV_FLEX_ALIGN_SPACE_BETWEEN, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
  btn_relay_low  = make_button(seg, "BAS",  COL_CARD2, 80, 44, &lv_font_montserrat_16, ev_relay_low);
  btn_relay_high = make_button(seg, "HAUT", COL_CARD2, 80, 44, &lv_font_montserrat_16, ev_relay_high);
  refresh_relay_buttons();
  focus_set[n_focus_set++] = btn_relay_low;
  focus_set[n_focus_set++] = btn_relay_high;

  // --- Wi-Fi ---
  btn_wifi = make_button(list, "Wi-Fi", COL_CARD2, lv_pct(100), 50, &lv_font_montserrat_16, ev_wifi_toggle);
  refresh_wifi_button();
  focus_set[n_focus_set++] = btn_wifi;

  // SSID
  lv_obj_t *taS = lv_textarea_create(list);
  lv_textarea_set_one_line(taS, true);
  lv_textarea_set_placeholder_text(taS, "Nom du reseau (SSID)");
  lv_textarea_set_text(taS, g_settings.wifiSsid);
  lv_obj_set_width(taS, lv_pct(100));
  lv_obj_set_user_data(taS, (void*)1);
  lv_obj_add_event_cb(taS, ev_ta_focus,   LV_EVENT_FOCUSED, NULL);
  lv_obj_add_event_cb(taS, ev_ta_defocus, LV_EVENT_DEFOCUSED, NULL);
  lv_obj_add_event_cb(taS, ev_ta_changed, LV_EVENT_VALUE_CHANGED, NULL);
  focus_set[n_focus_set++] = taS;

  // Mot de passe
  lv_obj_t *taP = lv_textarea_create(list);
  lv_textarea_set_one_line(taP, true);
  lv_textarea_set_password_mode(taP, true);
  lv_textarea_set_placeholder_text(taP, "Mot de passe");
  lv_textarea_set_text(taP, g_settings.wifiPass);
  lv_obj_set_width(taP, lv_pct(100));
  lv_obj_set_user_data(taP, (void*)2);
  lv_obj_add_event_cb(taP, ev_ta_focus,   LV_EVENT_FOCUSED, NULL);
  lv_obj_add_event_cb(taP, ev_ta_defocus, LV_EVENT_DEFOCUSED, NULL);
  lv_obj_add_event_cb(taP, ev_ta_changed, LV_EVENT_VALUE_CHANGED, NULL);
  focus_set[n_focus_set++] = taP;

  // Clavier (caché par défaut, au-dessus de tout)
  kb = lv_keyboard_create(scr_settings);
  lv_obj_add_flag(kb, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_event_cb(kb, ev_ta_defocus, LV_EVENT_READY,  NULL);  // ✓ ferme
  lv_obj_add_event_cb(kb, ev_ta_defocus, LV_EVENT_CANCEL, NULL);  // ✕ ferme
}

// ---------------------------------------------------------------------
//  API publique
// ---------------------------------------------------------------------
void ui_init() {
  // style de surbrillance (focus) commun
  lv_style_init(&style_focus);
  lv_style_set_outline_width(&style_focus, 3);
  lv_style_set_outline_color(&style_focus, COL_WHITE);
  lv_style_set_outline_pad(&style_focus, 2);

  g = lv_group_create();
  lv_group_set_default(g);

  build_home();
  build_settings();
  goto_screen(SCREEN_HOME);
}

void ui_tick() {
  if (s_screen != SCREEN_HOME) return;
  bool online = espnow_link_online();
  if (online) {
    lv_label_set_text(home_pill_lbl, LV_SYMBOL_OK "  Recepteur connecte");
    lv_obj_set_style_text_color(home_pill_lbl, COL_GREEN, 0);
    bool st = espnow_relay_state();
    lv_label_set_text(home_relay_lbl, st ? "Relais : ON" : "Relais : OFF");
    lv_obj_set_style_text_color(home_relay_lbl, st ? COL_GREEN : COL_GRAY, 0);
  } else {
    lv_label_set_text(home_pill_lbl, LV_SYMBOL_WARNING "  Hors ligne");
    lv_obj_set_style_text_color(home_pill_lbl, COL_GRAY, 0);
    lv_label_set_text(home_relay_lbl, "Relais : --");
    lv_obj_set_style_text_color(home_relay_lbl, COL_GRAY, 0);
  }
}

// --- Boutons physiques ---
void ui_on_ok() {
  lv_obj_t *f = lv_group_get_focused(g);
  if (f) lv_event_send(f, LV_EVENT_CLICKED, NULL);
}
void ui_on_next() {
  lv_group_focus_next(g);
}
void ui_on_back() {
  if (s_screen == SCREEN_SETTINGS) { settings_save(); goto_screen(SCREEN_HOME); }
}
