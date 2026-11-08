#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mi Band 1A reference client: скан, pair, UserInfo auth, battery/steps, история.

Основано на pymb1a (GPLv3). Это НЕ официальный SDK Xiaomi.
Запуск:
    python miband_1a_reader.py --scan 60
    python miband_1a_reader.py --mac AA:BB:CC:DD:EE:FF --pair
    python miband_1a_reader.py --mac AA:BB:CC:DD:EE:FF --auth
    python miband_1a_reader.py --mac AA:BB:CC:DD:EE:FF --fetch
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=3))
SERVICE = "0000fee0-0000-1000-8000-00805f9b34fb"
UUID = {
    "info": "0000ff01-0000-1000-8000-00805f9b34fb",
    "notify": "0000ff03-0000-1000-8000-00805f9b34fb",
    "userinfo": "0000ff04-0000-1000-8000-00805f9b34fb",
    "control": "0000ff05-0000-1000-8000-00805f9b34fb",
    "steps": "0000ff06-0000-1000-8000-00805f9b34fb",
    "activity": "0000ff07-0000-1000-8000-00805f9b34fb",
    "datetime": "0000ff0a-0000-1000-8000-00805f9b34fb",
    "battery": "0000ff0c-0000-1000-8000-00805f9b34fb",
    "sensor": "0000ff0e-0000-1000-8000-00805f9b34fb",
    "pair": "0000ff0f-0000-1000-8000-00805f9b34fb",
    "alert": "00002a06-0000-1000-8000-00805f9b34fb",
}

CRC8_TABLE = (
    0, 94, 188, 226, 97, 63, 221, 131, 194, 156, 126, 32, 163, 253, 31, 65,
    157, 195, 33, 127, 252, 162, 64, 30, 95, 1, 227, 189, 62, 96, 130, 220,
    35, 125, 159, 193, 66, 28, 254, 160, 225, 191, 93, 3, 128, 222, 60, 98,
    190, 224, 2, 92, 223, 129, 99, 61, 124, 34, 192, 158, 29, 67, 161, 255,
    70, 24, 250, 164, 39, 121, 155, 197, 132, 218, 56, 102, 229, 187, 89, 7,
    219, 133, 103, 57, 186, 228, 6, 88, 25, 71, 165, 251, 120, 38, 196, 154,
    101, 59, 217, 135, 4, 90, 184, 230, 167, 249, 27, 69, 198, 152, 122, 36,
    248, 166, 68, 26, 153, 199, 37, 123, 58, 100, 134, 216, 91, 5, 231, 185,
    140, 210, 48, 110, 237, 179, 81, 15, 78, 16, 242, 172, 47, 113, 147, 205,
    17, 79, 173, 243, 112, 46, 204, 146, 211, 141, 111, 49, 178, 236, 14, 80,
    175, 241, 19, 77, 206, 144, 114, 44, 109, 51, 209, 143, 12, 82, 176, 238,
    50, 108, 142, 208, 83, 13, 239, 177, 240, 174, 76, 18, 145, 207, 45, 115,
    202, 148, 118, 40, 171, 245, 23, 73, 8, 86, 180, 234, 105, 55, 213, 139,
    87, 9, 235, 181, 54, 104, 138, 212, 149, 203, 41, 119, 244, 170, 72, 22,
    233, 183, 85, 11, 136, 214, 52, 106, 43, 117, 151, 201, 74, 20, 246, 168,
    116, 42, 200, 150, 21, 75, 169, 247, 182, 232, 10, 84, 215, 137, 107, 53,
)


def log(message: str) -> None:
    print(f"{datetime.now():%H:%M:%S} {message}", flush=True)


def crc8(data: bytes) -> int:
    value = 0
    for byte in data:
        value = CRC8_TABLE[byte ^ value]
    return value


def java_hash(text: str) -> int:
    value = 0
    for char in text:
        value = ((value << 5) - value) + ord(char)
        value &= 0xFFFFFFFF
    return value


def build_user_info(mac: str, alias: str = "testy", gender: int = 2, age: int = 30,
                    height: int = 175, weight: int = 75, hand: int = 0,
                    feature: int = 5, appearance: int = 0) -> bytes:
    uid = int(alias) if alias.isdigit() else java_hash(alias)
    data = bytearray(20)
    data[0:4] = uid.to_bytes(4, "little")
    data[4:11] = bytes([gender, age, height, weight, hand, feature, appearance])
    data[11:19] = alias.encode("ascii", "replace")[:8].ljust(8, b"\x00")
    data[19] = crc8(bytes(data[:19])) ^ int(mac.replace(":", "")[-2:], 16)
    return bytes(data)


def decode_activity(payload: bytes) -> list[dict]:
    samples: list[dict] = []
    cursor = 0
    while cursor + 11 <= len(payload):
        header = payload[cursor:cursor + 11]
        month, day = header[2] + 1, header[3]
        hour, minute = header[4], header[5]
        if not (header[0] == 1 and 1 <= month <= 12 and 1 <= day <= 31
                and hour < 24 and minute < 60):
            cursor += 1
            continue
        try:
            start = datetime(2000 + header[1], month, day, hour, minute, header[6], tzinfo=TZ)
        except ValueError:
            cursor += 1
            continue
        blocks = (header[9] | (header[10] << 8)) * 3
        cursor += 11
        index = 0
        while index * 3 < blocks and cursor + 3 <= len(payload):
            a, i, s = payload[cursor:cursor + 3]
            samples.append({"ts": start.timestamp() + index * 60,
                            "activity": a, "intensity": i, "steps": s})
            cursor += 3
            index += 1
    return samples


