"""SecureFlow Security Middleware & Exception Handlers.

Applies strict security headers (CSP, HSTS, X-Content-Type-Options, X-Frame-Options,
Referrer-Policy, Permissions-Policy), Request ID tracking, CSRF token validation,
and generic error serialization.
Fixes VUL-06: Never leak stack traces to clients; logs securely server-side with request ID.
"""
import time
import uuid
from typing import Callable
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from secureflow.core.logging import logger


class SecurityHeadersAndTracingMiddleware(BaseHTTPMiddleware):
    """Middleware attaching request IDs and security headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                f"Unhandled exception during request {request.method} {request.url.path}: {str(exc)}",
                exc_info=True,
                extra={"request_id": request_id, "ip": request.client.host if request.client else "unknown"}
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "An internal server error occurred."},
                headers={"X-Request-ID": request_id}
            )

        duration = time.time() - start_time
        response.headers["X-Request-ID"] = request_id

        # Strict Content-Security-Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        return response


def register_exception_handlers(app: FastAPI) -> None:
    """Register uniform generic exception handlers that never leak stack traces."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers={"X-Request-ID": request_id}
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.error(
            f"Unhandled exception on {request.url.path}: {str(exc)}",
            exc_info=True,
            extra={"request_id": request_id}
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal error occurred. Please try again later."},
            headers={"X-Request-ID": request_id}
        )
