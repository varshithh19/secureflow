"""SecureFlow Sensor Management API Routers."""
import secrets
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.core.rbac import AuthenticatedUser, require
from secureflow.core.security import hash_device_secret
from secureflow.events.broker import broker
from secureflow.models import Sensor
from secureflow.repositories.database import get_db
from secureflow.schemas import (
    RegisterSensorRequest,
    RegisterSensorResponse,
    SensorResponse,
)
from secureflow.services.audit import write_audit

sensors_router = APIRouter(prefix="/api/sensors", tags=["sensors"])
admin_sensors_router = APIRouter(prefix="/api/admin/sensors", tags=["admin_sensors"])


@sensors_router.get("", response_model=List[SensorResponse])
async def list_sensors(
    user: AuthenticatedUser = Depends(require("sensor.view")),
    db: Session = Depends(get_db)
):
    """List all traffic sensors."""
    sensors = db.execute(select(Sensor).order_by(Sensor.id.asc())).scalars().all()
    return [
        SensorResponse(
            id=s.id,
            type=s.type,
            jid=s.jid,
            status=s.status,
            lastSeen=s.last_seen,
            quality=s.quality,
            loc=s.loc
        )
        for s in sensors
    ]


@admin_sensors_router.post("", response_model=RegisterSensorResponse)
async def register_sensor(
    payload: RegisterSensorRequest,
    user: AuthenticatedUser = Depends(require("sensor.manage")),
    db: Session = Depends(get_db)
):
    """Register a new sensor and return a single-use secret key."""
    # Find next sensor sequence ID
    last_sensor = db.execute(select(Sensor).order_by(Sensor.id.desc()).limit(1)).scalar_one_or_none()
    next_num = 113
    if last_sensor and last_sensor.id.startswith("SN-"):
        try:
            next_num = int(last_sensor.id.split("-")[1]) + 1
        except Exception:
            next_num = 113
    sensor_id = f"SN-{next_num}"

    raw_secret = secrets.token_hex(16)
    secret_hash = hash_device_secret(raw_secret)
    now_ms = int(time.time() * 1000)

    sensor = Sensor(
        id=sensor_id,
        type=payload.type,
        jid=payload.jid,
        status="PENDING",
        secret_hash=secret_hash,
        last_seen=now_ms,
        quality=0,
        loc=payload.loc or "Approach N"
    )
    db.add(sensor)
    db.commit()
    db.refresh(sensor)

    write_audit(db, user.id, "SENSOR_REGISTERED", sensor.id, "OK", f"{payload.type} {payload.jid}")

    return RegisterSensorResponse(
        sensor=SensorResponse(
            id=sensor.id,
            type=sensor.type,
            jid=sensor.jid,
            status=sensor.status,
            lastSeen=sensor.last_seen,
            quality=sensor.quality,
            loc=sensor.loc
        ),
        secret=raw_secret
    )


@admin_sensors_router.post("/{sensor_id}/activate", response_model=SensorResponse)
async def activate_sensor(
    sensor_id: str,
    user: AuthenticatedUser = Depends(require("sensor.manage")),
    db: Session = Depends(get_db)
):
    """Activate a pending sensor."""
    sensor = db.get(Sensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found.")

    sensor.status = "ACTIVE"
    sensor.last_seen = int(time.time() * 1000)
    sensor.quality = 92
    db.commit()

    write_audit(db, user.id, "SENSOR_ACTIVATED", sensor.id, "OK", "sensor activated")
    broker.publish("sensor.update", {
        "id": sensor.id,
        "type": sensor.type,
        "jid": sensor.jid,
        "status": sensor.status,
        "lastSeen": sensor.last_seen,
        "quality": sensor.quality,
        "loc": sensor.loc
    })

    return SensorResponse(
        id=sensor.id,
        type=sensor.type,
        jid=sensor.jid,
        status=sensor.status,
        lastSeen=sensor.last_seen,
        quality=sensor.quality,
        loc=sensor.loc
    )


@admin_sensors_router.post("/{sensor_id}/revoke", response_model=SensorResponse)
async def revoke_sensor(
    sensor_id: str,
    user: AuthenticatedUser = Depends(require("sensor.manage")),
    db: Session = Depends(get_db)
):
    """Revoke a sensor permanently."""
    sensor = db.get(Sensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found.")

    sensor.status = "REVOKED"
    db.commit()

    write_audit(db, user.id, "SENSOR_REVOKED", sensor.id, "OK", "sensor revoked")
    broker.publish("sensor.update", {
        "id": sensor.id,
        "type": sensor.type,
        "jid": sensor.jid,
        "status": sensor.status,
        "lastSeen": sensor.last_seen,
        "quality": sensor.quality,
        "loc": sensor.loc
    })

    return SensorResponse(
        id=sensor.id,
        type=sensor.type,
        jid=sensor.jid,
        status=sensor.status,
        lastSeen=sensor.last_seen,
        quality=sensor.quality,
        loc=sensor.loc
    )
