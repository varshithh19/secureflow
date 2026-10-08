"""SecureFlow Database Seeding Script.

Initializes the database with canonical junctions, sensors, demo users (Argon2 hashed),
initial change requests, incidents, alerts, and hash-chained audit log entries.
"""
import json
import time
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.core.constants import DEFAULT_JUNCTIONS, DEFAULT_SENSORS
from secureflow.core.security import generate_totp_secret, hash_device_secret, hash_password
from secureflow.models import (
    Alert,
    AuditLog,
    Corridor,
    Incident,
    IncidentNote,
    Junction,
    Sensor,
    SignalRequest,
    User,
)
from secureflow.repositories.database import SessionLocal, init_db
from secureflow.services.audit import write_audit


def seed_database(db: Session) -> None:
    """Seed the database with canonical initial data if empty."""
    if db.execute(select(User)).scalars().first():
        return  # Already seeded

    now_ms = int(time.time() * 1000)
    min_ms = 60000
    hr_ms = 3600000

    # 1. Seed Users (Argon2 Hashed Passwords)
    demo_pw = "Demo@1234"
    hashed_demo_pw = hash_password(demo_pw)

    users_data = [
        ("priya", "Priya Nair", "operator", False),
        ("rahul", "Rahul Menon", "operator", False),
        ("meera", "Meera Iyer", "supervisor", True),
        ("arjun", "Arjun Rao", "supervisor", True),
        ("sana", "Sana Khan", "admin", True),
        ("dev", "Dev Patel", "analyst", False),
        ("kavya", "Kavya Reddy", "auditor", False),
        ("ems", "Control EMS", "emergency_dispatcher", False),
    ]

    for uid, name, role, mfa in users_data:
        user = User(
            id=uid,
            name=name,
            hashed_password=hashed_demo_pw,
            role=role,
            mfa_enabled=mfa,
            totp_secret=generate_totp_secret() if mfa else None,
            locked=False,
            failed_attempts=0,
            last_login=now_ms - int(10 * min_ms)
        )
        db.add(user)

    # 2. Seed 9 Junctions
    for i, j in enumerate(DEFAULT_JUNCTIONS):
        junction = Junction(
            id=j["id"],
            name=j["name"],
            x=j["x"],
            y=j["y"],
            base=j["base"],
            occ=j["base"],
            speed=30,
            count=20,
            level=0 if j["base"] < 0.35 else 1 if j["base"] < 0.6 else 2 if j["base"] < 0.8 else 3,
            mode="Adaptive" if i % 3 else "Fixed time",
            plan_ns=45,
            plan_ew=40,
            plan_yellow=3,
            plan_allred=2,
            pi=i % 6,
            rem=5 + i * 3,
            corridor_id=None
        )
        db.add(junction)

    # 3. Seed Sensors
    shared_device_secret = "simulator-sensor-secret-key-32bytes"
    secret_hash = hash_device_secret(shared_device_secret)

    for i, s in enumerate(DEFAULT_SENSORS):
        sensor = Sensor(
            id=s["id"],
            type=s["type"],
            jid=s["jid"],
            status=s["status"],
            secret_hash=secret_hash,
            last_seen=now_ms - 8 * min_ms if s["id"] == "SN-107" else now_ms,
            quality=88 + (i % 11),
            loc=s["loc"]
        )
        db.add(sensor)

    # 4. Seed Requests
    req1 = SignalRequest(
        id="CR-001",
        jid="J-02",
        from_ns=45,
        from_ew=40,
        from_yellow=3,
        from_allred=2,
        plan_ns=50,
        plan_ew=35,
        plan_yellow=3,
        plan_allred=2,
        reason="Reduce queue on the harbour approach during morning peak",
        by="rahul",
        ts=now_ms - 5 * hr_ms,
        state="APPLIED",
        approver="meera",
        note=None
    )
    req2 = SignalRequest(
        id="CR-002",
        jid="J-05",
        from_ns=45,
        from_ew=40,
        from_yellow=3,
        from_allred=2,
        plan_ns=70,
        plan_ew=40,
        plan_yellow=3,
        plan_allred=2,
        reason="Station Square is saturated on the north-south axis",
        by="priya",
        ts=now_ms - 12 * min_ms,
        state="PROPOSED",
        approver=None,
        note=None
    )
    req3 = SignalRequest(
        id="CR-003",
        jid="J-03",
        from_ns=45,
        from_ew=40,
        from_yellow=3,
        from_allred=2,
        plan_ns=20,
        plan_ew=110,
        plan_yellow=3,
        plan_allred=2,
        reason="Try a longer east-west green for tech park exit traffic",
        by="priya",
        ts=now_ms - 26 * hr_ms,
        state="REJECTED",
        approver="arjun",
        note="East-west green is too long for the pedestrian crossing."
    )
    db.add_all([req1, req2, req3])

    # 5. Seed Corridors
    corridor1 = Corridor(
        id="EC-001",
        vehicle="EV-AMB-12",
        from_jid="J-07",
        to_jid="J-09",
        route_json=json.dumps(["J-07", "J-08", "J-09"]),
        by="ems",
        ts=now_ms - 3 * hr_ms,
        expires=now_ms - 3 * hr_ms + 120000,
        state="EXPIRED",
        reason="Patient transport"
    )
    db.add(corridor1)

    # 6. Seed Incidents & Notes
    inc1 = Incident(
        id="INC-001",
        title="Stalled bus at Station Square",
        jid="J-05",
        sev="HIGH",
        status="INVESTIGATING",
        assignee="priya",
        desc="Bus blocking the northbound lane. Tow requested.",
        ts=now_ms - 40 * min_ms
    )
    note1 = IncidentNote(
        incident_id="INC-001",
        by="priya",
        ts=now_ms - 30 * min_ms,
        text="Tow truck is 10 minutes away."
    )
    inc2 = Incident(
        id="INC-002",
        title="Controller timeout at Airport Link",
        jid="J-08",
        sev="MEDIUM",
        status="OPEN",
        assignee=None,
        desc="Signal controller missed two heartbeats.",
        ts=now_ms - 2 * hr_ms
    )
    inc3 = Incident(
        id="INC-003",
        title="Sensor SN-107 not reporting",
        jid="J-06",
        sev="LOW",
        status="OPEN",
        assignee=None,
        desc="No readings for 8 minutes.",
        ts=now_ms - 8 * min_ms
    )
    db.add_all([inc1, note1, inc2, inc3])

    # 7. Seed Alerts
    a1 = Alert(
        id="A-001",
        type="SENSOR_OFFLINE",
        sev="WARNING",
        jid="J-06",
        msg="Sensor SN-107 has not reported for 8 minutes.",
        ts=now_ms - 8 * min_ms,
        ack_by=None
    )
    a2 = Alert(
        id="A-002",
        type="SEVERE_CONGESTION",
        sev="CRITICAL",
        jid="J-05",
        msg="Station Square occupancy is above 80%.",
        ts=now_ms - 14 * min_ms,
        ack_by=None
    )
    a3 = Alert(
        id="A-003",
        type="FAILED_LOGINS",
        sev="WARNING",
        jid=None,
        msg="Three failed sign-ins for user rahul.",
        ts=now_ms - 50 * min_ms,
        ack_by=None
    )
    a4 = Alert(
        id="A-004",
        type="COMMAND_FAILED",
        sev="WARNING",
        jid="J-08",
        msg="Airport Link controller rejected an unsigned command.",
        ts=now_ms - 2 * hr_ms,
        ack_by="meera"
    )
    db.add_all([a1, a2, a3, a4])
    db.commit()

    # 8. Seed Hash-Chained Audit Logs
    audit_seeds = [
        ("LOGIN_SUCCESS", "meera", "auth", "OK", "MFA passed", 6.0),
        ("SIGNAL_CHANGE_PROPOSED", "rahul", "CR-001", "OK", "J-02", 5.1),
        ("SIGNAL_CHANGE_APPROVED", "meera", "CR-001", "OK", "two-person rule satisfied", 5.05),
        ("SIGNAL_CHANGE_APPLIED", "controller", "CR-001", "OK", "signed command verified", 5.0),
        ("INVALID_SIGNATURE", "SN-105", "telemetry", "DENIED", "HMAC mismatch", 3.0),
        ("LOGIN_FAILED", "rahul", "auth", "DENIED", "bad password", 1.0),
        ("EMERGENCY_REQUESTED", "ems", "EC-001", "OK", "EV-AMB-12 J-07 to J-09", 3.0),
        ("SIGNAL_CHANGE_REJECTED", "arjun", "CR-003", "OK", "pedestrian crossing", 26.0),
    ]

    # Sort chronological
    audit_seeds.sort(key=lambda x: x[5], reverse=True)
    for action, user_id, target, res, detail, hrs_ago in audit_seeds:
        write_audit(
            db=db,
            actor=user_id,
            action=action,
            target=target,
            result=res,
            detail=detail,
            ts=int(now_ms - hrs_ago * hr_ms)
        )


if __name__ == "__main__":
    init_db()
    session = SessionLocal()
    try:
        seed_database(session)
        print("Database seeded successfully with initial SecureFlow data.")
    finally:
        session.close()
