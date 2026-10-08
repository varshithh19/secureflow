"""SecureFlow FastAPI Application Entry Point.

Serves the frontend static files and secure backend API from the same origin.
"""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from secureflow.api.auth import auth_router, me_router
from secureflow.api.junctions import events_router, junctions_router
from secureflow.api.signals import signals_router
from secureflow.api.emergency import alerts_router, emergency_router, incidents_router
from secureflow.api.sensors import admin_sensors_router, sensors_router
from secureflow.api.users import audit_router, users_router
from secureflow.api.analytics import analytics_router
from secureflow.api.security import security_router
from secureflow.api.telemetry import ops_router, telemetry_router
from secureflow.core.config import get_settings
from secureflow.core.middleware import (
    SecurityHeadersAndTracingMiddleware,
    register_exception_handlers,
)
from secureflow.core.rate_limit import limiter
from secureflow.repositories.database import SessionLocal, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for database initialization and seeding."""
    init_db()
    # Auto-seed database if empty
    try:
        from scripts.seed import seed_database
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()
    except Exception as e:
        print(f"Database seed note: {e}")
    yield


def create_app() -> FastAPI:
    """Application factory for SecureFlow."""
    settings = get_settings()

    app = FastAPI(
        title="SecureFlow",
        description="Smart City Traffic Management System API (24CYS401 Lab)",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG or settings.DEMO_MODE else None,
        redoc_url=None
    )

    # Attach Rate Limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Attach Security Headers & Request Tracing Middleware
    app.add_middleware(SecurityHeadersAndTracingMiddleware)

    # Register Generic Exception Handlers
    register_exception_handlers(app)

    # Include API Routers
    app.include_router(auth_router)
    app.include_router(me_router)
    app.include_router(junctions_router)
    app.include_router(events_router)
    app.include_router(signals_router)
    app.include_router(emergency_router)
    app.include_router(incidents_router)
    app.include_router(alerts_router)
    app.include_router(sensors_router)
    app.include_router(admin_sensors_router)
    app.include_router(users_router)
    app.include_router(audit_router)
    app.include_router(analytics_router)
    app.include_router(security_router)
    app.include_router(telemetry_router)
    app.include_router(ops_router)

    # Mount Static Files
    static_dir = Path(__file__).resolve().parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(str(static_dir / "index.html"))

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("secureflow.main:app", host="0.0.0.0", port=8000, reload=True)
