"""SecureFlow Emergency Corridor, Incidents, and Alerts API Routers."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.core.rbac import AuthenticatedUser, require
from secureflow.models import Alert, Corridor, Incident
from secureflow.repositories.database import get_db
from secureflow.schemas import (
    AddIncidentNoteRequest,
    AlertResponse,
    CorridorResponse,
    CreateEmergencyRequest,
    CreateIncidentRequest,
    IncidentNoteResponse,
    IncidentResponse,
    UpdateIncidentStatusRequest,
)
from secureflow.services.emergency import (
    cancel_emergency_corridor,
    create_emergency_corridor,
    expire_corridors_check,
)
from secureflow.services.incidents import (
    ack_alert,
    add_incident_note,
    create_incident,
    update_incident_status,
)

emergency_router = APIRouter(prefix="/api/emergency", tags=["emergency"])
incidents_router = APIRouter(prefix="/api/incidents", tags=["incidents"])
alerts_router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# Emergency Endpoints
@emergency_router.get("", response_model=List[CorridorResponse])
async def list_corridors(
    user: AuthenticatedUser = Depends(require("emergency.view")),
    db: Session = Depends(get_db)
):
    """List all emergency corridors."""
    expire_corridors_check(db)
    corridors = db.execute(select(Corridor).order_by(Corridor.ts.desc())).scalars().all()
    results = []
    for c in corridors:
        results.append(CorridorResponse(
            id=c.id,
            vehicle=c.vehicle,
            from_=c.from_jid,
            to=c.to_jid,
            route=json.loads(c.route_json),
            by=c.by,
            ts=c.ts,
            expires=c.expires,
            state=c.state,
            reason=c.reason
        ))
    return results


@emergency_router.post("", response_model=CorridorResponse)
async def create_corridor(
    payload: CreateEmergencyRequest,
    user: AuthenticatedUser = Depends(require("emergency.create")),
    db: Session = Depends(get_db)
):
    """Request a priority green corridor for an emergency vehicle."""
    try:
        c = create_emergency_corridor(
            db=db,
            vehicle=payload.vehicle,
            from_jid=payload.from_junction,
            to_jid=payload.to_junction,
            duration=payload.duration,
            reason=payload.reason,
            dispatcher_id=user.id
        )
        return CorridorResponse(
            id=c.id,
            vehicle=c.vehicle,
            from_=c.from_jid,
            to=c.to_jid,
            route=json.loads(c.route_json),
            by=c.by,
            ts=c.ts,
            expires=c.expires,
            state=c.state,
            reason=c.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@emergency_router.delete("/{corridor_id}", response_model=CorridorResponse)
async def cancel_corridor(
    corridor_id: str,
    user: AuthenticatedUser = Depends(require("emergency.cancel")),
    db: Session = Depends(get_db)
):
    """Cancel an active green corridor."""
    try:
        c = cancel_emergency_corridor(db, corridor_id, user.id)
        return CorridorResponse(
            id=c.id,
            vehicle=c.vehicle,
            from_=c.from_jid,
            to=c.to_jid,
            route=json.loads(c.route_json),
            by=c.by,
            ts=c.ts,
            expires=c.expires,
            state=c.state,
            reason=c.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# Incident Endpoints
@incidents_router.get("", response_model=List[IncidentResponse])
async def list_incidents(
    user: AuthenticatedUser = Depends(require("incident.view")),
    db: Session = Depends(get_db)
):
    """List operational incidents."""
    incidents = db.execute(select(Incident).order_by(Incident.ts.desc())).scalars().all()
    results = []
    for inc in incidents:
        notes = [
            IncidentNoteResponse(by=n.by, ts=n.ts, text=n.text)
            for n in inc.notes
        ]
        results.append(IncidentResponse(
            id=inc.id,
            title=inc.title,
            jid=inc.jid,
            sev=inc.sev,
            status=inc.status,
            assignee=inc.assignee,
            desc=inc.desc,
            ts=inc.ts,
            notes=notes
        ))
    return results


@incidents_router.post("", response_model=IncidentResponse)
async def create_new_incident(
    payload: CreateIncidentRequest,
    user: AuthenticatedUser = Depends(require("incident.write")),
    db: Session = Depends(get_db)
):
    """Create a new incident."""
    try:
        inc = create_incident(
            db=db,
            title=payload.title,
            jid=payload.jid,
            sev=payload.sev,
            desc=payload.desc or "",
            alert_id=payload.alert_id,
            user_id=user.id
        )
        return IncidentResponse(
            id=inc.id,
            title=inc.title,
            jid=inc.jid,
            sev=inc.sev,
            status=inc.status,
            assignee=inc.assignee,
            desc=inc.desc,
            ts=inc.ts,
            notes=[]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@incidents_router.patch("/{incident_id}/status", response_model=IncidentResponse)
async def update_status(
    incident_id: str,
    payload: UpdateIncidentStatusRequest,
    user: AuthenticatedUser = Depends(require("incident.write")),
    db: Session = Depends(get_db)
):
    """Update incident lifecycle state."""
    try:
        inc = update_incident_status(
            db=db,
            incident_id=incident_id,
            new_status=payload.status,
            user_role=user.role,
            user_id=user.id
        )
        notes = [IncidentNoteResponse(by=n.by, ts=n.ts, text=n.text) for n in inc.notes]
        return IncidentResponse(
            id=inc.id,
            title=inc.title,
            jid=inc.jid,
            sev=inc.sev,
            status=inc.status,
            assignee=inc.assignee,
            desc=inc.desc,
            ts=inc.ts,
            notes=notes
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@incidents_router.post("/{incident_id}/notes", response_model=IncidentNoteResponse)
async def add_note(
    incident_id: str,
    payload: AddIncidentNoteRequest,
    user: AuthenticatedUser = Depends(require("incident.write")),
    db: Session = Depends(get_db)
):
    """Add a note to an existing incident."""
    try:
        note = add_incident_note(
            db=db,
            incident_id=incident_id,
            text=payload.text,
            user_id=user.id
        )
        return IncidentNoteResponse(by=note.by, ts=note.ts, text=note.text)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# Alerts Endpoints
@alerts_router.get("", response_model=List[AlertResponse])
async def list_alerts(
    user: AuthenticatedUser = Depends(require("alert.view")),
    db: Session = Depends(get_db)
):
    """List operational alerts."""
    alerts = db.execute(select(Alert).order_by(Alert.ts.desc())).scalars().all()
    return [
        AlertResponse(
            id=a.id,
            type=a.type,
            sev=a.sev,
            jid=a.jid,
            msg=a.msg,
            ts=a.ts,
            ack=a.ack_by
        )
        for a in alerts
    ]


@alerts_router.post("/{alert_id}/ack", response_model=AlertResponse)
async def acknowledge(
    alert_id: str,
    user: AuthenticatedUser = Depends(require("alert.view")),
    db: Session = Depends(get_db)
):
    """Acknowledge an operational alert."""
    try:
        a = ack_alert(db, alert_id, user.id)
        return AlertResponse(
            id=a.id,
            type=a.type,
            sev=a.sev,
            jid=a.jid,
            msg=a.msg,
            ts=a.ts,
            ack=a.ack_by
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
