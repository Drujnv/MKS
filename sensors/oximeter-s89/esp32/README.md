# S-89 на ESP32 / ESP-IDF

Здесь только протокол, без привязки к конкретному шлюзу.

## Что делать

1. Найти сервис `S89_SVC_UUID` (ESP-IDF отдаёт UUID в обратной ориентации —
   массив уже в ней).
2. Найти notify `S89_NTF_UUID` и write `S89_WR_UUID`.
3. `s89_make_cmd(buf, S89_OP_START)` → записать 20 байт в write-handle.
4. Подписаться на notify и отдавать каждый кадр в `s89_parse`.
5. При потере пальца/отключении — stop (`S89_OP_STOP`), затем повторить.

## Пример (ESP-IDF)

```c
uint8_t cmd[S89_CMD_LEN];
s89_make_cmd(cmd, S89_OP_START);
esp_ble_gattc_write_char(gattc_if, conn_id, wr_handle,
                         sizeof(cmd), cmd,
                         ESP_GATT_WRITE_TYPE_RSP, ESP_GATT_AUTH_REQ_NONE);

/* в GATTC_NOTIFY_EVT */
s89_reading_t r;
if (s89_parse(param->notify.value, param->notify.value_len, &r)) {
    ESP_LOGI("S89", "SpO2=%d pulse=%d HRV=%d PI=%.1f",
             r.spo2, r.pulse, r.hrv, r.pi);
}
```

## Важно

- UUID из `s89_protocol.h` — в ориентации ESP-IDF (`...04 01 00 08 F1`).
  Если сравниваешь со строкой `F1080001-0451-...`, это одна и та же сущность.
- Не отправляй `80 01 02`: это IH018/F008, к S-89 не относится.
- S-89 рекламируется только с пальцем; при занятом соединении телефоном
  ESP32 его не увидит.
- PI = `[7] / 10`; не `/100`.
- Батарея: `s89_make_battery_cmd()` → `90 01 02`; ответ `s89_parse_battery`
  (`[2]=2`, `[3]=ack`, `[4]=status`, `[5]=деления 0..4`). В проценты:
  `raw * 25`; `0x04` = 100 %, не 4 %.
- PPG/ADC: `s89_parse_adc` для кадров F102 с `[2]=4`, 5 сэмплов по 3 байта
  с `[3]`. Формулу `convert_ecg_value` из SDK ещё нужно перенести.
