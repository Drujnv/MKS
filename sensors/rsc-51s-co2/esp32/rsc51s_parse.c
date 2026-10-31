#include "rsc51s_parse.h"

#define RSC51S_FRAME_START 0x55
#define RSC51S_FRAME_END   0xAA
#define RSC51S_CMD_MEASURE 0x06
#define RSC51S_CO2_OFFSET  400

int rsc51s_parse_frame(const uint8_t *frame, size_t len, rsc51s_data_t *out) {
    if (!frame || !out || len != 20) return 0;
    if (frame[0] != RSC51S_FRAME_START || frame[19] != RSC51S_FRAME_END) return 0;
    if (frame[2] != RSC51S_CMD_MEASURE) return 0;

    const uint8_t *payload = frame + 3; /* 16 байт */
    uint16_t raw = (uint16_t)payload[10] | ((uint16_t)payload[11] << 8);

    out->co2_raw = raw;
    out->co2_ppm = raw + RSC51S_CO2_OFFSET;
    out->humidity_raw = payload[6];
    out->counter = payload[1];
    return 1;
}
