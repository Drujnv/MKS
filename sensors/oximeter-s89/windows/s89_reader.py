#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S-89 reference client: scan -> connect -> start -> parse SpO2/pulse/HRV/PI.

Только для собственного прибора. Не медицинское изделие.
Требует: pip install -r requirements.txt
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time

try:
    from bleak import BleakClient, BleakScanner
except ImportError:  # pragma: no cover
    print("нет bleak: pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(2)

SVC = "f1080001-0451-4000-b000-000000000000"
NTF = "f1080002-0451-4000-b000-000000000000"
WR = "f1080003-0451-4000-b000-000000000000"
ADC_NTF = "f1020002-0451-4000-b000-000000000000"
NAME_HINTS = ("s-89", "s89", "oximeter")


def make_cmd(kind: int) -> bytes:
    cmd = bytearray(20)
    cmd[0] = 0x90
    cmd[1] = 0x02
    cmd[2] = kind  # 1 start, 2 stop
    return bytes(cmd)


def make_battery_cmd() -> bytes:
    """Setting/get command: getCmd() + [1]=1,[2]=2 (battery)."""
    cmd = bytearray(20)
    cmd[0] = 0x90
    cmd[1] = 0x01
    cmd[2] = 0x02
    return bytes(cmd)


def parse_battery(data: bytes) -> dict | None:
    """Battery response: [2]==2, [3]==ack, [4]==status, [5]==level."""
    if len(data) < 6 or data[0] != 0x90 or data[2] != 2 or data[3] != 1:
        return None
    return {"status": data[4], "level": data[5]}


def parse_adc(data: bytes) -> dict | None:
    """F102 ADC frame: two channels ([2]=4/5), 5 x 3-byte big-endian samples at [3..17]."""
    if len(data) < 18 or data[0] != 0x90 or data[2] not in (4, 5):
        return None
    vals = []
    for i in range(5):
        b = data[3 + i * 3:6 + i * 3]
        vals.append((b[0] << 16) | (b[1] << 8) | b[2])
    return {"channel": data[2], "values": vals}


def parse_frame(data: bytes) -> dict | None:
    """Вернуть измерение или None. Формат см. docs/PROTOCOL.md."""
    if len(data) < 8 or data[0] != 0x90 or data[2] != 0x03:
        return None
    if data[3] != 1:  # палец не найден / не измеряет
        return None
    spo2, pulse, hrv, pi10 = data[4], data[5], data[6], data[7]
    if not 50 <= spo2 <= 100:
        return None
    return {
        "spo2": spo2,
        "pulse": pulse if 20 <= pulse <= 250 else None,
        "hrv": hrv,
        "pi": round(pi10 / 10.0, 1),
        "ts": time.time(),
    }


def _adv_matches(name: str | None, services: list[str] | None) -> bool:
    n = (name or "").lower()
    if any(h in n for h in NAME_HINTS):
        return True
    return any("90ea" in s.lower() for s in (services or []))


async def discover(seconds: float) -> list[dict]:
    found: list[dict] = []
    try:
        devices = await BleakScanner.discover(timeout=seconds, return_adv=True)
    except TypeError:  # старый bleak
        devices = await BleakScanner.discover(timeout=seconds)
        devices = {d.address: (d, None) for d in devices}
    for address, pair in devices.items():
        dev, adv = pair if isinstance(pair, tuple) else (pair, None)
        name = getattr(dev, "name", None) or getattr(adv, "local_name", None)
        services = list(getattr(adv, "service_uuids", []) or [])
        if _adv_matches(name, services):
            found.append({"address": address, "name": name or "?", "services": services,
                          "rssi": getattr(adv, "rssi", None)})
    return found


async def run(mac: str | None, seconds: float, scan: float, ppg: bool = False,
              battery: bool = False) -> int:
    if not mac:
        print(f"скан {scan:.0f} с...")
        found = await discover(scan)
        for f in found:
            print(f"  {f['address']}  {f['name']}  rssi={f['rssi']}")
        if not found:
            print("S-89 не найден. Проверь: палец на датчике, приложение/телефон не держат соединение.")
            return 1
        mac = found[0]["address"]
        print(f"выбран {mac}")

    def on_data(_char, data: bytearray) -> None:
        raw = bytes(data)
        b = parse_battery(raw)
        if b:
            print(f"BATTERY status={b['status']} level={b['level']}%")
            return
        r = parse_frame(raw)
        if r:
            print(f"SpO2={r['spo2']}%  pulse={r['pulse']}  HRV={r['hrv']}  PI={r['pi']}%")

    def on_adc(_char, data: bytearray) -> None:
        r = parse_adc(bytes(data))
        if r:
            print(f"PPG ch={r['channel']} values={r['values']}")

    async with BleakClient(mac, timeout=25) as client:
        print("connected")
        await client.start_notify(NTF, on_data)
        print("notify F1080002; start F1080003")
        if ppg:
            try:
                await client.start_notify(ADC_NTF, on_adc)
                print("notify F1020002 (PPG/ADC)")
            except Exception as exc:  # noqa: BLE001
                print(f"F102 notify недоступен: {type(exc).__name__}: {exc}")
        try:
            await client.write_gatt_char(WR, make_cmd(1), response=False)
        except Exception:
            await client.write_gatt_char(WR, make_cmd(1), response=True)
        if battery:
            await asyncio.sleep(2)
            try:
                await client.write_gatt_char(WR, make_battery_cmd(), response=False)
                print("battery cmd 90 01 02 -> F1080003")
            except Exception as exc:  # noqa: BLE001
                print(f"battery cmd ERR: {type(exc).__name__}: {exc}")
        t0 = time.time()
        while time.time() - t0 < seconds:
            await asyncio.sleep(0.2)
        try:
            await client.write_gatt_char(WR, make_cmd(2), response=False)
        except Exception:
            pass
        await client.stop_notify(NTF)
    return 0


def selftest() -> int:
    assert parse_frame(bytes.fromhex("90 02 03 01 63 45 d2 b7"))["spo2"] == 99
    assert parse_frame(bytes.fromhex("90 02 03 01 63 45 d2 b7"))["pulse"] == 69
    assert parse_frame(bytes.fromhex("90 02 03 01 63 45 d2 b7"))["pi"] == 18.3
    assert parse_frame(bytes.fromhex("90 02 01 01 00 00 00 00")) is None
    assert parse_frame(bytes.fromhex("90 02 03 00 63 45 d2 b7")) is None
    assert parse_battery(bytes.fromhex("90 01 02 01 01 64"))["level"] == 100
    assert parse_adc(bytes.fromhex("90 02 04 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f")) == {
        "channel": 4, "values": [0x010203, 0x040506, 0x070809, 0x0a0b0c, 0x0d0e0f]}
    assert parse_adc(bytes.fromhex("90 02 05 03 51 50 03 55 07 03 59 11 03 5d 3b 03 60 30"))["channel"] == 5
    print("selftest ok")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="S-89 BLE reader (SpO2/pulse/HRV/PI/battery/PPG)")
    ap.add_argument("--mac", help="MAC S-89; без него — поиск по имени")
    ap.add_argument("--seconds", type=float, default=30, help="длительность чтения")
    ap.add_argument("--scan", type=float, default=15, help="таймаут поиска")
    ap.add_argument("--battery", action="store_true", help="запросить батарею (90 01 02)")
    ap.add_argument("--ppg", action="store_true", help="подписаться на F1020002 и печатать ADC")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    try:
        return asyncio.run(run(args.mac, args.seconds, args.scan, args.ppg, args.battery))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
