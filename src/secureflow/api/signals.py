"""[VULNERABLE VERSION - v0-insecure]

VUL-03: Signal change endpoint missing RBAC check (unauthorized users can propose/approve).
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.models import SignalRequest
from secureflow.repositories.database import get_db
from secureflow.schemas import (
    DecideSignalRequest,
    ProposeSignalRequest,
    SignalRequestResponse,
    SignalTimingPlan,
)
from secureflow.services.signals import decide_signal_change, propose_signal_change

signals_router = APIRouter(prefix="/api/signal-requests", tags=["signals"])


@signals_router.get("", response_model=List[SignalRequestResponse])
async def list_signal_requests(db: Session = Depends(get_db)):
    # VUL-03: Missing RBAC permission dependency
    requests = db.execute(select(SignalRequest).order_by(SignalRequest.ts.desc())).scalars().all()
    results = []
    for r in requests:
        results.append(SignalRequestResponse(
            id=r.id,
            jid=r.jid,
            from_=SignalTimingPlan(ns=r.from_ns, ew=r.from_ew, yellow=r.from_yellow, allred=r.from_allred),
            plan=SignalTimingPlan(ns=r.plan_ns, ew=r.plan_ew, yellow=r.plan_yellow, allred=r.plan_allred),
            reason=r.reason,
            by=r.by,
            ts=r.ts,
            state=r.state,
            approver=r.approver,
            note=r.note
        ))
    return results


@signals_router.post("", response_model=SignalRequestResponse)
async def propose_change(
    payload: ProposeSignalRequest,
    db: Session = Depends(get_db)
):
    # VUL-03: Missing RBAC permission dependency
    try:
        req = propose_signal_change(
            db=db,
            jid=payload.jid,
            plan=payload.plan.model_dump(),
            reason=payload.reason,
            proposer_id="anonymous"
        )
        return SignalRequestResponse(
            id=req.id,
            jid=req.jid,
            from_=SignalTimingPlan(ns=req.from_ns, ew=req.from_ew, yellow=req.from_yellow, allred=req.from_allred),
            plan=SignalTimingPlan(ns=req.plan_ns, ew=req.plan_ew, yellow=req.plan_yellow, allred=req.plan_allred),
            reason=req.reason,
            by=req.by,
            ts=req.ts,
            state=req.state,
            approver=req.approver,
            note=req.note
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@signals_router.post("/{request_id}/decision", response_model=SignalRequestResponse)
async def decide_request(
    request_id: str,
    payload: DecideSignalRequest,
    db: Session = Depends(get_db)
):
    # VUL-03: Missing RBAC permission dependency
    try:
        req = decide_signal_change(
            db=db,
            request_id=request_id,
            decision=payload.decision,
            note=payload.note or "",
            approver_id="anonymous"
        )
        return SignalRequestResponse(
            id=req.id,
            jid=req.jid,
            from_=SignalTimingPlan(ns=req.from_ns, ew=req.from_ew, yellow=req.from_yellow, allred=req.from_allred),
            plan=SignalTimingPlan(ns=req.plan_ns, ew=req.plan_ew, yellow=req.plan_yellow, allred=req.plan_allred),
            reason=req.reason,
            by=req.by,
            ts=req.ts,
            state=req.state,
            approver=req.approver,
            note=req.note
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
