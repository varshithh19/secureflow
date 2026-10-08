"""SecureFlow Congestion Detection Strategy & Alert Generator.

Implements FR-03, FR-07:
- Strategy Pattern for level calculations (Low, Moderate, High, Severe)
- Thresholds (<0.35, <0.60, <0.80, >=0.80)
- Critical alert triggering with 5-minute deduplication
- 90-second sensor offline alarm
"""
import time
from abc import ABC, abstractmethod
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.events.broker import broker
from secureflow.models import Alert, Junction, Sensor, TelemetryRecord
from secureflow.services.audit import write_audit


class CongestionStrategy(ABC):
    """Abstract Strategy interface for calculating traffic congestion level."""

    @abstractmethod
    def calculate_level(self, occupancy: float) -> int:
        pass

    @abstractmethod
    def get_level_name(self, level_idx: int) -> str:
        pass


class StandardThresholdStrategy(CongestionStrategy):
    """Standard urban traffic threshold strategy."""

    LEVEL_NAMES = ["Low", "Moderate", "High", "Severe"]

    def calculate_level(self, occupancy: float) -> int:
        if occupancy < 0.35:
            return 0  # Low
        elif occupancy < 0.60:
            return 1  # Moderate
        elif occupancy < 0.80:
            return 2  # High
        else:
            return 3  # Severe

    def get_level_name(self, level_idx: int) -> str:
        idx = max(0, min(level_idx, len(self.LEVEL_NAMES) - 1))
        return self.LEVEL_NAMES[idx]


congestion_strategy = StandardThresholdStrategy()


def raise_alert_if_not_deduped(
    db: Session,
    alert_type: str,
    sev: str,
    jid: Optional[str],
    msg: str,
    dedup_window_sec: int = 300
) -> Optional[Alert]:
    """Create a new alert if a duplicate unacknowledged alert has not been created in the last 5 min."""
    now_ms = int(time.time() * 1000)
    cutoff_ms = now_ms - (dedup_window_sec * 1000)

    existing = db.execute(
        select(Alert).filter(
            Alert.type == alert_type,
            Alert.jid == jid,
            Alert.ack_by.is_(None),
            Alert.ts >= cutoff_ms
        )
    ).scalars().first()

    if existing:
        return None

    # Generate next Alert ID e.g. A-005
    last_alert = db.execute(select(Alert).order_by(Alert.id.desc()).limit(1)).scalar_one_or_none()
    next_num = 1
    if last_alert and last_alert.id.startswith("A-"):
        try:
            next_num = int(last_alert.id.split("-")[1]) + 1
        except Exception:
            next_num = 1
    alert_id = f"A-{next_num:03d}"

    alert = Alert(
        id=alert_id,
        type=alert_type,
        sev=sev,
        jid=jid,
        msg=msg,
        ts=now_ms,
        ack_by=None
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Broadcast via SSE broker
    broker.publish("alert.new", {
        "id": alert.id,
        "type": alert.type,
        "sev": alert.sev,
        "jid": alert.jid,
        "msg": alert.msg,
        "ts": alert.ts,
        "ack": alert.ack_by
    })

    return alert


def update_junction_congestion(db: Session, junction_id: str) -> Optional[Junction]:
    """Compute moving average traffic metrics for a junction and update state."""
    junction = db.get(Junction, junction_id)
    if not junction:
        return None

    now_ms = int(time.time() * 1000)
    # Query non-flagged readings in the last 60 seconds
    recent_readings = db.execute(
        select(TelemetryRecord).filter(
            TelemetryRecord.jid == junction_id,
            TelemetryRecord.is_flagged.is_(False),
            TelemetryRecord.timestamp >= (now_ms - 60000)
        )
    ).scalars().all()

    if recent_readings:
        avg_occ = sum(r.occupancy for r in recent_readings) / len(recent_readings)
        avg_spd = sum(r.avg_speed for r in recent_readings) / len(recent_readings)
        avg_cnt = sum(r.vehicle_count for r in recent_readings) / len(recent_readings)

        junction.occ = round(avg_occ, 4)
        junction.speed = int(avg_spd)
        junction.count = int(avg_cnt)

    new_level = congestion_strategy.calculate_level(junction.occ)
    old_level = junction.level
    junction.level = new_level

    # Severe congestion alert (entering level 3 / Severe)
    if new_level == 3 and old_level != 3:
        raise_alert_if_not_deduped(
            db=db,
            alert_type="SEVERE_CONGESTION",
            sev="CRITICAL",
            jid=junction.id,
            msg=f"{junction.name} occupancy is above 80%."
        )

    db.commit()
    db.refresh(junction)

    # Broadcast junction update
    broker.publish("junction.update", {
        "id": junction.id,
        "name": junction.name,
        "x": junction.x,
        "y": junction.y,
        "base": junction.base,
        "occ": junction.occ,
        "speed": junction.speed,
        "count": junction.count,
        "level": junction.level,
        "mode": junction.mode,
        "plan": {
            "ns": junction.plan_ns,
            "ew": junction.plan_ew,
            "yellow": junction.plan_yellow,
            "allred": junction.plan_allred
        },
        "pi": junction.pi,
        "rem": junction.rem,
        "corridor": junction.corridor_id
    })

    return junction


def check_sensors_health(db: Session) -> List[Sensor]:
    """Detect sensors that have not reported for 90 seconds and raise SENSOR_OFFLINE alerts."""
    now_ms = int(time.time() * 1000)
    cutoff_ms = now_ms - 90000

    sensors = db.execute(select(Sensor).filter(Sensor.status == "ACTIVE")).scalars().all()
    offline_sensors: List[Sensor] = []

    for sensor in sensors:
        if sensor.last_seen and sensor.last_seen < cutoff_ms:
            offline_sensors.append(sensor)
            raise_alert_if_not_deduped(
                db=db,
                alert_type="SENSOR_OFFLINE",
                sev="WARNING",
                jid=sensor.jid,
                msg=f"Sensor {sensor.id} has not reported for 90 seconds."
            )

    return offline_sensors
