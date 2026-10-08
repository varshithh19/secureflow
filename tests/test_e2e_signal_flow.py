"""End-to-End System Tests: Signal Change Lifecycle & Two-Person Approval."""
from fastapi.testclient import TestClient


def test_signal_change_two_person_e2e(client: TestClient, auth_headers):
    operator_headers = auth_headers("priya", "operator")
    supervisor_meera_headers = auth_headers("meera", "supervisor")
    supervisor_priya_headers = auth_headers("priya", "supervisor")  # Priya acting as supervisor
    admin_headers = auth_headers("sana", "admin")

    # Step 1: Operator Priya proposes a valid signal change for J-05
    propose_payload = {
        "jid": "J-05",
        "plan": {"ns": 60, "ew": 45, "yellow": 4, "allred": 2},
        "reason": "Optimize traffic flow during evening rush hour."
    }
    prop_res = client.post("/api/signal-requests", json=propose_payload, headers=operator_headers)
    assert prop_res.status_code == 200
    req_data = prop_res.json()
    req_id = req_data["id"]
    assert req_data["state"] == "PROPOSED"
    assert req_data["by"] == "priya"

    # Step 2: Negative Path - Proposer Priya attempts to approve her own request
    self_approve_res = client.post(
        f"/api/signal-requests/{req_id}/decision",
        json={"decision": "approve"},
        headers=supervisor_priya_headers
    )
    assert self_approve_res.status_code == 403
    assert "different supervisor" in self_approve_res.json()["detail"].lower()

    # Step 3: Positive Path - A different supervisor (Meera) approves the request
    approve_res = client.post(
        f"/api/signal-requests/{req_id}/decision",
        json={"decision": "approve"},
        headers=supervisor_meera_headers
    )
    assert approve_res.status_code == 200
    approved_data = approve_res.json()
    assert approved_data["state"] == "APPLIED"
    assert approved_data["approver"] == "meera"

    # Step 4: Verify Junction state updated with new plan
    j_res = client.get("/api/junctions/J-05", headers=operator_headers)
    assert j_res.status_code == 200
    j_data = j_res.json()
    assert j_data["plan"]["ns"] == 60
    assert j_data["plan"]["ew"] == 45

    # Step 5: Verify Audit Log chain remains intact
    audit_res = client.get("/api/audit/verify", headers=admin_headers)
    assert audit_res.status_code == 200
    assert audit_res.json()["ok"] is True
