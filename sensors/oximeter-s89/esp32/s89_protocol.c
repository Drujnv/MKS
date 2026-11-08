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
