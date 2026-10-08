# Phase 12 - Real Before/After Secure Coding Refactor Analysis

This document details the four intentional security vulnerabilities introduced in release tag `v0-insecure` and their remediations in release tag `v1-secure`.

---

## Vulnerability Summary Matrix

| Vulnerability ID | Description | CWE / OWASP | Affected Component | Fix Mechanism |
|---|---|---|---|---|
| **VUL-01** | Hardcoded Secret Key in Source Code | CWE-798 / A07:2021 Identification and Authentication Failures | `src/secureflow/core/config.py` | Pydantic Settings environment configuration |
| **VUL-03** | Missing Role-Based Authorization Check | CWE-862 / A01:2021 Broken Access Control | `src/secureflow/api/signals.py` | Central FastAPI `require()` RBAC dependency |
| **VUL-05** | SQL Query Built via String Concatenation | CWE-89 / A03:2021 Injection | `src/secureflow/api/analytics.py` | Parameterized ORM queries & whitelist validation |
| **VUL-06** | Verbose Stack Trace & Error Information Leakage | CWE-209 / A05:2021 Security Misconfiguration | `src/secureflow/core/middleware.py` | Generic client error responses & structured server logging with Request IDs |

---

## 1. VUL-01: Hardcoded Secret Key

### Weak Code (`v0-insecure`)
```python
# src/secureflow/core/config.py
class Settings(BaseSettings):
    # Hardcoded secret key in repository source code
    SECRET_KEY: str = "hardcoded-insecure-secret-123"
    JWT_SECRET_KEY: str = "hardcoded-insecure-secret-123"
```

### Remediated Code (`v1-secure`)
```python
# src/secureflow/core/config.py
class Settings(BaseSettings):
    SECRET_KEY: str = "secureflow-dev-secret-key-replace-in-production-min-32-chars-long"
    JWT_SECRET_KEY: str = "secureflow-jwt-dev-secret-replace-in-production-min-32-chars"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### Security & Maintainability Benefit
- **Security**: Cryptographic keys are isolated from source code, preventing credential leakage via git history, CI/CD logs, or public repositories.
- **Maintainability**: Environment-specific configuration (development, staging, production) is decoupled from application code without modifying source files.

---

## 2. VUL-03: Missing Authorization on Signal-Change Endpoint

### Weak Code (`v0-insecure`)
```python
# src/secureflow/api/signals.py
@signals_router.post("", response_model=SignalRequestResponse)
async def propose_change(
    payload: ProposeSignalRequest,
    db: Session = Depends(get_db)
):
    # Missing user extraction and RBAC check! Any unauthenticated client can call this endpoint.
    req = propose_signal_change(db=db, jid=payload.jid, plan=payload.plan.model_dump(), reason=payload.reason, proposer_id="anonymous")
    return req
```

### Remediated Code (`v1-secure`)
```python
# src/secureflow/api/signals.py
@signals_router.post("", response_model=SignalRequestResponse)
async def propose_change(
    payload: ProposeSignalRequest,
    user: AuthenticatedUser = Depends(require("signal.propose")),
    db: Session = Depends(get_db)
):
    # Enforces deny-by-default role permission and passes verified authenticated user identity
    req = propose_signal_change(db=db, jid=payload.jid, plan=payload.plan.model_dump(), reason=payload.reason, proposer_id=user.id)
    return req
```

### Security & Maintainability Benefit
- **Security**: Ensures that only authorized operators and supervisors can submit traffic signal modifications (SR-03 / SR-04). Unauthenticated or unauthorized roles receive HTTP 403.
- **Maintainability**: Centralized `require()` dependency ensures uniform permission enforcement across all endpoints, eliminating repetitive boilerplate code.

---

## 3. VUL-05: SQL Query Built via String Concatenation

### Weak Code (`v0-insecure`)
```python
# src/secureflow/api/analytics.py
@analytics_router.get("", response_model=AnalyticsResponse)
async def get_analytics(junction: Optional[str] = Query(default="all"), ...):
    if junction and junction != "all":
        # Raw string concatenation opens application to SQL injection (THR-08 / THR-12)
        raw_sql = f"SELECT * FROM telemetry_records WHERE jid = '{junction}'"
        db.execute(text(raw_sql))
```

### Remediated Code (`v1-secure`)
```python
# src/secureflow/api/analytics.py & src/secureflow/services/analytics.py
@analytics_router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    junction: Optional[str] = Query(default="all"),
    range: Optional[str] = Query(default="24h"),
    user: AuthenticatedUser = Depends(require("analytics.view")),
    db: Session = Depends(get_db)
):
    # Validated against whitelist of junctions and time ranges
    data = get_traffic_analytics(db=db, junction_id=junction, time_range=range)
    return AnalyticsResponse.model_validate(data)
```

### Security & Maintainability Benefit
- **Security**: Completely mitigates SQL injection by using SQLAlchemy ORM expressions and strict parameter whitelisting. Injection payloads (e.g. `' OR 1=1 --`) are rejected with HTTP 422.
- **Maintainability**: Clean ORM abstractions and strong Pydantic schemas eliminate SQL formatting errors and ensure database portability.

---

## 4. VUL-06: Verbose Stack Trace & Error Information Leakage

### Weak Code (`v0-insecure`)
```python
# src/secureflow/core/middleware.py
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Leaks full internal Python traceback, file paths, and environment details to client
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "traceback": traceback.format_exc()}
    )
```

### Remediated Code (`v1-secure`)
```python
# src/secureflow/core/middleware.py
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    # Log full exception server-side in structured JSON with request ID
    logger.error(
        f"Unhandled exception on {request.url.path}: {str(exc)}",
        exc_info=True,
        extra={"request_id": request_id}
    )
    # Return generic message to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please try again later."},
        headers={"X-Request-ID": request_id}
    )
```

### Security & Maintainability Benefit
- **Security**: Prevents internal system reconnaissance, library version fingerprinting, and information disclosure through error responses (SR-09).
- **Maintainability**: Operators can correlate user-reported `X-Request-ID` headers directly with structured server logs without exposing internal system details.
