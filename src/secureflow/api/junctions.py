"""SecureFlow Junctions & Real-Time Events API Routers."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.core.rbac import AuthenticatedUser, require
from secureflow.events.broker import broker
from secureflow.models import Junction
from secureflow.repositories.database import get_db
from secureflow.schemas import JunctionResponse, SignalTimingPlan

junctions_router = APIRouter(prefix="/api/junctions", tags=["junctions"])
events_router = APIRouter(prefix="/api/events", tags=["events"])


@junctions_router.get("", response_model=List[JunctionResponse])
async def list_junctions(
    user: AuthenticatedUser = Depends(require("dashboard.view")),
    db: Session = Depends(get_db)
):
    """Retrieve list of all 9 city junctions and current signal/congestion states."""
    junctions = db.execute(select(Junction).order_by(Junction.id.asc())).scalars().all()
    results = []
    for j in junctions:
        results.append(JunctionResponse(
            id=j.id,
            name=j.name,
            x=j.x,
            y=j.y,
            base=j.base,
            occ=j.occ,
            speed=j.speed,
            count=j.count,
            level=j.level,
            mode=j.mode,
            plan=SignalTimingPlan(ns=j.plan_ns, ew=j.plan_ew, yellow=j.plan_yellow, allred=j.plan_allred),
            pi=j.pi,
            rem=j.rem,
            corridor=j.corridor_id
        ))
    return results


@junctions_router.get("/{junction_id}", response_model=JunctionResponse)
async def get_junction(
    junction_id: str,
    user: AuthenticatedUser = Depends(require("dashboard.view")),
    db: Session = Depends(get_db)
):
    """Retrieve detailed state of a single junction."""
    j = db.get(Junction, junction_id)
    if not j:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Junction not found.")

    return JunctionResponse(
        id=j.id,
        name=j.name,
        x=j.x,
        y=j.y,
        base=j.base,
        occ=j.occ,
        speed=j.speed,
        count=j.count,
        level=j.level,
        mode=j.mode,
        plan=SignalTimingPlan(ns=j.plan_ns, ew=j.plan_ew, yellow=j.plan_yellow, allred=j.plan_allred),
        pi=j.pi,
        rem=j.rem,
        corridor=j.corridor_id
    )


@events_router.get("")
async def stream_live_events(
    user: AuthenticatedUser = Depends(require("dashboard.view"))
):
    """Server-Sent Events (SSE) live event stream for real-time dashboard updates."""
    return StreamingResponse(
        broker.subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
