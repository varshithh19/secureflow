"""Integration tests for Auth API: Login, Lockout, MFA, Token Refresh, and Profile."""
from fastapi.testclient import TestClient


def test_login_flow_standard_operator(client: TestClient):
    res = client.post("/api/auth/login", json={"username": "priya", "password": "Demo@1234"})
    assert res.status_code == 200
    data = res.json()
    assert data["access_token"] is not None
    assert data["mfa_required"] is False
    assert data["user"]["id"] == "priya"
    assert data["user"]["role"] == "operator"


def test_login_flow_supervisor_mfa(client: TestClient):
    # Step 1: Login triggers MFA requirement
    res = client.post("/api/auth/login", json={"username": "meera", "password": "Demo@1234"})
    assert res.status_code == 200
    data = res.json()
    assert data["mfa_required"] is True

    # Step 2: Complete MFA with 123456
    mfa_res = client.post("/api/auth/mfa", json={"username": "meera", "code": "123456"})
    assert mfa_res.status_code == 200
    mfa_data = mfa_res.json()
    assert mfa_data["access_token"] is not None
    assert mfa_data["user"]["id"] == "meera"


def test_account_lockout_after_5_failed_attempts(client: TestClient):
    # Attempt 5 incorrect logins
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "rahul", "password": "WrongPassword@123"})

    # 6th attempt should be blocked due to account lockout
    locked_res = client.post("/api/auth/login", json={"username": "rahul", "password": "Demo@1234"})
    assert locked_res.status_code == 401
    assert "account is locked" in locked_res.json()["detail"].lower()


def test_me_endpoint(client: TestClient, auth_headers):
    headers = auth_headers("priya", "operator")
    res = client.get("/api/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["id"] == "priya"
