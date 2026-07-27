#include "hw_display.h"
#include "config.h"
#include <Wire.h>
#include <lvgl.h>
#include <Arduino_GFX_Library.h>
#include "esp_heap_caps.h"

// ---------- Pilote AMOLED (QSPI + SH8601) ----------
static Arduino_DataBus *bus = new Arduino_ESP32QSPI(
    LCD_CS, LCD_SCLK, LCD_SDIO0, LCD_SDIO1, LCD_SDIO2, LCD_SDIO3);

// RST = -1 (reset logiciel). Si l'image est décalée, ajuster les offsets
// en fin de constructeur (col_offset1, row_offset1, ...).
static Arduino_GFX *gfx = new Arduino_SH8601(
    bus, GFX_NOT_DEFINED /* RST */, 0 /* rotation */, LCD_WIDTH, LCD_HEIGHT);

// ---------- Tampons LVGL ----------
static lv_disp_draw_buf_t draw_buf;
static lv_color_t *buf1 = nullptr;
static lv_color_t *buf2 = nullptr;
static lv_disp_drv_t disp_drv;
static lv_indev_drv_t indev_drv;

// ---------------------------------------------------------------------
//  Flush LVGL -> AMOLED
// ---------------------------------------------------------------------
static void disp_flush_cb(lv_disp_drv_t *drv, const lv_area_t *area, lv_color_t *color_p) {
  uint32_t w = area->x2 - area->x1 + 1;
  uint32_t h = area->y2 - area->y1 + 1;
#if (LV_COLOR_16_SWAP != 0)
  gfx->draw16bitBeRGBBitmap(area->x1, area->y1, (uint16_t *)&color_p->full, w, h);
#else
  gfx->draw16bitRGBBitmap(area->x1, area->y1, (uint16_t *)&color_p->full, w, h);
#endif
  lv_disp_flush_ready(drv);
}

// ---------------------------------------------------------------------
//  Tactile FT3168 (compatible FocalTech FT6x36)
// ---------------------------------------------------------------------
bool ft3168_read(int16_t &x, int16_t &y) {
  // On lit 5 octets à partir du registre 0x02 :
  //   [0]=TD_STATUS, [1]=XH, [2]=XL, [3]=YH, [4]=YL
  Wire.beginTransmission(FT3168_ADDR);
  Wire.write(0x02);
  if (Wire.endTransmission(true) != 0) return false;
  if (Wire.requestFrom((int)FT3168_ADDR, 5) != 5) return false;

  uint8_t b[5];
  for (int i = 0; i < 5; i++) b[i] = Wire.read();

  uint8_t points = b[0] & 0x0F;
  if (points == 0 || points > 5) return false;

  x = ((b[1] & 0x0F) << 8) | b[2];
  y = ((b[3] & 0x0F) << 8) | b[4];

  if (x >= LCD_WIDTH)  x = LCD_WIDTH - 1;
  if (y >= LCD_HEIGHT) y = LCD_HEIGHT - 1;
  return true;
}

static void touch_read_cb(lv_indev_drv_t *drv, lv_indev_data_t *data) {
  static int16_t last_x = 0, last_y = 0;
  int16_t x, y;
  if (ft3168_read(x, y)) {
    last_x = x; last_y = y;
    data->state = LV_INDEV_STATE_PRESSED;
  } else {
    data->state = LV_INDEV_STATE_RELEASED;
  }
  data->point.x = last_x;
  data->point.y = last_y;
}

// ---------------------------------------------------------------------
//  Expandeur TCA9554 — lecture du port d'entrée (registre 0x00)
//  (les broches sont en entrée par défaut, on ne fait que lire)
// ---------------------------------------------------------------------
bool tca9554_read_input(uint8_t &value) {
  Wire.beginTransmission(TCA9554_ADDR);
  Wire.write(0x00);
  if (Wire.endTransmission(true) != 0) return false;
  if (Wire.requestFrom((int)TCA9554_ADDR, 1) != 1) return false;
  value = Wire.read();
  return true;
}

// ---------------------------------------------------------------------
//  Luminosité
// ---------------------------------------------------------------------
void display_set_brightness(uint8_t b) {
  gfx->setBrightness(b);
}

// ---------------------------------------------------------------------
//  Init global
// ---------------------------------------------------------------------
void display_init() {
  Wire.begin(I2C_SDA, I2C_SCL, I2C_FREQ_HZ);
  pinMode(TOUCH_INT, INPUT);

  gfx->begin();
  gfx->fillScreen(BLACK);
  display_set_brightness(0);   // on lèvera la luminosité après le 1er flush

  lv_init();

  // Tampons partiels (40 lignes), en RAM interne de préférence
  uint32_t bufLines = 40;
  uint32_t bufPx = LCD_WIDTH * bufLines;
  buf1 = (lv_color_t *)heap_caps_malloc(bufPx * sizeof(lv_color_t),
                                        MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  buf2 = (lv_color_t *)heap_caps_malloc(bufPx * sizeof(lv_color_t),
                                        MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  if (!buf1) buf1 = (lv_color_t *)heap_caps_malloc(bufPx * sizeof(lv_color_t), MALLOC_CAP_8BIT);
  if (!buf2) buf2 = (lv_color_t *)heap_caps_malloc(bufPx * sizeof(lv_color_t), MALLOC_CAP_8BIT);
  lv_disp_draw_buf_init(&draw_buf, buf1, buf2, bufPx);

  lv_disp_drv_init(&disp_drv);
  disp_drv.hor_res  = LCD_WIDTH;
  disp_drv.ver_res  = LCD_HEIGHT;
  disp_drv.flush_cb = disp_flush_cb;
  disp_drv.draw_buf = &draw_buf;
  lv_disp_drv_register(&disp_drv);

  lv_indev_drv_init(&indev_drv);
  indev_drv.type    = LV_INDEV_TYPE_POINTER;
  indev_drv.read_cb = touch_read_cb;
  lv_indev_drv_register(&indev_drv);
}
