"""SecureFlow Database Seeding Script.

Initializes the database with canonical junctions, sensors, demo users (Argon2 hashed),
initial change requests, incidents, alerts, and hash-chained audit log entries.
"""
import json
import sys
import time
from pathlib import Path

# Add src to Python path so secureflow can be imported when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

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
    now_ms = int(time.time() * 1000)
    min_ms = 60000
    hr_ms = 3600000

    # 1. Seed Users (Argon2 Hashed Passwords)
    demo_pw = "Demo@1234"
    hashed_demo_pw = hash_password(demo_pw)
    hashed_op_pw = hash_password("Operator#2026!")
    hashed_sup_pw = hash_password("Supervisor#2026!")
    hashed_adm_pw = hash_password("Admin#2026!")

    users_data = [
        # Canonical prototype accounts
        ("priya", "Priya Nair", "operator", False, hashed_demo_pw),
        ("rahul", "Rahul Menon", "operator", False, hashed_demo_pw),
        ("meera", "Meera Iyer", "supervisor", True, hashed_demo_pw),
        ("arjun", "Arjun Rao", "supervisor", True, hashed_demo_pw),
        ("sana", "Sana Khan", "admin", True, hashed_demo_pw),
        ("dev", "Dev Patel", "analyst", False, hashed_demo_pw),
        ("kavya", "Kavya Reddy", "auditor", False, hashed_demo_pw),
        ("ems", "Control EMS", "emergency_dispatcher", False, hashed_demo_pw),
        # Convenience aliases
        ("operator1", "Operator 1", "operator", False, hashed_op_pw),
        ("supervisor1", "Supervisor 1", "supervisor", True, hashed_sup_pw),
        ("admin1", "Administrator 1", "admin", True, hashed_adm_pw),
        ("dispatcher1", "Dispatcher 1", "emergency_dispatcher", False, hashed_demo_pw),
        ("analyst1", "Analyst 1", "analyst", False, hashed_demo_pw),
        ("auditor1", "Auditor 1", "auditor", False, hashed_demo_pw),
    ]

    for uid, name, role, mfa, hpw in users_data:
        existing = db.get(User, uid)
        if not existing:
            user = User(
                id=uid,
                name=name,
                hashed_password=hpw,
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
        if not db.get(Junction, j["id"]):
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
        if not db.get(Sensor, s["id"]):
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
    req_data = [
        ("CR-001", "J-02", 45, 40, 3, 2, 50, 35, 3, 2, "Reduce queue on the harbour approach during morning peak", "rahul", now_ms - 5 * hr_ms, "APPLIED", "meera", None),
        ("CR-002", "J-05", 45, 40, 3, 2, 70, 40, 3, 2, "Station Square is saturated on the north-south axis", "priya", now_ms - 12 * min_ms, "PROPOSED", None, None),
        ("CR-003", "J-03", 45, 40, 3, 2, 20, 110, 3, 2, "Try a longer east-west green for tech park exit traffic", "priya", now_ms - 26 * hr_ms, "REJECTED", "arjun", "East-west green is too long for the pedestrian crossing."),
    ]
    for rid, jid, fns, few, fy, fr, pns, pew, py, pr, reason, by, ts, state, approver, note in req_data:
        if not db.get(SignalRequest, rid):
            db.add(SignalRequest(
                id=rid, jid=jid, from_ns=fns, from_ew=few, from_yellow=fy, from_allred=fr,
                plan_ns=pns, plan_ew=pew, plan_yellow=py, plan_allred=pr,
                reason=reason, by=by, ts=ts, state=state, approver=approver, note=note
            ))

    # 5. Seed Corridors
    if not db.get(Corridor, "EC-001"):
        db.add(Corridor(
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
        ))

    # 6. Seed Incidents & Notes
    if not db.get(Incident, "INC-001"):
        db.add(Incident(
            id="INC-001",
            title="Stalled bus at Station Square",
            jid="J-05",
            sev="HIGH",
            status="INVESTIGATING",
            assignee="priya",
            desc="Bus blocking the northbound lane. Tow requested.",
            ts=now_ms - 40 * min_ms
        ))
        db.add(IncidentNote(
            incident_id="INC-001",
            by="priya",
            ts=now_ms - 30 * min_ms,
            text="Tow truck is 10 minutes away."
        ))
    if not db.get(Incident, "INC-002"):
        db.add(Incident(
            id="INC-002",
            title="Controller timeout at Airport Link",
            jid="J-08",
            sev="MEDIUM",
            status="OPEN",
            assignee=None,
            desc="Signal controller missed two heartbeats.",
            ts=now_ms - 2 * hr_ms
        ))
    if not db.get(Incident, "INC-003"):
        db.add(Incident(
            id="INC-003",
            title="Sensor SN-107 not reporting",
            jid="J-06",
            sev="LOW",
            status="OPEN",
            assignee=None,
            desc="No readings for 8 minutes.",
            ts=now_ms - 8 * min_ms
        ))

    # 7. Seed Alerts
    alert_seeds = [
        ("A-001", "SENSOR_OFFLINE", "WARNING", "J-06", "Sensor SN-107 has not reported for 8 minutes.", now_ms - 8 * min_ms, None),
        ("A-002", "SEVERE_CONGESTION", "CRITICAL", "J-05", "Station Square occupancy is above 80%.", now_ms - 14 * min_ms, None),
        ("A-003", "FAILED_LOGINS", "WARNING", None, "Three failed sign-ins for user rahul.", now_ms - 50 * min_ms, None),
        ("A-004", "COMMAND_FAILED", "WARNING", "J-08", "Airport Link controller rejected an unsigned command.", now_ms - 2 * hr_ms, "meera")
    ]
    for aid, atype, asev, ajid, amsg, ats, aack in alert_seeds:
        if not db.get(Alert, aid):
            db.add(Alert(id=aid, type=atype, sev=asev, jid=ajid, msg=amsg, ts=ats, ack_by=aack))

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
