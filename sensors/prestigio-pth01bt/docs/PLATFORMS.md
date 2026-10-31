# Платформы и способы интеграции

| Платформа | Что использовать | Что получаем | Ограничения |
|---|---|---|---|
| **Windows** | `windows/prestigio_reader.py` + bleak | t/h/p/battery из рекламы; GATT опционально | нужен BLE-адаптер; GATT монополизирует датчик |
| **Linux** | тот же скрипт, bleak | то же | BlueZ должен быть поднят |
| **macOS** | тот же скрипт, bleak | то же | разрешение Bluetooth для терминала |
| **ESP32 (Arduino/NimBLE)** | `esp32/prestigio_decode.c` | декодер в своей прошивке | нужен свой BLE-сканер |
| **ESP32 (ESP-IDF)** | `esp32/prestigio_decode.c` | то же | смещения `ble_adv` зависят от сборки |
| **ESP32-C3 R4S (форк alutov)** | `r4s-fork/PRESTIGIO-R4S.md` | MQTT `r4s0/<mac>/*`, UI, HA | адаптер общий с Redmond; пропуски пакетов |
| **Home Assistant** | `homeassistant/prestigio_mqtt.yaml` | сенсоры t/h/p/battery | нужен MQTT-брокер и публикатор |
| **Prometheus/Grafana** | `integrations/prestigio_exporter.py` | метрики `/metrics` на 9191 | нужен MQTT-публикатор |

## Рекомендуемая схема для дома

```
Prestigio PTH01BT
   │ BLE advertising (manufacturer 0x01DE)
   ▼
ESP32-C3 R4S-шлюз (форк alutov)
   │ MQTT: r4s0/<mac>/temperature|humidity|pressure|battery
   ├──► Home Assistant (MQTT sensors)
   ├──► Prometheus exporter (9191)
   └──► PostgreSQL / Grafana (через свой мост)
```

GATT используется только для разового замера: он занимает датчик и мешает
постоянному мониторингу.

## Что нужно заменить при развёртывании

* MAC-плейсхолдер `AA:BB:CC:DD:EE:FF` / `aabbccddeeff` — на свой;
* MQTT-хост/логин — в своих конфигах, **не коммитить**;
* при необходимости — префикс топиков `r4s0` на свой.
