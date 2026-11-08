/*
 * S-89 oximeter protocol helpers (MIT).
 * No ESP-IDF dependency: pure C99, can be used in ESP-IDF/Arduino.
 * See docs/PROTOCOL.md.
 */
#ifndef S89_PROTOCOL_H
#define S89_PROTOCOL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define S89_CMD_LEN 20
#define S89_OP_START 0x01
#define S89_OP_STOP  0x02

/* UUID в ориентации, которую ESP-IDF отдаёт в SEARCH_RES (обратная строка). */
static const uint8_t S89_SVC_UUID[16] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xB0,
    0x00, 0x40, 0x51, 0x04, 0x01, 0x00, 0x08, 0xF1
};
static const uint8_t S89_NTF_UUID[16] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xB0,
    0x00, 0x40, 0x51, 0x04, 0x02, 0x00, 0x08, 0xF1
};
static const uint8_t S89_WR_UUID[16] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xB0,
    0x00, 0x40, 0x51, 0x04, 0x03, 0x00, 0x08, 0xF1
};

typedef struct {
    int spo2;      /* % */
    int pulse;     /* bpm */
    int hrv;       /* [6], по SDK DetectData.hrv */
    float pi;      /* [7] / 10.0 */
    bool worn;     /* [3] == 1 */
} s89_reading_t;

/* Собрать 20-байтовый кадр: start=0x01, stop=0x02. */
void s89_make_cmd(uint8_t out[S89_CMD_LEN], uint8_t op);

/* Разобрать notify. Возвращает true только для валидного измерения. */
bool s89_parse(const uint8_t *data, size_t len, s89_reading_t *out);

#endif /* S89_PROTOCOL_H */
