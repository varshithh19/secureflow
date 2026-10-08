"""SecureFlow Security Metrics & Threat Simulation API Router."""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from secureflow.core.logging import (
    EMERGENCY_REQUESTS_TOTAL,
    FAILED_LOGINS_TOTAL,
    INVALID_SIGNATURES_TOTAL,
    RATE_LIMIT_HITS_TOTAL,
    REPLAY_ATTEMPTS_TOTAL,
    SIGNAL_CHANGES_TOTAL,
    SUSPICIOUS_TELEMETRY_TOTAL,
)
from secureflow.core.rbac import AuthenticatedUser, require
from secureflow.repositories.database import get_db
from secureflow.services.security_sim import run_threat_simulation

security_router = APIRouter(prefix="/api/security", tags=["security"])


@security_router.get("/metrics")
async def get_metrics(
    user: AuthenticatedUser = Depends(require("security.view"))
) -> Dict[str, int]:
    """Retrieve security defense metrics from Prometheus counters."""
    applied_signals = 0
    try:
        applied_signals = int(SIGNAL_CHANGES_TOTAL.labels(status="applied")._value.get())
    except Exception:
        pass

    return {
        "invalid_signatures": int(INVALID_SIGNATURES_TOTAL._value.get()),
        "replay_attempts": int(REPLAY_ATTEMPTS_TOTAL._value.get()),
        "rate_limit_hits": int(RATE_LIMIT_HITS_TOTAL._value.get()),
        "failed_logins": int(FAILED_LOGINS_TOTAL._value.get()),
        "suspicious_telemetry": int(SUSPICIOUS_TELEMETRY_TOTAL._value.get()),
        "signal_changes": applied_signals,
        "emergency_requests": int(EMERGENCY_REQUESTS_TOTAL._value.get())
    }


@security_router.post("/simulate/{threat_id}")
async def simulate_threat(
    threat_id: str,
    user: AuthenticatedUser = Depends(require("security.simulate")),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Run an attack simulation against real defensive code paths (THR-01 to THR-12)."""
    try:
        result = run_threat_simulation(db=db, threat_id=threat_id, actor=user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
