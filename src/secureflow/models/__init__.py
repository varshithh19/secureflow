"""SecureFlow SQLAlchemy Models."""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secureflow.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # username slug e.g. "priya"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_login: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class Junction(Base):
    __tablename__ = "junctions"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # "J-01"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    base: Mapped[float] = mapped_column(Float, default=0.5)
    occ: Mapped[float] = mapped_column(Float, default=0.5)
    speed: Mapped[int] = mapped_column(Integer, default=30)
    count: Mapped[int] = mapped_column(Integer, default=20)
    level: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str] = mapped_column(String(50), default="Fixed time")
    plan_ns: Mapped[int] = mapped_column(Integer, default=45)
    plan_ew: Mapped[int] = mapped_column(Integer, default=40)
    plan_yellow: Mapped[int] = mapped_column(Integer, default=3)
    plan_allred: Mapped[int] = mapped_column(Integer, default=2)
    pi: Mapped[int] = mapped_column(Integer, default=0)
    rem: Mapped[int] = mapped_column(Integer, default=45)
    corridor_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # "SN-101"
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # camera, loop, radar
    jid: Mapped[str] = mapped_column(String(20), ForeignKey("junctions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, ACTIVE, REVOKED
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    last_seen: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    quality: Mapped[int] = mapped_column(Integer, default=90)
    loc: Mapped[str] = mapped_column(String(100), default="Approach N")


class SignalRequest(Base):
    __tablename__ = "signal_requests"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # "CR-001"
    jid: Mapped[str] = mapped_column(String(20), ForeignKey("junctions.id"), nullable=False)
    from_ns: Mapped[int] = mapped_column(Integer, nullable=False)
    from_ew: Mapped[int] = mapped_column(Integer, nullable=False)
    from_yellow: Mapped[int] = mapped_column(Integer, nullable=False)
    from_allred: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_ns: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_ew: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_yellow: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_allred: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    by: Mapped[str] = mapped_column(String(50), nullable=False)
    ts: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state: Mapped[str] = mapped_column(String(50), default="PROPOSED")  # PROPOSED, APPROVED, APPLIED, REJECTED, EXPIRED
    approver: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Corridor(Base):
    __tablename__ = "corridors"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # "EC-001"
    vehicle: Mapped[str] = mapped_column(String(50), nullable=False)
    from_jid: Mapped[str] = mapped_column(String(20), nullable=False)
    to_jid: Mapped[str] = mapped_column(String(20), nullable=False)
    route_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of junction IDs
    by: Mapped[str] = mapped_column(String(50), nullable=False)
    ts: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state: Mapped[str] = mapped_column(String(50), default="ACTIVE")  # ACTIVE, EXPIRED, CANCELLED
    reason: Mapped[str] = mapped_column(String(100), nullable=False)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # "INC-001"
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    jid: Mapped[str] = mapped_column(String(20), ForeignKey("junctions.id"), nullable=False)
    sev: Mapped[str] = mapped_column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    status: Mapped[str] = mapped_column(String(20), default="OPEN")  # OPEN, INVESTIGATING, RESOLVED, CLOSED
    assignee: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    desc: Mapped[str] = mapped_column(Text, default="")
    ts: Mapped[int] = mapped_column(BigInteger, nullable=False)

    notes: Mapped[List["IncidentNote"]] = relationship("IncidentNote", back_populates="incident", cascade="all, delete-orphan")


class IncidentNote(Base):
    __tablename__ = "incident_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(50), ForeignKey("incidents.id"), nullable=False)
    by: Mapped[str] = mapped_column(String(50), nullable=False)
    ts: Mapped[int] = mapped_column(BigInteger, nullable=False)
    text: Mapped[str] = mapped_column(String(500), nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="notes")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # "A-001"
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    sev: Mapped[str] = mapped_column(String(20), nullable=False)  # INFO, WARNING, CRITICAL
    jid: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    msg: Mapped[str] = mapped_column(String(255), nullable=False)
    ts: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ack_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[int] = mapped_column(BigInteger, nullable=False)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str] = mapped_column(String(100), nullable=False)
    result: Mapped[str] = mapped_column(String(20), default="OK")
    detail: Mapped[str] = mapped_column(Text, default="")
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)


class NonceRecord(Base):
    __tablename__ = "nonces"

    nonce: Mapped[str] = mapped_column(String(64), primary_key=True)
    sensor_id: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[str] = mapped_column(String(50), nullable=False)
    jid: Mapped[str] = mapped_column(String(20), nullable=False)
    vehicle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_speed: Mapped[float] = mapped_column(Float, nullable=False)
    occupancy: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    signature: Mapped[str] = mapped_column(String(64), nullable=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
