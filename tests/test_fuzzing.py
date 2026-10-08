"""Hypothesis Property-Based Fuzz Testing for Telemetry and Analytics Ingestion.

Ensures the backend never panics with unhandled 500 Internal Server Errors
or leaks stack traces when presented with arbitrary, hostile, or malformed inputs.
"""
import math
import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
@given(
    sensor_id=st.text(max_size=100),
    junction_id=st.text(max_size=50),
    vehicle_count=st.integers(min_value=-1000, max_value=10000),
    avg_speed=st.floats(min_value=-1000.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    occupancy=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    timestamp=st.integers(min_value=-10**12, max_value=10**15),
    nonce=st.text(max_size=128),
    signature=st.text(max_size=128)
)
def test_fuzz_telemetry_endpoint(
    client: TestClient,
    sensor_id: str,
    junction_id: str,
    vehicle_count: int,
    avg_speed: float,
    occupancy: float,
    timestamp: int,
    nonce: str,
    signature: str
):
    payload = {
        "sensor_id": sensor_id,
        "junction_id": junction_id,
        "vehicle_count": vehicle_count,
        "avg_speed": avg_speed,
        "occupancy": occupancy,
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": signature
    }

    res = client.post("/api/telemetry", json=payload)
    # The application must handle invalid inputs gracefully with 4xx and NEVER return 500
    assert res.status_code != 500
    # The response body must not leak traceback or internal state
    assert "Traceback" not in res.text


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
@given(
    junction_query=st.text(max_size=120),
    range_query=st.text(max_size=120)
)
def test_fuzz_analytics_filters(
    client: TestClient,
    auth_headers,
    junction_query: str,
    range_query: str
):
    headers = auth_headers("priya", "operator")
    res = client.get(
        "/api/analytics",
        params={"junction": junction_query, "range": range_query},
        headers=headers
    )
    assert res.status_code != 500
    assert "Traceback" not in res.text
