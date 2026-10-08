"""Security Test: Complete Authorization Matrix Across All Endpoints and Roles.

Asserts allowed (200/400/422) or forbidden (403) for every role.
"""
import pytest
from fastapi.testclient import TestClient

ALL_ROLES = ["operator", "supervisor", "admin", "analyst", "auditor", "emergency_dispatcher"]


@pytest.mark.parametrize("role", ALL_ROLES)
def test_dashboard_view_matrix(client: TestClient, auth_headers, role: str):
    headers = auth_headers(f"user_{role}", role)
    res = client.get("/api/junctions", headers=headers)
    # Allowed for all roles
    assert res.status_code == 200


@pytest.mark.parametrize("role", ALL_ROLES)
def test_admin_user_manage_matrix(client: TestClient, auth_headers, role: str):
    headers = auth_headers(f"user_{role}", role)
    res = client.get("/api/admin/users", headers=headers)
    if role == "admin":
        assert res.status_code == 200
    else:
        assert res.status_code == 403


@pytest.mark.parametrize("role", ALL_ROLES)
def test_signal_approve_matrix(client: TestClient, auth_headers, role: str):
    headers = auth_headers(f"user_{role}", role)
    res = client.post("/api/signal-requests/CR-002/decision", json={"decision": "approve"}, headers=headers)
    if role == "supervisor":
        # Allowed authorization (status 200 or 400 if state mismatch)
        assert res.status_code in (200, 400)
    else:
        assert res.status_code == 403


@pytest.mark.parametrize("role", ALL_ROLES)
def test_emergency_create_matrix(client: TestClient, auth_headers, role: str):
    headers = auth_headers(f"user_{role}", role)
    res = client.post(
        "/api/emergency",
        json={"vehicle": "EV-1", "from_junction": "J-01", "to_junction": "J-02", "duration": 120, "reason": "Test"},
        headers=headers
    )
    if role == "emergency_dispatcher":
        assert res.status_code in (200, 400)
    else:
        assert res.status_code == 403


@pytest.mark.parametrize("role", ALL_ROLES)
def test_audit_view_matrix(client: TestClient, auth_headers, role: str):
    headers = auth_headers(f"user_{role}", role)
    res = client.get("/api/audit", headers=headers)
    if role in ("admin", "auditor"):
        assert res.status_code == 200
    else:
        assert res.status_code == 403