async def find_device(mac: str | None, seconds: float):
    from bleak import BleakScanner

    found = {}

    def callback(device, adv):
        name = f"{device.name or ''} {adv.local_name or ''}".upper()
        if (mac and device.address.upper() == mac.upper()) or "MI1A" in name or "MI BAND" in name:
            found[device.address.upper()] = device

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    await asyncio.sleep(seconds)
    await scanner.stop()
    if not found:
        raise RuntimeError("браслет не найден в эфире")
    return next(iter(found.values()))


async def connect(mac: str | None, seconds: float):
    from bleak import BleakClient

    device = await find_device(mac, seconds)
    log(f"найден {device.address}")
    for attempt in range(1, 6):
        client = BleakClient(device, timeout=15.0)
        try:
            await client.connect()
            return client, device.address
        except Exception as exc:  # noqa: BLE001
            log(f"connect {attempt}/5: {type(exc).__name__}: {exc}")
            try:
                await client.disconnect()
            except Exception:
                pass
            await asyncio.sleep(3)
    raise RuntimeError("не удалось подключиться к браслету")


async def auth(client, mac: str) -> bool:
    inbox = []
    await client.start_notify(UUID["notify"], lambda _c, d: inbox.append(bytes(d)))
    info = build_user_info(mac)
    log(f"UserInfo: {info.hex(' ')}")
    await client.write_gatt_char(UUID["userinfo"], info, response=True)
    for _ in range(60):
        await asyncio.sleep(0.1)
        while inbox:
            data = inbox.pop(0)
            if data[:1] == b"\x05":
                log("auth: УСПЕХ 0x05")
                return True
            if data[:1] == b"\x06":
                log("auth: ОТКАЗ 0x06")
                return False
    log("auth: ответа нет")
    return False


async def pair(client) -> None:
    try:
        await client.write_gatt_char(UUID["pair"], b"\x02", response=True)
        log("pair: отправлено; НАЖМИ НА БРАСЛЕТ В ТЕЧЕНИЕ 5 СЕКУНД")
    except Exception as exc:  # noqa: BLE001
        log(f"pair: ошибка {type(exc).__name__}: {exc}")
    try:
        await client.write_gatt_char(UUID["alert"], b"\x02", response=True)
    except Exception:
        pass
    await asyncio.sleep(7)


async def fetch(client, timeout: float = 40.0) -> list[dict]:
    inbox = []
    for key in ("steps", "activity"):
        try:
            await client.start_notify(UUID[key], lambda _c, d: inbox.append(bytes(d)))
        except Exception as exc:  # noqa: BLE001
            log(f"notify {key}: {type(exc).__name__}")
    await client.write_gatt_char(UUID["control"], b"\x06", response=True)
    payload = bytearray()
    started = time.time()
    while time.time() - started < timeout:
        await asyncio.sleep(0.2)
        while inbox:
            payload.extend(inbox.pop(0))
    return decode_activity(bytes(payload))


def selftest() -> int:
    info = build_user_info("AA:BB:CC:DD:EE:FF")
    assert len(info) == 20
    assert info[9] == 5 and info[10] == 0
    assert info[:4] == java_hash("testy").to_bytes(4, "little")
    assert info[19] == (crc8(info[:19]) ^ 0xFF)
    assert crc8(b"\x00") == 0
    assert crc8(b"\x01") == 0x5E
    payload = bytes.fromhex(
        "01 11 00 01 00 00 00 00 00 02 00"
        " 01 02 03 04 05 06"
    )
    samples = decode_activity(payload)
    assert len(samples) == 2 and samples[0]["steps"] == 3
    print("selftest ok")
    return 0


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mac", help="MAC; без него поиск по имени MI1A / MI BAND")
    ap.add_argument("--scan", type=float, default=0, help="только сканировать N секунд")
    ap.add_argument("--pair", action="store_true")
    ap.add_argument("--auth", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--seconds", type=float, default=60, help="окно поиска")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.scan:
        device = await find_device(args.mac, args.scan)
        print(f"{device.address} | {device.name}")
        return 0
    client, mac = await connect(args.mac, args.seconds)
    try:
        if args.pair:
            await pair(client)
        ok = await auth(client, mac)
        if not ok:
            return 2
        try:
            battery = bytes(await client.read_gatt_char(UUID["battery"]))
            if len(battery) >= 10:
                log(f"battery: {battery[0]}% status={battery[9]}")
        except Exception as exc:  # noqa: BLE001
            log(f"battery: {type(exc).__name__}: {exc}")
        try:
            steps = int.from_bytes(bytes(await client.read_gatt_char(UUID["steps"])), "little")
            log(f"steps: {steps}")
        except Exception as exc:  # noqa: BLE001
            log(f"steps: {type(exc).__name__}: {exc}")
        if args.fetch:
            samples = await fetch(client)
            log(f"activity: {len(samples)} samples")
            for sample in samples[:5]:
                moment = datetime.fromtimestamp(sample["ts"], TZ)
                log(f"  {moment:%d.%m %H:%M} steps={sample['steps']} intensity={sample['intensity']}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
