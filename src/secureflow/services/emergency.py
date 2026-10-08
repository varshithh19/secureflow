"""SecureFlow Emergency Corridor Preemption Service.

Implements FR-05, SR-07, TB5:
- BFS shortest-path corridor routing over road topology
- Conflict detection (no overlapping active green corridors)
- Vehicle preemption rate limiting (max 3 per 10 minutes)
- Automatic timer-based corridor expiration and junction release
"""
import json
import time
from collections import deque
from typing import Dict, List, Optional, Set
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.core.constants import ROAD_EDGES
from secureflow.core.logging import EMERGENCY_REQUESTS_TOTAL, RATE_LIMIT_HITS_TOTAL
from secureflow.events.broker import broker
from secureflow.models import Corridor, Junction
from secureflow.services.audit import write_audit
from secureflow.services.congestion import raise_alert_if_not_deduped


def find_bfs_route(start_jid: str, end_jid: str) -> Optional[List[str]]:
    """Compute the shortest path road route between two junctions using BFS."""
    adj: Dict[str, List[str]] = {}
    for a, b in ROAD_EDGES:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)

    queue: deque = deque([[start_jid]])
    visited: Set[str] = {start_jid}

    while queue:
        path = queue.popleft()
        curr = path[-1]
        if curr == end_jid:
            return path
        for neighbor in adj.get(curr, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return None


def create_emergency_corridor(
    db: Session,
    vehicle: str,
    from_jid: str,
    to_jid: str,
    duration: int,
    reason: str,
    dispatcher_id: str
) -> Corridor:
    """Create and activate an emergency vehicle green wave corridor."""
    if from_jid == to_jid:
        raise ValueError("Choose two different junctions that are connected by road.")

    route = find_bfs_route(from_jid, to_jid)
    if not route:
        raise ValueError("Choose two different junctions that are connected by road.")

    if not (60 <= duration <= 300):
        raise ValueError("Duration must be 60 to 300 seconds.")

    now_ms = int(time.time() * 1000)
    ten_min_ago = now_ms - (10 * 60 * 1000)

    # Vehicle rate limit check: max 3 requests per 10 minutes
    recent_vehicle_requests = db.execute(
        select(Corridor).filter(
            Corridor.vehicle == vehicle,
            Corridor.ts >= ten_min_ago
        )
    ).scalars().all()

    if len(recent_vehicle_requests) >= 3:
        RATE_LIMIT_HITS_TOTAL.inc()
        write_audit(db, dispatcher_id, "RATE_LIMITED", vehicle, "DENIED", "3 requests per 10 min")
        raise ValueError("Too many priority requests for this vehicle. Wait a few minutes or call a supervisor.")

    # Conflict check: ensure no active corridor already occupies any junction in route
    for jid in route:
        j = db.get(Junction, jid)
        if j and j.corridor_id:
            raise ValueError("Part of this route already has an active emergency corridor.")

    # Sequence ID generation (EC-xxx)
    last_ec = db.execute(select(Corridor).order_by(Corridor.id.desc()).limit(1)).scalar_one_or_none()
    next_num = 1
    if last_ec and last_ec.id.startswith("EC-"):
        try:
            next_num = int(last_ec.id.split("-")[1]) + 1
        except Exception:
            next_num = 1
    corridor_id = f"EC-{next_num:03d}"

    expires_ms = now_ms + (duration * 1000)
    corridor = Corridor(
        id=corridor_id,
        vehicle=vehicle,
        from_jid=from_jid,
        to_jid=to_jid,
        route_json=json.dumps(route),
        by=dispatcher_id,
        ts=now_ms,
        expires=expires_ms,
        state="ACTIVE",
        reason=reason
    )
    db.add(corridor)

    # Assign corridor to each junction in route
    for jid in route:
        j = db.get(Junction, jid)
        if j:
            j.corridor_id = corridor.id

    db.commit()
    db.refresh(corridor)

    EMERGENCY_REQUESTS_TOTAL.inc()
    write_audit(db, dispatcher_id, "EMERGENCY_REQUESTED", corridor.id, "OK", f"{vehicle} {from_jid} to {to_jid}")

    from_name = db.get(Junction, from_jid).name if db.get(Junction, from_jid) else from_jid
    to_name = db.get(Junction, to_jid).name if db.get(Junction, to_jid) else to_jid
    raise_alert_if_not_deduped(
        db=db,
        alert_type="EMERGENCY_PRIORITY",
        sev="INFO",
        jid=from_jid,
        msg=f"{vehicle} has a green corridor from {from_name} to {to_name}."
    )

    # Broadcast corridor update
    broker.publish("corridor.update", {
        "id": corridor.id,
        "vehicle": corridor.vehicle,
        "from": corridor.from_jid,
        "to": corridor.to_jid,
        "route": route,
        "by": corridor.by,
        "ts": corridor.ts,
        "expires": corridor.expires,
        "state": corridor.state,
        "reason": corridor.reason
    })

    return corridor


def cancel_emergency_corridor(
    db: Session,
    corridor_id: str,
    user_id: str
) -> Corridor:
    """Cancel an active emergency corridor immediately."""
    corridor = db.get(Corridor, corridor_id)
    if not corridor or corridor.state != "ACTIVE":
        raise ValueError("Corridor is not active.")

    corridor.state = "CANCELLED"
    route = json.loads(corridor.route_json)
    for jid in route:
        j = db.get(Junction, jid)
        if j and j.corridor_id == corridor.id:
            j.corridor_id = None

    db.commit()
    write_audit(db, user_id, "EMERGENCY_CANCELLED", corridor.id, "OK", "cancelled by user")

    broker.publish("corridor.update", {
        "id": corridor.id,
        "vehicle": corridor.vehicle,
        "from": corridor.from_jid,
        "to": corridor.to_jid,
        "route": route,
        "by": corridor.by,
        "ts": corridor.ts,
        "expires": corridor.expires,
        "state": corridor.state,
        "reason": corridor.reason
    })

    return corridor


def expire_corridors_check(db: Session) -> List[Corridor]:
    """Check and automatically expire finished emergency corridors."""
    now_ms = int(time.time() * 1000)
    active_corridors = db.execute(
        select(Corridor).filter(
            Corridor.state == "ACTIVE",
            Corridor.expires <= now_ms
        )
    ).scalars().all()

    for corridor in active_corridors:
        corridor.state = "EXPIRED"
        route = json.loads(corridor.route_json)
        for jid in route:
            j = db.get(Junction, jid)
            if j and j.corridor_id == corridor.id:
                j.corridor_id = None
        write_audit(db, "system", "EMERGENCY_EXPIRED", corridor.id, "OK", "corridor duration ended")

    if active_corridors:
        db.commit()

    return active_corridors
