/* S-89 protocol helpers (MIT). См. docs/PROTOCOL.md. */
#include "s89_protocol.h"

#include <string.h>

void s89_make_cmd(uint8_t out[S89_CMD_LEN], uint8_t op)
{
    if (!out) return;
    memset(out, 0, S89_CMD_LEN);
    out[0] = 0x90;
    out[1] = 0x02;
    out[2] = op; /* 0x01 start, 0x02 stop */
}

void s89_make_battery_cmd(uint8_t out[S89_CMD_LEN])
{
    if (!out) return;
    memset(out, 0, S89_CMD_LEN);
    out[0] = 0x90;
    out[1] = 0x01;
    out[2] = 0x02;
}

bool s89_parse_battery(const uint8_t *data, size_t len, s89_battery_t *out)
{
    if (!data || !out || len < 6) return false;
    if (data[0] != 0x90 || data[2] != 0x02 || data[3] != 1) return false;
    out->status = data[4];
    out->level = data[5];
    return true;
}

bool s89_parse_adc(const uint8_t *data, size_t len, int out[5])
{
    if (!data || !out || len < 18) return false;
    if (data[0] != 0x90 || data[2] != 0x04) return false;
    for (int i = 0; i < 5; i++) {
        const uint8_t *b = data + 3 + i * 3;
        out[i] = (b[0] << 16) | (b[1] << 8) | b[2];
    }
    return true;
}

bool s89_parse(const uint8_t *data, size_t len, s89_reading_t *out)
{
    if (!data || !out || len < 8) return false;
    if (data[0] != 0x90 || data[2] != 0x03 || data[3] != 1) return false;

    int spo2 = data[4];
    int pulse = data[5];
    if (spo2 < 50 || spo2 > 100) return false;
    if (pulse < 20 || pulse > 250) return false;

    out->spo2 = spo2;
    out->pulse = pulse;
    out->hrv = data[6];
    out->pi = data[7] / 10.0f;
    out->worn = true;
    return true;
}
