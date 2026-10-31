# ESP32 / ESP-IDF / Arduino

## Файлы

- `prestigio_decode.c` — декодер рекламы и GATT, чистый C;
- `prestigio_decode.h` — структура и API.

Зависимостей нет, подходит для ESP-IDF, Arduino-ESP32 и любого C-проекта.

## Arduino (NimBLE или встроенный BLE)

```cpp
#include <NimBLEDevice.h>
#include "prestigio_decode.h"

class ScanCallbacks : public NimBLEAdvertisedDeviceCallbacks {
    void onResult(NimBLEAdvertisedDevice *dev) override {
        if (!dev->haveManufacturerData()) return;
        std::string mfg = dev->getManufacturerData();
        if (mfg.size() < 2) return;
        uint16_t company = (uint8_t)mfg[0] | ((uint16_t)(uint8_t)mfg[1] << 8);
        if (company != 0x01DE) return;

        prestigio_data_t d;
        if (prestigio_decode_adv((const uint8_t *)mfg.data() + 2, mfg.size() - 2, &d)) {
            Serial.printf("%s: %.2f C, %.2f %%, %.1f hPa, %u %%\n",
                dev->getAddress().toString().c_str(),
                d.temperature_centi / 100.0,
                d.humidity_centi / 100.0,
                d.pressure_tenths_hpa / 10.0,
                d.battery_percent);
        }
    }
};

void setup() {
    Serial.begin(115200);
    NimBLEDevice::init("prestigio-scan");
    auto *scan = NimBLEDevice::getScan();
    scan->setAdvertisedDeviceCallbacks(new ScanCallbacks());
    scan->setActiveScan(false);
    scan->start(0, false);
}

void loop() { delay(1000); }
```

MATLAB manufacturer data в NimBLE: первые 2 байта — company ID little-endian
(`0xDE 0x01`), далее payload; поэтому в вызов передаётся `mfg + 2`.

## ESP-IDF (GAP scan)

В обработчике `ESP_GAP_BLE_SCAN_RESULT_EVT`:

```c
if (param->scan_rst.adv_data_len >= 26 &&
    param->scan_rst.ble_adv[3] == 0x03 && param->scan_rst.ble_adv[4] == 0x02 &&
    param->scan_rst.ble_adv[5] == 0x00 && param->scan_rst.ble_adv[6] == 0xFE &&
    param->scan_rst.ble_adv[7] == 0x12 && param->scan_rst.ble_adv[8] == 0xFF &&
    param->scan_rst.ble_adv[9] == 0xDE && param->scan_rst.ble_adv[10] == 0x01) {
    prestigio_data_t d;
    /* manufacturer payload начинается с ble_adv[11] */
    if (prestigio_decode_adv(&param->scan_rst.ble_adv[11],
                             param->scan_rst.adv_data_len - 11, &d)) {
        ESP_LOGI("PRESTIGIO", "%.2f C %.2f %% %.1f hPa %u %%",
                 d.temperature_centi / 100.0, d.humidity_centi / 100.0,
                 d.pressure_tenths_hpa / 10.0, d.battery_percent);
    }
}
```

> В некоторых сборках `ble_adv` уже содержит полный payload; ориентируйтесь на
> сигнатуру сервиса `FE00`/company `01DE` и смещения из `PROTOCOL.md`.

## GATT (опционально)

Если нужен разовый замер: подключиться к сервису `0xFA04`, прочитать
характеристику `0xFB43`, вызвать `prestigio_decode_gatt`. **После чтения
обязательно закрыть соединение** — иначе датчик перестанет рекламироваться.

## R4S-шлюз

Готовый пример встраивания в форк `alutov/ESP32-R4sGate-for-Redmond` —
`../r4s-fork/PRESTIGIO-R4S.md`.
