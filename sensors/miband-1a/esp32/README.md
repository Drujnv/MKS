# ESP32: как Mi Band встроен в R4sGate

Прошивка MKS `R4sGate` (`main/sleepdot.c`) — BLE-централь на ESP32-C3.
Модуль Mi Band:

- сканирует эфир по имени `MI1A` / `MI BAND` или по MAC;
- по появлению открывает GATT-соединение;
- при `pair` пишет `FF0F=0x02`, вибрирует `2A06=0x02`, ждёт тап;
- после SMP пишет 20-байтный `UserInfo` в `FF04`;
- ждёт `0x05` на `FF03`;
- читает `FF0C` (батарея) и `FF06` (шаги);
- публикует MQTT `mks/miband/*`:
  - `state` — JSON battery/steps/activity/intensity/sleep_minutes/last_sync;
  - `battery`, `steps`, `status`;
- отдаёт HA-discovery (`homeassistant/...`).

## Важно

- MAC в прошивке — конкретного браслета; в публичном коде он заменён
  на `AA:BB:CC:DD:EE:FF`. При смене браслета MAC нужно обновить.
- `feature = 5`, `appearance = 0` — только для 1A.
- CRC — Dallas/Maxim; см. `docs/PROTOCOL.md`.
- Автоопрос делает **battery/steps**, а не постоянный live-поток.
- Если телефон держит браслет, ESP32 увидит таймаут — это нормальное
  ограничение BLE, а не ошибка прошивки.

## Сборка

```
pio run -e esp32c3
pio run -e esp32c3 -t upload --upload-port COM6
```

Перед заливкой: backup `main/sleepdot.c` + патч, проверить размер flash.
У нас сборка с PPG/SleepDot/MiBand занимала **98.9 %** — следующее крупное
изменение может не влезть.
