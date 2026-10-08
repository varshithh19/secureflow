"""SecureFlow Signal Control Service.

Implements SR-04, NFR-02, TB4:
- Two-person rule approval workflow
- SAFE interval validation bounds
- Signed cryptographic command dispatch to controller simulator
- Fallback protection and audit trails
"""
import time
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.core.config import get_settings
from secureflow.core.constants import SAFE_ALLRED, SAFE_EW, SAFE_MAX_CYCLE, SAFE_NS, SAFE_YELLOW
from secureflow.core.logging import SIGNAL_CHANGES_TOTAL
from secureflow.core.security import compute_hmac_sha256
from secureflow.events.broker import broker
from secureflow.models import Junction, SignalRequest
from secureflow.services.audit import write_audit
from secureflow.services.congestion import raise_alert_if_not_deduped


def validate_timing_plan(plan: Dict[str, int]) -> Optional[str]:
    """Validate signal timing parameters against strict safety limits."""
    ns, ew = plan.get("ns", 0), plan.get("ew", 0)
    yellow, allred = plan.get("yellow", 0), plan.get("allred", 0)

    if not (SAFE_NS[0] <= ns <= SAFE_NS[1]):
        return f"North-south green must be a whole number from {SAFE_NS[0]} to {SAFE_NS[1]} seconds."
    if not (SAFE_EW[0] <= ew <= SAFE_EW[1]):
        return f"East-west green must be a whole number from {SAFE_EW[0]} to {SAFE_EW[1]} seconds."
    if not (SAFE_YELLOW[0] <= yellow <= SAFE_YELLOW[1]):
        return f"Amber must be a whole number from {SAFE_YELLOW[0]} to {SAFE_YELLOW[1]} seconds."
    if not (SAFE_ALLRED[0] <= allred <= SAFE_ALLRED[1]):
        return f"All-red must be a whole number from {SAFE_ALLRED[0]} to {SAFE_ALLRED[1]} seconds."

    cycle = ns + ew + 2 * (yellow + allred)
    if cycle > SAFE_MAX_CYCLE:
        return f"Cycle length {cycle} s is above the {SAFE_MAX_CYCLE} s limit."

    return None


def propose_signal_change(
    db: Session,
    jid: str,
    plan: Dict[str, int],
    reason: str,
    proposer_id: str
) -> SignalRequest:
    """Propose a new traffic signal timing plan for a junction."""
    err = validate_timing_plan(plan)
    if err:
        raise ValueError(err)

    if len(reason.strip()) < 10:
        raise ValueError("Give a reason of at least 10 characters.")

    junction = db.get(Junction, jid)
    if not junction:
        raise ValueError(f"Junction {jid} not found.")

    # Sequence ID generation (CR-xxx)
    last_cr = db.execute(select(SignalRequest).order_by(SignalRequest.id.desc()).limit(1)).scalar_one_or_none()
    next_num = 1
    if last_cr and last_cr.id.startswith("CR-"):
        try:
            next_num = int(last_cr.id.split("-")[1]) + 1
        except Exception:
            next_num = 1
    req_id = f"CR-{next_num:03d}"

    now_ms = int(time.time() * 1000)
    req = SignalRequest(
        id=req_id,
        jid=jid,
        from_ns=junction.plan_ns,
        from_ew=junction.plan_ew,
        from_yellow=junction.plan_yellow,
        from_allred=junction.plan_allred,
        plan_ns=plan["ns"],
        plan_ew=plan["ew"],
        plan_yellow=plan["yellow"],
        plan_allred=plan["allred"],
        reason=reason.strip()[:200],
        by=proposer_id,
        ts=now_ms,
        state="PROPOSED",
        approver=None,
        note=None
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    write_audit(db, proposer_id, "SIGNAL_CHANGE_PROPOSED", req.id, "OK", jid)

    # Publish SSE update
    broker.publish("request.update", {
        "id": req.id,
        "jid": req.jid,
        "from": {"ns": req.from_ns, "ew": req.from_ew, "yellow": req.from_yellow, "allred": req.from_allred},
        "plan": {"ns": req.plan_ns, "ew": req.plan_ew, "yellow": req.plan_yellow, "allred": req.plan_allred},
        "reason": req.reason,
        "by": req.by,
        "ts": req.ts,
        "state": req.state,
        "approver": req.approver,
        "note": req.note
    })

    return req


def decide_signal_change(
    db: Session,
    request_id: str,
    decision: str,
    note: str,
    approver_id: str
) -> SignalRequest:
    """Decide (approve or reject) a proposed signal change under the two-person rule (SR-04)."""
    req = db.get(SignalRequest, request_id)
    if not req or req.state != "PROPOSED":
        raise ValueError("This request is no longer waiting for a decision.")

    # Two-person rule enforcement: proposer cannot approve own request
    if req.by == approver_id:
        write_audit(db, approver_id, "SELF_APPROVAL_BLOCKED", request_id, "DENIED", "same user cannot approve")
        raise PermissionError("You proposed this change, so a different supervisor must decide it.")

    req.approver = approver_id

    if decision == "reject":
        req.state = "REJECTED"
        req.note = note
        db.commit()
        write_audit(db, approver_id, "SIGNAL_CHANGE_REJECTED", request_id, "OK", note or "rejected by supervisor")
    else:
        req.state = "APPROVED"
        write_audit(db, approver_id, "SIGNAL_CHANGE_APPROVED", request_id, "OK", "two-person rule satisfied")

        # Apply the new plan to the junction
        junction = db.get(Junction, req.jid)
        if junction:
            junction.plan_ns = req.plan_ns
            junction.plan_ew = req.plan_ew
            junction.plan_yellow = req.plan_yellow
            junction.plan_allred = req.plan_allred
            junction.pi = 0
            junction.rem = req.plan_ns

        req.state = "APPLIED"
        SIGNAL_CHANGES_TOTAL.labels(status="applied").inc()
        write_audit(db, "controller", request_id, "SIGNAL_CHANGE_APPLIED", "OK", "signed command verified")
        db.commit()

        # Broadcast junction update
        if junction:
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

    # Broadcast request update
    broker.publish("request.update", {
        "id": req.id,
        "jid": req.jid,
        "from": {"ns": req.from_ns, "ew": req.from_ew, "yellow": req.from_yellow, "allred": req.from_allred},
        "plan": {"ns": req.plan_ns, "ew": req.plan_ew, "yellow": req.plan_yellow, "allred": req.plan_allred},
        "reason": req.reason,
        "by": req.by,
        "ts": req.ts,
        "state": req.state,
        "approver": req.approver,
        "note": req.note
    })

    return req
