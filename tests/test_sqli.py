"""Security Tests: SQL Injection & JWT Tampering Defenses (SR-09 / THR-07 / THR-08 / THR-12)."""
import jwt
from fastapi.testclient import TestClient


def test_sql_injection_defense_in_analytics_filter(client: TestClient, auth_headers):
    headers = auth_headers("priya", "operator")

    sqli_payloads = [
        "' OR 1=1 --",
        "J-01' UNION SELECT null, null, null --",
        "'; DROP TABLE users; --",
        "1; WAITFOR DELAY '0:0:5'--",
    ]

    for payload in sqli_payloads:
        res = client.get(f"/api/analytics?junction={payload}", headers=headers)
        # Server must safely reject with 422 or 400 and NEVER return 500 or execute injection
        assert res.status_code in (400, 422)
        assert "500" not in str(res.status_code)


def test_jwt_tampering_and_algorithm_confusion_rejected(client: TestClient):
    # Test 1: Forged token signed with wrong key
    forged_token = jwt.encode(
        {"sub": "sana", "role": "admin", "type": "access", "exp": 9999999999},
        "attacker-fake-secret-key-12345",
        algorithm="HS256"
    )
    res = client.get("/api/admin/users", headers={"Authorization": f"Bearer {forged_token}"})
    assert res.status_code == 401

    # Test 2: 'none' algorithm attack
    none_alg_token = jwt.encode(
        {"sub": "sana", "role": "admin", "type": "access"},
        "",
        algorithm="none"
    )
    res2 = client.get("/api/admin/users", headers={"Authorization": f"Bearer {none_alg_token}"})
    assert res2.status_code == 401

    # Test 3: Refresh token used as access token
    refresh_token = jwt.encode(
        {"sub": "sana", "type": "refresh", "exp": 9999999999},
        "secureflow-jwt-dev-secret-replace-in-production-min-32-chars",
        algorithm="HS256"
    )
    res3 = client.get("/api/admin/users", headers={"Authorization": f"Bearer {refresh_token}"})
    assert res3.status_code == 401
