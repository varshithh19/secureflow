"""Integration tests for User Role Management, Lockout, and Analytics CSV Export."""
from fastapi.testclient import TestClient


def test_user_role_change_and_lock(client: TestClient, auth_headers):
    admin_headers = auth_headers("sana", "admin")

    # 1. Admin modifies role for rahul
    role_res = client.patch(
        "/api/admin/users/rahul/role",
        json={"role": "supervisor"},
        headers=admin_headers
    )
    assert role_res.status_code == 200
    assert role_res.json()["role"] == "supervisor"

    # 2. Admin locks dev
    lock_res = client.patch(
        "/api/admin/users/dev/lock",
        json={"locked": True},
        headers=admin_headers
    )
    assert lock_res.status_code == 200
    assert lock_res.json()["locked"] is True

    # 3. Admin resets MFA for meera
    mfa_reset_res = client.post("/api/admin/users/meera/reset-mfa", headers=admin_headers)
    assert mfa_reset_res.status_code == 200


def test_analytics_and_csv_export(client: TestClient, auth_headers):
    analyst_headers = auth_headers("dev", "analyst")

    # 1. Fetch JSON analytics
    res = client.get("/api/analytics?junction=J-01&range=24h", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["hours"]) == 24
    assert len(data["perJ"]) >= 1

    # 2. Fetch CSV export
    csv_res = client.get("/api/analytics/export.csv?junction=all&range=24h", headers=analyst_headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["Content-Type"]
    assert "Junction" in csv_res.text
    assert "Average congestion" in csv_res.text
