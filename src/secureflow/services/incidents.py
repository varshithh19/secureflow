"""SecureFlow Incidents and Alerts Management Service.

Implements FR-07:
- Structured incident state transitions (OPEN -> INVESTIGATING -> RESOLVED -> CLOSED)
- Supervisor-only close authorization
- Alert lifecycle and incident derivation
- Audit logging for operational actions
"""
import time
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.models import Alert, Incident, IncidentNote
from secureflow.services.audit import write_audit


def create_incident(
    db: Session,
    title: str,
    jid: str,
    sev: str,
    desc: str,
    alert_id: Optional[str],
    user_id: str
) -> Incident:
    """Create a new incident and optionally acknowledge the source alert."""
    if len(title.strip()) < 5:
        raise ValueError("Give the incident a title of at least 5 characters.")

    # Generate sequence ID (INC-xxx)
    last_inc = db.execute(select(Incident).order_by(Incident.id.desc()).limit(1)).scalar_one_or_none()
    next_num = 1
    if last_inc and last_inc.id.startswith("INC-"):
        try:
            next_num = int(last_inc.id.split("-")[1]) + 1
        except Exception:
            next_num = 1
    inc_id = f"INC-{next_num:03d}"

    now_ms = int(time.time() * 1000)
    incident = Incident(
        id=inc_id,
        title=title.strip()[:100],
        jid=jid,
        sev=sev,
        status="OPEN",
        assignee=user_id,
        desc=(desc or "")[:500],
        ts=now_ms
    )
    db.add(incident)

    # If linked to an alert, acknowledge it
    if alert_id:
        alert = db.get(Alert, alert_id)
        if alert and not alert.ack_by:
            alert.ack_by = user_id

    db.commit()
    db.refresh(incident)

    write_audit(db, user_id, "INCIDENT_CREATED", incident.id, "OK", incident.sev)
    return incident


def update_incident_status(
    db: Session,
    incident_id: str,
    new_status: str,
    user_role: str,
    user_id: str
) -> Incident:
    """Transition incident status with role enforcement (CLOSED requires supervisor)."""
    incident = db.get(Incident, incident_id)
    if not incident:
        raise ValueError("Incident not found.")

    if new_status == "CLOSED" and user_role != "supervisor":
        raise PermissionError("Only a supervisor can close an incident.")

    incident.status = new_status
    db.commit()

    write_audit(db, user_id, f"INCIDENT_{new_status}", incident.id, "OK", f"status moved to {new_status}")
    return incident


def add_incident_note(
    db: Session,
    incident_id: str,
    text: str,
    user_id: str
) -> IncidentNote:
    """Add a timestamped progress note to an incident."""
    if not text or not text.strip():
        raise ValueError("Write a note before saving.")

    incident = db.get(Incident, incident_id)
    if not incident:
        raise ValueError("Incident not found.")

    now_ms = int(time.time() * 1000)
    note = IncidentNote(
        incident_id=incident_id,
        by=user_id,
        ts=now_ms,
        text=text.strip()[:300]
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    write_audit(db, user_id, "INCIDENT_NOTE", incident_id, "OK", "note added")
    return note


def ack_alert(
    db: Session,
    alert_id: str,
    user_id: str
) -> Alert:
    """Acknowledge an active operational alert."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise ValueError("Alert not found.")

    alert.ack_by = user_id
    db.commit()

    write_audit(db, user_id, "ALERT_ACK", alert.id, "OK", "acknowledged")
    return alert
