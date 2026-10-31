#!/usr/bin/env python3
"""Офлайн-тесты декодера Prestigio (без BLE).

Запуск: python tools/test_decode.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "windows"))

from prestigio_reader import decode_adv, decode_gatt  # noqa: E402

ADV_HEX = "01099b0201054f0410006403023e71"
GATT_HEX = "0936053e3e900064"


def main() -> int:
    adv = decode_adv("AA:BB:CC:DD:EE:FF", bytes.fromhex(ADV_HEX))
    gatt = decode_gatt("AA:BB:CC:DD:EE:FF", bytes.fromhex(GATT_HEX))
    assert adv is not None and gatt is not None

    assert abs(adv.temperature_c - 26.8) < 0.2, adv
    assert abs(adv.humidity_percent - 59.7) < 0.5, adv
    assert abs(adv.pressure_hpa - 999.1) < 1.0, adv
    assert adv.battery_percent == 100, adv

    assert abs(gatt.temperature_c - 23.9) < 1.0, gatt
    assert abs(gatt.humidity_percent - 57.6) < 1.0, gatt
    assert abs(gatt.pressure_hpa - 1001.0) < 2.0, gatt
    assert gatt.battery_percent == 100, gatt

    print("ADV :", adv)
    print("GATT:", gatt)
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

