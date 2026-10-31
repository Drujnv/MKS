#!/usr/bin/env python3
"""Prestigio PTH01BT: чтение без приложения и облака.

Два режима:
  --scan N   пассивно слушать рекламу N секунд (рекомендуется)
  --gatt     подключиться и прочитать характеристику 0xFB43 (монополизирует датчик)

Примеры:
  python prestigio_reader.py --scan 30
  python prestigio_reader.py --mac AA:BB:CC:DD:EE:FF --scan 30
  python prestigio_reader.py --mac AA:BB:CC:DD:EE:FF --gatt

Данные: температура °C, влажность %, давление hPa, батарея %.
Без MAC слушает все пакеты с company ID 0x01DE.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict, dataclass

COMPANY_ID = 0x01DE
SERVICE_UUID = "0000fa04-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "0000fb43-0000-1000-8000-00805f9b34fb"


@dataclass
class Reading:
    mac: str
    temperature_c: float
    humidity_percent: float
    pressure_hpa: float
    battery_percent: int
    source: str
    ts: float


def decode_adv(mac: str, raw: bytes) -> Reading | None:
    """Декодирует manufacturer data (15 байт)."""
    if len(raw) < 15:
        return None
    w_temp = (raw[1] << 8) | raw[2]
    w_hum = (raw[5] << 8) | raw[6]
    w_press = (raw[13] << 8) | raw[14]
    return Reading(
        mac=mac.upper(),
        temperature_c=round(0.03017 * w_temp - 47.39, 2),
        humidity_percent=round(0.0875 * w_hum - 59.2, 2),
        pressure_hpa=round(w_press / 16.0, 1),
        battery_percent=int(raw[10]),
        source="adv",
        ts=time.time(),
    )


def decode_gatt(mac: str, raw: bytes) -> Reading | None:
    if len(raw) < 8:
        return None
    w1 = (raw[0] << 8) | raw[1]
    w2 = (raw[2] << 8) | raw[3]
    w3 = (raw[4] << 8) | raw[5]
    return Reading(
        mac=mac.upper(),
        temperature_c=round(0.03253 * w1 - 52.79, 2),
        humidity_percent=round(0.09101 * w2 - 64.55, 2),
        pressure_hpa=round(w3 / 16.0, 1),
        battery_percent=int(raw[7]),
        source="gatt",
        ts=time.time(),
    )


def emit(reading: Reading) -> None:
    print(json.dumps(asdict(reading), ensure_ascii=False), flush=True)


async def scan(seconds: float, mac: str | None) -> int:
    from bleak import BleakScanner

    seen: set[str] = set()

    def callback(device, adv) -> None:
        manufacturer = adv.manufacturer_data or {}
        if COMPANY_ID not in manufacturer:
            return
        if mac and device.address.upper() != mac.upper():
            return
        reading = decode_adv(device.address, bytes(manufacturer[COMPANY_ID]))
        if reading is None:
            return
        emit(reading)
        seen.add(reading.mac)

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    try:
        await asyncio.sleep(seconds)
    finally:
        await scanner.stop()
    if not seen:
        print("Пакетов Prestigio не найдено; проверьте, что датчик рекламируется.",
              file=sys.stderr)
        return 2
    return 0


async def gatt(mac: str) -> int:
    from bleak import BleakClient

    async with BleakClient(mac, timeout=25.0) as client:
        raw = await client.read_gatt_char(CHAR_UUID)
        reading = decode_gatt(mac, bytes(raw))
        if reading is None:
            print("Короткий ответ GATT", file=sys.stderr)
            return 2
        emit(reading)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prestigio PTH01BT BLE reader")
    parser.add_argument("--mac", help="MAC датчика (необязательно для --scan)")
    parser.add_argument("--scan", type=float, default=0.0,
                        help="слушать рекламу N секунд (по умолчанию 30)")
    parser.add_argument("--gatt", action="store_true",
                        help="подключиться и прочитать GATT (монополизирует датчик)")
    args = parser.parse_args()
    if args.gatt:
        if not args.mac:
            parser.error("--gatt требует --mac")
        return asyncio.run(gatt(args.mac))
    return asyncio.run(scan(args.scan or 30.0, args.mac))


if __name__ == "__main__":
    raise SystemExit(main())
