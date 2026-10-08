"""End-to-End System Tests: Emergency Vehicle Corridor Lifecycle & Rate Limits."""
from fastapi.testclient import TestClient


def test_emergency_corridor_lifecycle_and_rate_limits(client: TestClient, auth_headers):
    dispatcher_headers = auth_headers("ems", "emergency_dispatcher")
    supervisor_headers = auth_headers("meera", "supervisor")
    operator_headers = auth_headers("priya", "operator")

    # Step 1: Dispatcher requests green corridor from J-07 to J-09
    payload = {
        "vehicle": "EV-AMB-12",
        "from_junction": "J-07",
        "to_junction": "J-09",
        "duration": 180,
        "reason": "Emergency cardiac transit"
    }
    create_res = client.post("/api/emergency", json=payload, headers=dispatcher_headers)
    assert create_res.status_code == 200
    c_data = create_res.json()
    corridor_id = c_data["id"]
    assert c_data["state"] == "ACTIVE"
    assert c_data["route"] == ["J-07", "J-08", "J-09"]

    # Step 2: Verify conflict rejection on overlapping active route
    conflict_payload = {
        "vehicle": "EV-FIRE-03",
        "from_junction": "J-08",
        "to_junction": "J-09",
        "duration": 120,
        "reason": "Fire response"
    }
    conflict_res = client.post("/api/emergency", json=conflict_payload, headers=dispatcher_headers)
    assert conflict_res.status_code == 400
    assert "already has an active emergency corridor" in conflict_res.json()["detail"].lower()

    # Step 3: Supervisor cancels the active corridor
    cancel_res = client.delete(f"/api/emergency/{corridor_id}", headers=supervisor_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["state"] == "CANCELLED"

    # Step 4: Verify junctions are released
    j_res = client.get("/api/junctions/J-08", headers=operator_headers)
    assert j_res.status_code == 200
    assert j_res.json()["corridor"] is None
