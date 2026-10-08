"""Unit tests for Telemetry Plausibility and Physical Limit Checks (SR-08 / THR-02)."""
import time
from sqlalchemy.orm import Session

from secureflow.core.security import compute_hmac_sha256
from secureflow.services.telemetry import validate_and_ingest_telemetry

SHARED_KEY = b"simulator-sensor-secret-key-32bytes"


def test_implausible_speed_flagged(db_session: Session):
    sensor_id = "SN-105"
    junction_id = "J-05"
    count = 10
    speed = 480.0  # Physically impossible speed (480 km/h)
    occ = 0.90
    now_ms = int(time.time() * 1000)
    nonce = "nonce-implausible-speed-1"

    msg = f"{sensor_id}|{junction_id}|{count}|{speed:.2f}|{occ:.4f}|{now_ms}|{nonce}".encode("utf-8")
    sig = compute_hmac_sha256(SHARED_KEY, msg)

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
    assert record is not None
    assert record.is_flagged is True
    assert "Out of physical bounds" in record.flag_reason


def test_contradictory_speed_and_occupancy_flagged(db_session: Session):
    sensor_id = "SN-105"
    junction_id = "J-05"
    count = 50
    speed = 120.0  # 120 km/h at 95% occupancy
    occ = 0.95
    now_ms = int(time.time() * 1000)
    nonce = "nonce-contradictory-1"

    msg = f"{sensor_id}|{junction_id}|{count}|{speed:.2f}|{occ:.4f}|{now_ms}|{nonce}".encode("utf-8")
    sig = compute_hmac_sha256(SHARED_KEY, msg)

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
    assert record is not None
    assert record.is_flagged is True
    assert "Contradictory traffic state" in record.flag_reason


def test_sudden_speed_jump_flagged(db_session: Session):
    sensor_id = "SN-102"
    junction_id = "J-02"
    now_ms = int(time.time() * 1000)

    # First baseline reading: 30 km/h
    msg1 = f"{sensor_id}|{junction_id}|20|30.00|0.4000|{now_ms}|nonce-jump-1".encode("utf-8")
    sig1 = compute_hmac_sha256(SHARED_KEY, msg1)
    validate_and_ingest_telemetry(
        db=db_session,
        sensor_id=sensor_id,
        junction_id=junction_id,
        vehicle_count=20,
        avg_speed=30.0,
        occupancy=0.40,
        timestamp=now_ms,
        nonce="nonce-jump-1",
        signature=sig1,
        device_secret_bytes=SHARED_KEY
    )

    # Second reading 1 second later with extreme jump to 130 km/h (+100 km/h in 1s)
    msg2 = f"{sensor_id}|{junction_id}|20|130.00|0.4000|{now_ms + 1000}|nonce-jump-2".encode("utf-8")
    sig2 = compute_hmac_sha256(SHARED_KEY, msg2)
    accepted, err, record2 = validate_and_ingest_telemetry(
        db=db_session,
        sensor_id=sensor_id,
        junction_id=junction_id,
        vehicle_count=20,
        avg_speed=130.0,
        occupancy=0.40,
        timestamp=now_ms + 1000,
        nonce="nonce-jump-2",
        signature=sig2,
        device_secret_bytes=SHARED_KEY
    )

    assert accepted is True
    assert record2.is_flagged is True
    assert "jump" in record2.flag_reason.lower()
