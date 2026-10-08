"""SecureFlow IoT Telemetry Ingestion & Operations Routers."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session

from secureflow.core.rate_limit import limiter
from secureflow.repositories.database import get_db
from secureflow.schemas import TelemetryIngestPayload
from secureflow.services.congestion import update_junction_congestion
from secureflow.services.telemetry import validate_and_ingest_telemetry

telemetry_router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])
ops_router = APIRouter(tags=["ops"])


@telemetry_router.post("")
@telemetry_router.post("/")
@limiter.limit("120/minute")
async def ingest_telemetry(
    request: Request,
    payload: TelemetryIngestPayload,
    db: Session = Depends(get_db)
):
    """Ingest live IoT traffic telemetry with HMAC signature validation (TB1 / SR-01 / SR-02)."""
    # Standard simulator shared key in lab mode: b"simulator-sensor-secret-key-32bytes"
    device_secret_bytes = b"simulator-sensor-secret-key-32bytes"

    accepted, err, record = validate_and_ingest_telemetry(
        db=db,
        sensor_id=payload.sensor_id,
        junction_id=payload.junction_id,
        vehicle_count=payload.vehicle_count,
        avg_speed=payload.avg_speed,
        occupancy=payload.occupancy,
        timestamp=payload.timestamp,
        nonce=payload.nonce,
        signature=payload.signature,
        device_secret_bytes=device_secret_bytes
    )

    if not accepted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=err or "Telemetry rejected.")

    # Update real-time junction congestion
    update_junction_congestion(db, payload.junction_id)

    return {
        "status": "accepted",
        "flagged": record.is_flagged if record else False,
        "detail": record.flag_reason if (record and record.is_flagged) else "Telemetry accepted."
    }


# Health and Metrics Operations Endpoints
@ops_router.get("/healthz")
async def liveness_probe():
    """Kubernetes liveness probe."""
    return {"status": "healthy"}


@ops_router.get("/readyz")
async def readiness_probe(db: Session = Depends(get_db)):
    """Kubernetes readiness probe checking database availability."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable."
        ) from e


@ops_router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
