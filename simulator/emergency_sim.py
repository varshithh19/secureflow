"""SecureFlow Emergency Vehicle Priority Simulator.

Simulates authenticated emergency dispatch requests (TB5).
"""
import argparse
import time
import httpx


def main():
    parser = argparse.ArgumentParser(description="SecureFlow Emergency Simulator")
    parser.add_argument("--url", default="http://localhost:8000", help="SecureFlow API Base URL")
    parser.add_argument("--vehicle", default="EV-AMB-12", help="Vehicle identifier")
    parser.add_argument("--from-junction", default="J-07", help="Origin junction")
    parser.add_argument("--to-junction", default="J-09", help="Destination junction")
    parser.add_argument("--duration", type=int, default=120, help="Duration in seconds")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.url, timeout=5.0)

    # 1. Sign in as emergency dispatcher (ems)
    login_res = client.post("/api/auth/login", json={"username": "ems", "password": "Demo@1234"})
    if login_res.status_code != 200:
        print(f"[!] Login failed: {login_res.text}")
        return

    data = login_res.json()
    token = data["access_token"]
    csrf_token = data.get("csrf_token", "")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": csrf_token
    }

    # 2. Request priority green wave corridor
    req_body = {
        "vehicle": args.vehicle,
        "from_junction": args.from_junction,
        "to_junction": args.to_junction,
        "duration": args.duration,
        "reason": "Simulated emergency transit"
    }

    res = client.post("/api/emergency", json=req_body, headers=headers)
    print(f"[*] Corridor Request Status: {res.status_code}")
    print(f"[*] Response: {res.text}")


if __name__ == "__main__":
    main()
