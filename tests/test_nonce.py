"""Unit tests for Telemetry Nonce Replay Store (SR-02 / THR-03)."""
import time
from sqlalchemy.orm import Session

from secureflow.core.security import compute_hmac_sha256
from secureflow.models import NonceRecord
from secureflow.services.telemetry import validate_and_ingest_telemetry

SHARED_KEY = b"simulator-sensor-secret-key-32bytes"


def test_nonce_single_use_and_replay_rejection(db_session: Session):
    sensor_id = "SN-101"
    junction_id = "J-01"
    count = 20
    speed = 45.0
    occ = 0.40
    now_ms = int(time.time() * 1000)
    nonce = "unique-nonce-12345678"

    msg = f"{sensor_id}|{junction_id}|{count}|{speed:.2f}|{occ:.4f}|{now_ms}|{nonce}".encode("utf-8")
    sig = compute_hmac_sha256(SHARED_KEY, msg)

    # First transmission: should succeed
    accepted, err, record = validate_and_ingest_telemetry(
        db=db_session,
        sensor_id=sensor_id,
        junction_id=junction_id,
        vehicle_count=count,
        avg_speed=speed,
        occupancy=occ,
        timestamp=now_ms,
        nonce=nonce,
        signature=sig,
        device_secret_bytes=SHARED_KEY
    )
    assert accepted is True
    assert err is None
    assert record is not None

    # Check nonce was saved
    saved_nonce = db_session.get(NonceRecord, nonce)
    assert saved_nonce is not None
    assert saved_nonce.sensor_id == sensor_id

    # Second transmission with exact same nonce: must be rejected as replay
    accepted2, err2, record2 = validate_and_ingest_telemetry(
        db=db_session,
        sensor_id=sensor_id,
        junction_id=junction_id,
        vehicle_count=count,
        avg_speed=speed,
        occupancy=occ,
        timestamp=now_ms,
        nonce=nonce,
        signature=sig,
        device_secret_bytes=SHARED_KEY
    )
    assert accepted2 is False
    assert "Replay detected" in err2
    assert record2 is None


def test_stale_timestamp_rejection(db_session: Session):
    sensor_id = "SN-101"
    junction_id = "J-01"
    stale_ts = int(time.time() * 1000) - 45000  # 45 seconds old (> 30s window)
    nonce = "stale-nonce-87654321"

    msg = f"{sensor_id}|{junction_id}|20|45.00|0.4000|{stale_ts}|{nonce}".encode("utf-8")
    sig = compute_hmac_sha256(SHARED_KEY, msg)

    accepted, err, record = validate_and_ingest_telemetry(
        db=db_session,
        sensor_id=sensor_id,
        junction_id=junction_id,
        vehicle_count=20,
        avg_speed=45.0,
        occupancy=0.40,
        timestamp=stale_ts,
        nonce=nonce,
        signature=sig,
        device_secret_bytes=SHARED_KEY
    )
    assert accepted is False
    assert "30-second window" in err
