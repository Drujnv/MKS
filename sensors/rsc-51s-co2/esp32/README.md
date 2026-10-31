# ESP32: чтение RSC-51S

## Что нужно

- BLE 4.2+ (ESP32/ESP32-C3);
- GATT-клиент: сервис `6e400001-b5a3-f393-e0a9-e50e24dcca9e`;
- запись — `6e400002-…` (TX),
- уведомления — `6e400003-…` (RX).

## Обязательный порядок

1. Подключиться.
2. **Подписаться на notify** (CCCD) — до команд, иначе первые кадры теряются.
3. **Сопряжение Just Works** (без PIN) — без него запись получает
   `Insufficient Authentication`.
4. Записать **два байта** `01 00` в TX — запуск потока.
5. Записать кадр `55 00 FF FF FF FF FF FF FF FF AA` — «авторизация».
6. На каждый notify длиной 20 байт — разобрать `rsc51s_parse_frame()`.

## Arduino (NimBLE) — эскиз

```cpp
#include <NimBLEDevice.h>
#include "rsc51s_parse.h"

static const char *SVC = "6e400001-b5a3-f393-e0a9-e50e24dcca9e";
static const char *TX  = "6e400002-b5a3-f393-e0a9-e50e24dcca9e";
static const char *RX  = "6e400003-b5a3-f393-e0a9-e50e24dcca9e";

void onNotify(NimBLERemoteCharacteristic *, uint8_t *data, size_t len, bool) {
    rsc51s_data_t d;
    if (rsc51s_parse_frame(data, len, &d)) {
        Serial.printf("CO2 %u ppm (raw %u), hum_raw %u\n",
                      d.co2_ppm, d.co2_raw, d.humidity_raw);
    }
}

void readStation(NimBLEAddress addr) {
    NimBLEClient *client = NimBLEDevice::createClient();
    client->connect(addr);
    auto *svc = client->getService(SVC);
    auto *tx = svc->getCharacteristic(TX);
    auto *rx = svc->getCharacteristic(RX);

    rx->subscribe(true, onNotify);          // 1) подписка
    client->getSecurity()->setSecurityMode(ESP_LE_AUTH_BOND);
    client->secureConnection();             // 2) Just Works, без PIN
    tx->writeValue((uint8_t[]){0x01, 0x00}, 2, true);   // 3) старт
    uint8_t auth[] = {0x55,0x00,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xAA};
    tx->writeValue(auth, sizeof(auth), true);            // 4) авторизация
}
```

## ESP-IDF

Используйте `esp_ble_gattc_*`: `register_for_notify` → `esp_ble_set_encryption`
(Just Works) → `write_char(0x01,0x00)` → `write_char(auth frame)`. Разбор — тем же
`rsc51s_parse_frame()`.

## R4S-шлюз

Если не хотите писать свой GATT-клиент, используйте форк
[`alutov/ESP32-R4sGate-for-Redmond`](https://github.com/alutov/ESP32-R4sGate-for-Redmond):
RSC-51S там штатное устройство. Наши заметки — `../r4s-fork/RSC51S-R4S.md`.

## Ограничения

- первые 10 минут после включения — прогрев;
- 3–5 м, металлизированное остекление не пробивает;
- влажность — сырое значение;
- протокол без шифрования.
