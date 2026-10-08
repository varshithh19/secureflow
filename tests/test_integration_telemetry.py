"""Integration tests: Sensor Registration -> Signed Ingest -> Congestion Alert -> Dashboard."""
import time
from fastapi.testclient import TestClient

from secureflow.core.security import compute_hmac_sha256

SHARED_KEY = b"simulator-sensor-secret-key-32bytes"


def test_full_telemetry_to_dashboard_pipeline(client: TestClient, auth_headers):
    # 1. Register a new sensor as Admin
    admin_headers = auth_headers("sana", "admin")
    reg_res = client.post(
        "/api/admin/sensors",
        json={"type": "radar", "jid": "J-01", "loc": "Approach N"},
        headers=admin_headers
    )
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    sensor_id = reg_data["sensor"]["id"]
    assert reg_data["secret"] is not None

    # 2. Activate the sensor
    act_res = client.post(f"/api/admin/sensors/{sensor_id}/activate", headers=admin_headers)
    assert act_res.status_code == 200
    assert act_res.json()["status"] == "ACTIVE"

    # 3. Ingest signed telemetry causing Severe congestion
    now_ms = int(time.time() * 1000)
    nonce = f"nonce-integ-{now_ms}"
    vehicle_count = 55
    avg_speed = 12.0
    occupancy = 0.88  # Severe congestion (> 0.80)

    msg = f"{sensor_id}|J-01|{vehicle_count}|{avg_speed:.2f}|{occupancy:.4f}|{now_ms}|{nonce}".encode("utf-8")
    sig = compute_hmac_sha256(SHARED_KEY, msg)

    ingest_res = client.post(
        "/api/telemetry",
        json={
            "sensor_id": sensor_id,
            "junction_id": "J-01",
            "vehicle_count": vehicle_count,
            "avg_speed": avg_speed,
            "occupancy": occupancy,
            "timestamp": now_ms,
            "nonce": nonce,
            "signature": sig
        }
    )
    assert ingest_res.status_code == 200
    assert ingest_res.json()["status"] == "accepted"

    # 4. Operator views Dashboard Junctions and Alerts
    op_headers = auth_headers("priya", "operator")
    junc_res = client.get("/api/junctions/J-01", headers=op_headers)
    assert junc_res.status_code == 200
    j_data = junc_res.json()
    assert j_data["level"] == 3  # Severe level

    alerts_res = client.get("/api/alerts", headers=op_headers)
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    severe_alerts = [a for a in alerts if a["jid"] == "J-01" and a["type"] == "SEVERE_CONGESTION"]
    assert len(severe_alerts) >= 1
