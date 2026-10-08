"""Integration tests for Security Center Threat Simulations & Real Metrics (THR-01 to THR-12)."""
from fastapi.testclient import TestClient


def test_threat_simulations_and_metrics(client: TestClient, auth_headers):
    sup_headers = auth_headers("meera", "supervisor")

    threat_ids = ["THR-01", "THR-02", "THR-03", "THR-04", "THR-05", "THR-06", "THR-10", "THR-12"]

    for thr in threat_ids:
        sim_res = client.post(f"/api/security/simulate/{thr}", headers=sup_headers)
        assert sim_res.status_code == 200
        sim_data = sim_res.json()
        assert sim_data["id"] == thr
        assert len(sim_data["result"]) > 0

    # Verify Prometheus metrics endpoint
    metrics_res = client.get("/api/security/metrics", headers=sup_headers)
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["invalid_signatures"] >= 1
    assert metrics["replay_attempts"] >= 1
    assert metrics["rate_limit_hits"] >= 1
