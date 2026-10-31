/* Redmond RSC-51S: разбор кадра измерений (BLE, 20 байт). */
#ifndef RSC51S_PARSE_H
#define RSC51S_PARSE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint16_t co2_ppm;       /* ppm = raw + 400 */
    uint16_t co2_raw;       /* сырое значение (хранить для пересчёта) */
    uint8_t humidity_raw;   /* НЕ проценты: шкала не калибрована */
    uint8_t counter;        /* счётчик кадров, заворачивается на 255 */
} rsc51s_data_t;

/* Кадр: 55 | counter | 06 | 16 байт данных | AA */
int rsc51s_parse_frame(const uint8_t *frame, size_t len, rsc51s_data_t *out);

#ifdef __cplusplus
}
#endif

#endif
