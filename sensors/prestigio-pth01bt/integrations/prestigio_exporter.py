#!/usr/bin/env python3
"""Prometheus exporter для Prestigio PTH01BT (MQTT → /metrics).

Не занимает BLE. Подписывается на топики r4s0/<mac>/...,
которые публикует ESP32-шлюз (R4S-форк).

Запуск:
  pip install paho-mqtt
  python prestigio_exporter.py --mac aabbccddeeff
  # http://127.0.0.1:9191/metrics
"""
from __future__ import annotations

import argparse
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import paho.mqtt.client as mqtt

STATE: dict[str, float] = {}
TS = 0.0
LOCK = threading.Lock()


def make_on_message(topic_prefix: str):
    def on_message(_client, _userdata, msg) -> None:
        global TS
        key = msg.topic.rsplit("/", 1)[-1]
        try:
            value = float(msg.payload.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return
        with LOCK:
            STATE[key] = value
            TS = time.time()
    return on_message


def metrics() -> str:
    with LOCK:
        data = dict(STATE)
        ts = TS
    age = round(time.time() - ts, 1) if ts else None
    lines = ["# TYPE prestigio_up gauge",
             f"prestigio_up {1 if data else 0}"]
    for name, key in (
        ("prestigio_temperature_celsius", "temperature"),
        ("prestigio_humidity_percent", "humidity"),
        ("prestigio_pressure_hpa", "pressure"),
        ("prestigio_battery_percent", "battery"),
    ):
        if key in data:
            lines += [f"# TYPE {name} gauge", f"{name} {data[key]}"]
    if age is not None:
        lines += ["# TYPE prestigio_state_age_seconds gauge",
                  f"prestigio_state_age_seconds {age}"]
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path not in ("/metrics", "/"):
            self.send_response(404)
            self.end_headers()
            return
        body = metrics().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--mac", required=True,
                        help="MAC без двоеточий, нижним регистром")
    parser.add_argument("--http-port", type=int, default=9191)
    args = parser.parse_args()

    client = mqtt.Client(client_id="prestigio-exporter")
    client.on_message = make_on_message(f"r4s0/{args.mac}/")
    client.connect(args.host, args.port, 30)
    client.subscribe(f"r4s0/{args.mac}/+")
    client.loop_start()

    server = HTTPServer(("0.0.0.0", args.http_port), Handler)
    print(f"Prestigio exporter: http://0.0.0.0:{args.http_port}/metrics")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
