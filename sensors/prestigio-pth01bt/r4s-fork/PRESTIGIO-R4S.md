# Интеграция в форк `alutov/ESP32-R4sGate-for-Redmond`

Проверено на **ESP32-C3 SuperMini** (4 MB flash), ESP-IDF 5.3.1, PlatformIO.
Форк — база R4S-шлюза: Wi-Fi, MQTT, BLE-сканер, веб-UI, управление Redmond.

## 1. Что добавляется

1. распознавание рекламы Prestigio по service `0xFE00` + manufacturer `0x01DE`;
2. декодирование температуры/влажности/давления/батареи;
3. публикация в MQTT:
   ```
   r4s0/<mac>/temperature
   r4s0/<mac>/humidity
   r4s0/<mac>/pressure
   r4s0/<mac>/battery
   ```
   `<mac>` — MAC без двоеточий, нижним регистром;
4. опционально — строка в веб-UI и HA-discovery.

## 2. Куда вставить

В `main/r4sGate.c`, в обработчике `ESP_GAP_BLE_SCAN_RESULT_EVT`, после
получения `scan_result` (до обработки Redmond/имени устройства).

```c
/* Prestigio PTH01BT: service FE00 + manufacturer 01DE. */
static bool prestigio_publish(const esp_ble_gap_cb_param_t *scan_result)
{
    if (!mqttConnected) return false;
    if (scan_result->scan_rst.adv_data_len < 26) return false;

    const uint8_t *a = scan_result->scan_rst.ble_adv;
    /* 03 02 00 FE 12 FF DE 01 — service + company */
    if (!(a[3] == 0x03 && a[4] == 0x02 && a[5] == 0x00 && a[6] == 0xFE &&
          a[7] == 0x12 && a[8] == 0xFF && a[9] == 0xDE && a[10] == 0x01)) {
        return false;
    }

    uint16_t w_temp  = ((uint16_t)a[12] << 8) | a[13];
    uint16_t w_hum   = ((uint16_t)a[16] << 8) | a[17];
    uint16_t w_press = ((uint16_t)a[24] << 8) | a[25];

    int32_t t_centi = ((int32_t)3017 * w_temp) / 1000 - 4739;  /* 0.03017*w - 47.39 */
    int32_t h_centi = ((int32_t)875  * w_hum)  / 100  - 5920;  /* 0.0875*w - 59.2  */
    uint16_t p_tenth = (uint16_t)(((uint32_t)w_press * 5u) / 8u); /* w/16 hPa * 10 */
    uint8_t battery = a[21];

    char mac[13];
    for (int j = 0; j < 6; j++) sprintf(mac + j * 2, "%02x", scan_result->scan_rst.bda[5 - j]);

    char topic[64], value[24];
    snprintf(topic, sizeof(topic), "r4s0/%s/temperature", mac);
    snprintf(value, sizeof(value), "%d.%02d", t_centi / 100, abs(t_centi % 100));
    esp_mqtt_client_publish(mqttclient, topic, value, 0, 1, 1);

    snprintf(topic, sizeof(topic), "r4s0/%s/humidity", mac);
    snprintf(value, sizeof(value), "%d.%02d", h_centi / 100, abs(h_centi % 100));
    esp_mqtt_client_publish(mqttclient, topic, value, 0, 1, 1);

    snprintf(topic, sizeof(topic), "r4s0/%s/pressure", mac);
    snprintf(value, sizeof(value), "%u.%u", p_tenth / 10, p_tenth % 10);
    esp_mqtt_client_publish(mqttclient, topic, value, 0, 1, 1);

    snprintf(topic, sizeof(topic), "r4s0/%s/battery", mac);
    snprintf(value, sizeof(value), "%u", battery);
    esp_mqtt_client_publish(mqttclient, topic, value, 0, 1, 1);
    return true;
}
```

Вызвать в `ESP_GAP_BLE_SCAN_RESULT_EVT`:

```c
if (prestigio_publish(&param->scan_rst)) {
    /* опционально: обновить UI-переменные и не отдавать пакет дальше */
}
```

> В оригинальном коде MAC сравнивался жёстко (`AA:BB:...`). В публичной версии
> **не хардкодьте MAC**: распознавайте по service/company ID. Если нужен фильтр —
> вынесите MAC в `secrets.h`/NVS, не в публичный код.

## 3. MQTT/HA

Топики совместимы с `homeassistant/prestigio_mqtt.yaml`.
Для HA-discovery можно добавить retained-конфиг:

```cpp
const char *cfg = R"({
 "name":"Prestigio temperature",
 "state_topic":"r4s0/<mac>/temperature",
 "unit_of_measurement":"°C",
 "device_class":"temperature",
 "unique_id":"prestigio_<mac>_temp"
})";
```

## 4. Сборка

```bash
git clone https://github.com/alutov/ESP32-R4sGate-for-Redmond
# наложите изменения из этого документа
pio run -e esp32c3
pio run -e esp32c3 -t upload
```

Для C3 в исходном форке может потребоваться `board_build.partitions=C3/partitions.csv`,
`CONFIG_BT_BLE_42_FEATURES_SUPPORTED=y`, `CONFIG_BT_BLE_50_FEATURES_SUPPORTED=n`,
`-Os` (см. issue/сборку форка). Прошивка должна влезать в раздел OTA; при
нехватке — увеличить app-раздел, как в нашем форке.

## 5. Проверка

1. В логе R4S: `PRESTIGIO`/MQTT publish;
2. `mosquitto_sub -v -t 'r4s0/+/temperature'` — значения совпадают с датчиком;
3. HA: сенсоры обновляются;
4. GATT не используется — адаптер свободен для Redmond/сканера.

## 6. Ограничения

- R4S-сканер работает в общем эфире; при большом числе устройств возможны
  пропуски пакетов (низкий duty cycle рекламы);
- давление в рекламе приближённое;
- не подключайтесь GATT-ом к Prestigio на том же адаптере постоянно — это
  монополизирует датчик.
