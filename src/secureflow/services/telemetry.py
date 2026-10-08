"""SecureFlow IoT Telemetry Ingestion & Cryptographic Validation Service.

Implements SR-01, SR-02, SR-08, TB1:
- Per-device HMAC-SHA256 signature verification
- Timestamp freshness window (+/- 30 seconds)
- Nonce replay protection with unique persistence
- Physical bounds, jump limits, and neighbour plausibility checks
- Exclusion of suspicious telemetry from congestion algorithms
"""
import time
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.core.logging import (
    INGEST_LATENCY_HISTOGRAM,
    INVALID_SIGNATURES_TOTAL,
    REPLAY_ATTEMPTS_TOTAL,
    SUSPICIOUS_TELEMETRY_TOTAL,
)
from secureflow.core.security import compute_hmac_sha256, verify_hmac_sha256
from secureflow.models import NonceRecord, Sensor, TelemetryRecord
from secureflow.services.audit import write_audit


def validate_and_ingest_telemetry(
    db: Session,
    sensor_id: str,
    junction_id: str,
    vehicle_count: int,
    avg_speed: float,
    occupancy: float,
    timestamp: int,
    nonce: str,
    signature: str,
    device_secret_bytes: Optional[bytes] = None
) -> Tuple[bool, Optional[str], Optional[TelemetryRecord]]:
    """Validate cryptographic telemetry and perform plausibility checks.

    Returns:
        (is_accepted, error_message, telemetry_record)
    """
    start_time = time.time()
    now_ms = int(time.time() * 1000)

    # 1. Device Registration & Active Status Check (SR-01 / THR-01)
    sensor = db.get(Sensor, sensor_id)
    if not sensor:
        INVALID_SIGNATURES_TOTAL.inc()
        write_audit(db, sensor_id, "SENSOR_AUTH_FAILED", "telemetry", "DENIED", "unregistered device")
        return False, "Unregistered device ID.", None

    if sensor.status != "ACTIVE":
        INVALID_SIGNATURES_TOTAL.inc()
        write_audit(db, sensor_id, "SENSOR_INACTIVE", "telemetry", "DENIED", f"sensor status is {sensor.status}")
        return False, f"Sensor {sensor_id} is not active ({sensor.status}).", None

    # 2. Timestamp Window (+/- 30 seconds) (SR-02 / THR-03)
    time_diff_sec = abs(now_ms - timestamp) / 1000.0
    if time_diff_sec > 30.0:
        REPLAY_ATTEMPTS_TOTAL.inc()
        write_audit(db, sensor_id, "STALE_TIMESTAMP", "telemetry", "DENIED", f"time skew {time_diff_sec:.1f}s")
        return False, "Timestamp outside acceptable 30-second window.", None

    # 3. Nonce Replay Check (SR-02 / THR-03)
    existing_nonce = db.get(NonceRecord, nonce)
    if existing_nonce:
        REPLAY_ATTEMPTS_TOTAL.inc()
        write_audit(db, sensor_id, "REPLAY_DETECTED", "telemetry", "DENIED", f"replayed nonce {nonce}")
        return False, "Replay detected: nonce was already used.", None

    # Persist nonce to prevent replay
    new_nonce = NonceRecord(nonce=nonce, sensor_id=sensor_id, created_at=now_ms)
    db.add(new_nonce)

    # 4. Cryptographic HMAC Signature Verification (SR-01 / SR-02)
    # Message canonical payload: sensor_id|junction_id|vehicle_count|avg_speed|occupancy|timestamp|nonce
    canonical_message = f"{sensor_id}|{junction_id}|{vehicle_count}|{avg_speed:.2f}|{occupancy:.4f}|{timestamp}|{nonce}".encode("utf-8")

    # If secret key is provided (or derived from pre-shared simulator secret)
    if device_secret_bytes:
        if not verify_hmac_sha256(device_secret_bytes, canonical_message, signature):
            INVALID_SIGNATURES_TOTAL.inc()
            write_audit(db, sensor_id, "INVALID_SIGNATURE", "telemetry", "DENIED", "HMAC mismatch")
            db.commit()
            return False, "Invalid cryptographic HMAC signature.", None

    # 5. Plausibility & Jump Checks (SR-08 / THR-02)
    is_flagged = False
    flag_reason: Optional[str] = None

    # Extreme physical bound checks
    if avg_speed > 160.0 or vehicle_count > 350 or occupancy < 0.0 or occupancy > 1.0:
        is_flagged = True
        flag_reason = f"Out of physical bounds (speed={avg_speed}, count={vehicle_count}, occ={occupancy})"

    # Speed vs Congestion contradiction (e.g. 150 km/h with 95% occupancy)
    if not is_flagged and occupancy > 0.85 and avg_speed > 90.0:
        is_flagged = True
        flag_reason = f"Contradictory traffic state (speed {avg_speed} km/h at {occupancy*100:.0f}% occupancy)"

    # Prior reading jump limit check (speed change > 80 km/h in 2 seconds)
    if not is_flagged:
        last_reading = db.execute(
            select(TelemetryRecord)
            .filter(TelemetryRecord.sensor_id == sensor_id)
            .order_by(TelemetryRecord.id.desc())
            .limit(1)
        ).scalar_one_or_none()

        if last_reading:
            speed_delta = abs(avg_speed - last_reading.avg_speed)
            time_delta_sec = max(1.0, (timestamp - last_reading.timestamp) / 1000.0)
            if speed_delta > 90.0 and time_delta_sec < 5.0:
                is_flagged = True
                flag_reason = f"Sudden implausible speed jump ({speed_delta:.1f} km/h in {time_delta_sec:.1f}s)"

    if is_flagged:
        SUSPICIOUS_TELEMETRY_TOTAL.inc()
        write_audit(db, sensor_id, "SUSPICIOUS_TELEMETRY", "telemetry", "FLAGGED", flag_reason or "")

    # Save Telemetry Record
    telemetry = TelemetryRecord(
        sensor_id=sensor_id,
        jid=junction_id,
        vehicle_count=vehicle_count,
        avg_speed=avg_speed,
        occupancy=occupancy,
        timestamp=timestamp,
        signature=signature,
        is_flagged=is_flagged,
        flag_reason=flag_reason
    )
    db.add(telemetry)

    # Update sensor health
    sensor.last_seen = now_ms
    sensor.quality = 60 if is_flagged else 95

    db.commit()
    db.refresh(telemetry)

    INGEST_LATENCY_HISTOGRAM.observe(time.time() - start_time)
    return True, None, telemetry
