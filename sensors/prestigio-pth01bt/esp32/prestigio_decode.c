#include "prestigio_decode.h"

int prestigio_decode_adv(const uint8_t *mfg, size_t len, prestigio_data_t *out) {
    if (!mfg || !out || len < 15) return 0;

    uint16_t w_temp = ((uint16_t)mfg[1] << 8) | mfg[2];
    uint16_t w_hum  = ((uint16_t)mfg[5] << 8) | mfg[6];
    uint16_t w_press = ((uint16_t)mfg[13] << 8) | mfg[14];

    /* t = 0.03017*w - 47.39, в сотых °C: (3017*w)/1000 - 4739 */
    int32_t t = ((int32_t)3017 * w_temp) / 1000 - 4739;
    /* h = 0.0875*w - 59.2, в сотых %: (875*w)/100 - 5920 */
    int32_t h = ((int32_t)875 * w_hum) / 100 - 5920;
    /* p = w / 16 hPa; в десятых hPa: (w*10)/16 = w*5/8 */
    uint16_t p = (uint16_t)(((uint32_t)w_press * 5u) / 8u);

    out->temperature_centi = (int16_t)t;
    out->humidity_centi = (int16_t)h;
    out->pressure_tenths_hpa = p;
    out->battery_percent = mfg[10];
    return 1;
}

int prestigio_decode_gatt(const uint8_t *raw, size_t len, prestigio_data_t *out) {
    if (!raw || !out || len < 8) return 0;

    uint16_t w1 = ((uint16_t)raw[0] << 8) | raw[1];
    uint16_t w2 = ((uint16_t)raw[2] << 8) | raw[3];
    uint16_t w3 = ((uint16_t)raw[4] << 8) | raw[5];

    /* t = 0.03253*w1 - 52.79, в сотых °C */
    int32_t t = ((int32_t)3253 * w1) / 1000 - 5279;
    /* h = 0.09101*w2 - 64.55 */
    int32_t h = ((int32_t)9101 * w2) / 1000 - 6455;
    /* p = w3 / 16 hPa -> в десятых hPa: w3*5/8 */
    uint16_t p = (uint16_t)(((uint32_t)w3 * 5u) / 8u);

    out->temperature_centi = (int16_t)t;
    out->humidity_centi = (int16_t)h;
    out->pressure_tenths_hpa = p;
    out->battery_percent = raw[7];
    return 1;
}
