"""[VULNERABLE VERSION - v0-insecure]

VUL-06: Verbose exception stack-trace error responses leaked to client.
"""
import traceback
from typing import Callable
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersAndTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            # VUL-06: Leaking detailed internal traceback to client
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "internal_state": "DEBUG_LEAK"
                }
            )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # VUL-06: Leaking full traceback on unhandled exceptions
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": str(exc),
                "traceback": traceback.format_exc()
            }
        )
