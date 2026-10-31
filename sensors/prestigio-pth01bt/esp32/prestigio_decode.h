/* Prestigio PTH01BT decoder — portable C (ESP32, Arduino, ESP-IDF, host).
 *
 * Только чистая арифметика, без зависимостей от BLE-стека.
 * Формулы и смещения: docs/PROTOCOL.md.
 */
#ifndef PRESTIGIO_DECODE_H
#define PRESTIGIO_DECODE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int16_t temperature_centi;    /* °C * 100, например 2680 = 26.80 °C */
    int16_t humidity_centi;       /* % * 100,  например 5970 = 59.70 % */
    uint16_t pressure_tenths_hpa; /* hPa * 10,  например 9991 = 999.1 hPa */
    uint8_t battery_percent;      /* 0..100 */
} prestigio_data_t;

/* manufacturer data из рекламы: company ID 0x01DE */
int prestigio_decode_adv(const uint8_t *mfg, size_t len, prestigio_data_t *out);

/* 8 байт характеристики 0xFB43 */
int prestigio_decode_gatt(const uint8_t *raw, size_t len, prestigio_data_t *out);

#ifdef __cplusplus
}
#endif

#endif /* PRESTIGIO_DECODE_H */
