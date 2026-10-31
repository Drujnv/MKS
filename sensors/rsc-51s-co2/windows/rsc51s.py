#!/usr/bin/env python3
"""
rsc51s.py — чтение показаний станции CO2 Redmond RSC-51S напрямую по Bluetooth LE.

Зачем: станция отдаёт данные только своему приложению. Скрипт подключается к ней
напрямую с обычного компьютера (Windows/Linux/macOS), без аккаунта, без облака и
без интернета, и сохраняет замеры в CSV.

Проверено на: Redmond RSC-51S (model CST001, прошивка 136, ПО 3.21).

Что нужно знать перед запуском (подробности — PROTOCOL.md):
  1) нужен Bluetooth-адаптер и расстояние 3–5 метров до станции (через глухое
     остекление связи нет);
  2) первые 10 минут после включения станции данные не используем: прибор
     калибруется (проверено трижды);
  3) ppm = значение поля + 400 (проверено на свежем воздухе: 406–421 ppm).

Зависимости:  pip install bleak
Запуск:       python rsc51s.py --address <MAC> --minutes 60 --out co2.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import datetime
import sys

from bleak import BleakClient, BleakScanner

# Характеристики станции (служба 6e400001-…, как в Nordic UART — но протокол свой).
UUID_TX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"   # сюда пишем команды
UUID_RX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"   # отсюда приходят кадры

# Кадр: 0x55 | счётчик | команда | данные | 0xAA
FRAME_START = 0x55
FRAME_END = 0xAA
CMD_READ_MODE = 0x06      # режим измерений (то, что мы читаем)
CMD_AUTH = 0xFF           # «авторизация»: 55 00 FF <8 байт 0xFF> AA

CO2_OFFSET = 400          # смещение шкалы: ppm = сырое значение + 400
WARMUP_SECONDS = 600      # первые 10 минут после включения станции — калибровка

CSV_FIELDS = ["время", "co2_ppm", "co2_сырое", "влажность_сырое", "счётчик", "годен"]


def parse_frame(data: bytes) -> dict | None:
    """Разобрать кадр измерений. Возвращает словарь или None, если кадр не наш."""
    if len(data) != 20 or data[0] != FRAME_START or data[-1] != FRAME_END:
        return None
    if data[2] != CMD_READ_MODE:
        return None
    payload = data[3:-1]                      # 16 байт полезной нагрузки
    raw_co2 = payload[10] | (payload[11] << 8)
    return {
        "co2_сырое": raw_co2,
        "co2_ppm": raw_co2 + CO2_OFFSET,
        "влажность_сырое": payload[6],        # НЕ проценты: шкала не калибрована
        "счётчик": payload[1],                 # счётчик кадров, заворачивается на 255
    }


async def find_device(address: str | None, timeout: float = 15.0):
    """Найти станцию: по адресу или как первое устройство с нужной службой."""
    if address:
        return address
    print("Ищу станцию (15 секунд)…")
    devices = await BleakScanner.discover(timeout=timeout)
    for dev in devices:
        name = (dev.name or "")
        if "RSC" in name.upper() or "REDMOND" in name.upper():
            print(f"  нашёл: {name} [{dev.address}]")
            return dev.address
    return None


async def run(address: str | None, minutes: float, out_path: str) -> int:
    address = await find_device(address)
    if not address:
        print("Станция не найдена. Подойдите ближе (3–5 м) и запустите снова.")
        return 2

    rows: list[dict] = []
    session_start = datetime.datetime.now()

    def on_frame(_sender, data: bytearray) -> None:
        parsed = parse_frame(bytes(data))
        if not parsed:
            return
        now = datetime.datetime.now().astimezone()
        age = (now - session_start).total_seconds()
        parsed["время"] = now.isoformat(timespec="seconds")
        parsed["годен"] = 0 if age < WARMUP_SECONDS else 1
        rows.append(parsed)
        if len(rows) == 1 or len(rows) % 60 == 0:
            flag = "прогрев" if parsed["годен"] == 0 else "ок"
            print(f"  {parsed['co2_ppm']:>5} ppm | влажность(сырое) {parsed['влажность_сырое']:>3} | {flag}")

    client = BleakClient(address, timeout=20.0)
    try:
        await client.connect()
        # ВАЖНО: сначала подписка, потом команды — иначе первые кадры теряются.
        await client.start_notify(UUID_RX, on_frame)
        # Станция требует ПАРУ (сопряжение) перед записью: без него ATT отвечает
        # «Insufficient Authentication». Для этого класса устройств используется
        # Just Works (без PIN): protection_level=2.
        try:
            await client.pair(protection_level=2)
        except Exception as exc:                        # уже сопряжены — это нормально
            print(f"  сопряжение не потребовалось ({type(exc).__name__})")
        # Запуск потока измерений: ровно два байта 01 00.
        await client.write_gatt_char(UUID_TX, bytes([0x01, 0x00]), response=True)
        # Кадр «авторизации», после которого станция начинает вещать раз в секунду.
        auth = bytes([FRAME_START, 0x00, CMD_AUTH]) + bytes([0xFF] * 8) + bytes([FRAME_END])
        await client.write_gatt_char(UUID_TX, auth, response=True)
        print(f"Поток открыт. Пишу {minutes:.0f} мин в {out_path} (первые 10 минут — прогрев).")
        await asyncio.sleep(minutes * 60)
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    with open(out_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    usable = [r for r in rows if r["годен"] == 1]
    print(f"Готово: кадров {len(rows)}, из них годных {len(usable)}")
    if usable:
        vals = [r["co2_ppm"] for r in usable]
        print(f"CO2: от {min(vals)} до {max(vals)} ppm, последнее {vals[-1]} ppm")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Чтение CO2 со станции Redmond RSC-51S по BLE")
    parser.add_argument("--address", help="MAC станции (если не указан — поиск по имени)")
    parser.add_argument("--minutes", type=float, default=10.0, help="сколько минут писать (по умолчанию 10)")
    parser.add_argument("--out", default="rsc51s.csv", help="файл CSV для записи")
    args = parser.parse_args()
    try:
        return asyncio.run(run(args.address, args.minutes, args.out))
    except KeyboardInterrupt:
        print("Остановлено вручную.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
