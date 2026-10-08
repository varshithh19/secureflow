"""Integration tests for Incidents and Alerts API."""
from fastapi.testclient import TestClient


def test_incident_full_lifecycle(client: TestClient, auth_headers):
    operator_headers = auth_headers("priya", "operator")
    supervisor_headers = auth_headers("meera", "supervisor")

    # 1. Create incident
    create_res = client.post(
        "/api/incidents",
        json={
            "title": "Stalled truck at Tech Park",
            "jid": "J-03",
            "sev": "HIGH",
            "desc": "Truck broke down blocking lane."
        },
        headers=operator_headers
    )
    assert create_res.status_code == 200
    inc_data = create_res.json()
    inc_id = inc_data["id"]
    assert inc_data["status"] == "OPEN"

    # 2. Add progress note
    note_res = client.post(
        f"/api/incidents/{inc_id}/notes",
        json={"text": "Heavy tow truck dispatched."},
        headers=operator_headers
    )
    assert note_res.status_code == 200
    assert note_res.json()["text"] == "Heavy tow truck dispatched."

    # 3. Move to INVESTIGATING
    inv_res = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "INVESTIGATING"},
        headers=operator_headers
    )
    assert inv_res.status_code == 200
    assert inv_res.json()["status"] == "INVESTIGATING"

    # 4. Operator attempting to CLOSE should be forbidden (supervisor only)
    close_op_res = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "CLOSED"},
        headers=operator_headers
    )
    assert close_op_res.status_code == 403

    # 5. Supervisor closes incident
    close_sup_res = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "CLOSED"},
        headers=supervisor_headers
    )
    assert close_sup_res.status_code == 200
    assert close_sup_res.json()["status"] == "CLOSED"


def test_alert_acknowledgement(client: TestClient, auth_headers):
    op_headers = auth_headers("priya", "operator")
    ack_res = client.post("/api/alerts/A-001/ack", headers=op_headers)
    assert ack_res.status_code == 200
    assert ack_res.json()["ack"] == "priya"
