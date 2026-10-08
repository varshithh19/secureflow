"""SecureFlow IoT Traffic Sensor Simulator.

Simulates edge sensors generating signed telemetry with rush-hour patterns.
Supports live attack demonstration flags: --spoof, --replay, --implausible, --flood.
"""
import argparse
import hashlib
import hmac
import math
import secrets
import sys
import time
from typing import Dict, List, Tuple
import httpx

# Pre-shared simulator HMAC key
SIM_SECRET_KEY = b"simulator-sensor-secret-key-32bytes"

SENSORS: List[Tuple[str, str, float]] = [
    ("SN-101", "J-01", 0.45),
    ("SN-102", "J-02", 0.38),
    ("SN-103", "J-03", 0.70),
    ("SN-104", "J-04", 0.55),
    ("SN-105", "J-05", 0.84),
    ("SN-106", "J-05", 0.80),
    ("SN-107", "J-06", 0.50),
    ("SN-108", "J-07", 0.25),
    ("SN-110", "J-08", 0.40),
    ("SN-111", "J-09", 0.60),
]


def compute_signature(sensor_id: str, junction_id: str, count: int, speed: float, occ: float, ts: int, nonce: str) -> str:
    message = f"{sensor_id}|{junction_id}|{count}|{speed:.2f}|{occ:.4f}|{ts}|{nonce}".encode("utf-8")
    return hmac.new(SIM_SECRET_KEY, message, hashlib.sha256).hexdigest()


def generate_reading(sensor_id: str, junction_id: str, base_occ: float) -> Dict:
    hour = time.localtime().tm_hour + time.localtime().tm_min / 60.0
    # Rush hour peaks at 8:30 AM and 6:00 PM
    rush = 0.35 * math.exp(-((hour - 8.5) ** 2) / 4.0) + 0.45 * math.exp(-((hour - 18.0) ** 2) / 6.0)
    occ = max(0.05, min(0.95, base_occ * (0.6 + rush) + (secrets.randbelow(10) - 5) / 100.0))
    speed = max(10.0, min(110.0, 55.0 * (1.0 - occ) + secrets.randbelow(10)))
    count = int(occ * 45 + secrets.randbelow(6))
    ts = int(time.time() * 1000)
    nonce = secrets.token_hex(16)
    sig = compute_signature(sensor_id, junction_id, count, speed, occ, ts, nonce)

    return {
        "sensor_id": sensor_id,
        "junction_id": junction_id,
        "vehicle_count": count,
        "avg_speed": round(speed, 2),
        "occupancy": round(occ, 4),
        "timestamp": ts,
        "nonce": nonce,
        "signature": sig
    }


def main():
    parser = argparse.ArgumentParser(description="SecureFlow Sensor Simulator")
    parser.add_argument("--url", default="http://localhost:8000/api/telemetry", help="Target telemetry API URL")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval between ticks in seconds")
    parser.add_argument("--spoof", action="store_true", help="Attack demo: send telemetry from an unregistered device (THR-01)")
    parser.add_argument("--implausible", action="store_true", help="Attack demo: send physically impossible reading (THR-02)")
    parser.add_argument("--replay", action="store_true", help="Attack demo: replay a captured telemetry message (THR-03)")
    parser.add_argument("--flood", action="store_true", help="Attack demo: flood endpoint with rapid requests (THR-06)")
    args = parser.parse_args()

    client = httpx.Client(timeout=5.0)
    print(f"[*] SecureFlow Sensor Simulator started -> {args.url}")

    if args.spoof:
        print("[!] Running THR-01 attack demo: Spoofed unregistered sensor ID (SN-999)")
        payload = generate_reading("SN-999", "J-01", 0.5)
        res = client.post(args.url, json=payload)
        print(f"Server response ({res.status_code}): {res.text}")
        return

    if args.implausible:
        print("[!] Running THR-02 attack demo: Implausible reading (480 km/h speed at jammed junction)")
        payload = generate_reading("SN-105", "J-05", 0.9)
        payload["avg_speed"] = 480.0
        payload["vehicle_count"] = 0
        payload["signature"] = compute_signature(
            payload["sensor_id"], payload["junction_id"], payload["vehicle_count"],
            payload["avg_speed"], payload["occupancy"], payload["timestamp"], payload["nonce"]
        )
        res = client.post(args.url, json=payload)
        print(f"Server response ({res.status_code}): {res.text}")
        return

    if args.replay:
        print("[!] Running THR-03 attack demo: Replay of captured reading with identical nonce")
        payload = generate_reading("SN-101", "J-01", 0.45)
        res1 = client.post(args.url, json=payload)
        print(f"Initial transmission ({res1.status_code}): {res1.text}")
        print("[*] Replaying exact same payload...")
        res2 = client.post(args.url, json=payload)
        print(f"Replay response ({res2.status_code}): {res2.text}")
        return

    if args.flood:
        print("[!] Running THR-06 attack demo: Rapid flood of 150 requests to trigger rate limiting")
        blocked = 0
        for i in range(150):
            payload = generate_reading("SN-101", "J-01", 0.45)
            res = client.post(args.url, json=payload)
            if res.status_code == 429:
                blocked += 1
        print(f"[*] Sent 150 requests. Blocked by rate limiter (429): {blocked}")
        return

    # Normal continuous telemetry loop
    try:
        while True:
            for s_id, j_id, base in SENSORS:
                payload = generate_reading(s_id, j_id, base)
                try:
                    res = client.post(args.url, json=payload)
                    if res.status_code != 200:
                        print(f"[{s_id}] Status {res.status_code}: {res.text}")
                except Exception as e:
                    print(f"[{s_id}] Failed to send: {e}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[*] Sensor simulator stopped.")


if __name__ == "__main__":
    main()
