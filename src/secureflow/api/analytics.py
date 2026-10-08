"""SecureFlow Analytics API Router.

Fixes VUL-05: Removes raw SQL string concatenation; enforces parameterized ORM queries
and parameter whitelisting (SR-09 / THR-08 / THR-12).
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from secureflow.core.rbac import AuthenticatedUser, require
from secureflow.repositories.database import get_db
from secureflow.schemas import AnalyticsResponse
from secureflow.services.analytics import generate_neutralized_csv, get_traffic_analytics

analytics_router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@analytics_router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    junction: Optional[str] = Query(default="all"),
    range: Optional[str] = Query(default="24h"),
    user: AuthenticatedUser = Depends(require("analytics.view")),
    db: Session = Depends(get_db)
):
    """Retrieve aggregate historical traffic analytics."""
    try:
        data = get_traffic_analytics(db=db, junction_id=junction, time_range=range)
        return AnalyticsResponse.model_validate(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e


@analytics_router.get("/export.csv")
async def export_csv(
    junction: Optional[str] = Query(default="all"),
    range: Optional[str] = Query(default="24h"),
    user: AuthenticatedUser = Depends(require("analytics.view")),
    db: Session = Depends(get_db)
):
    """Export historical traffic analysis as sanitized CSV."""
    try:
        data = get_traffic_analytics(db=db, junction_id=junction, time_range=range)
        csv_content = generate_neutralized_csv(
            data=data,
            actor=user.id,
            db=db,
            jid=junction or "all",
            trange=range or "24h"
        )
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=traffic-analysis.csv"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
