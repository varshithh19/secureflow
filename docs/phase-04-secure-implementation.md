# Phase 4: Secure Implementation & Code Review

**Course**: 24CYS401 - Secure Software Engineering  
**System**: SecureFlow - Smart City Traffic Management System  
**Canonical Reference**: `docs/00-canonical-facts.md`

---

## 1. Secure Coding Standards Applied

1. **Deny-by-Default Authorization**:
   - Every API router explicitly declares security dependencies via `Depends(require_permission("..."))`. No endpoint defaults to open access.
2. **Defensive Input Validation**:
   - All external inputs are validated through Pydantic v2 schemas (`src/secureflow/schemas/`) with strict bounds checking, regex validation on IDs, and enum validation on state machines.
3. **Prepared Statements & ORM Safety**:
   - All database queries use SQLAlchemy 2.0 select abstractions or parameterized bindings. No dynamic SQL string interpolation exists in the production codebase.
4. **Formula Injection Neutralization**:
   - Analytics CSV exports escape special spreadsheet execution triggers (`=`, `+`, `-`, `@`) by prepending a single quote (`'`).
5. **Strict Content Security Policy (CSP)**:
   - Zero inline scripts and zero inline styles in HTML views.
   - Header enforced: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none';`.
6. **Output Encoding & Sanitization**:
   - Dynamic UI properties pass through the `esc()` sanitization helper in `static/js/ui.js` before DOM insertion.

---

## 2. OWASP Top 10 (2021) Mapping & Defense Implementation

| OWASP Category | Vulnerability Risk in Traffic Systems | SecureFlow Implementation & Defensive Control | Code Reference |
|:---|:---|:---|:---|
| **A01: Broken Access Control** | Unauthorized signal modification, bypass of two-person rule, self-role escalation. | Server-side RBAC dependency (`require_permission`), explicit proposer vs approver identity check (`proposer_id != user.id`), cannot change own role in user admin endpoint. | `src/secureflow/core/rbac.py`<br>`src/secureflow/services/signals.py`<br>`src/secureflow/api/users.py` |
| **A02: Cryptographic Failures** | Weak password hashes, plaintext tokens, exposed device keys. | Argon2id for password storage, HMAC-SHA256 device telemetry authentication, PyJWT HS256 tokens with short 15m expiration, encrypted/hashed secrets in database. | `src/secureflow/core/security.py`<br>`src/secureflow/services/telemetry.py` |
| **A03: Injection** | SQL injection in analytics filters, CSV formula execution, command injection. | SQLAlchemy 2.0 ORM parameterized queries, sanitization filter prefixing formulas with `'`, regex validation on identifiers (`^[A-Z0-9_-]+$`). | `src/secureflow/services/analytics.py`<br>`src/secureflow/schemas/__init__.py` |
| **A04: Insecure Design** | Unbounded signal timing causing traffic collisions, lack of replay defense. | Strict `SAFE` timing boundary enforcement ($G \in [10, 120]$, $A \in [3, 5]$, $R \in [1, 5]$), 60s TTL nonce cache with $\pm 30\text{s}$ freshness window. | `src/secureflow/core/constants.py`<br>`src/secureflow/services/telemetry.py` |
| **A05: Security Misconfiguration** | Missing security headers, verbose stack traces in production, open CORS. | `SecurityHeadersMiddleware` with strict CSP, HSTS, X-Content-Type-Options; same-origin static file serving eliminating CORS risks; generic JSON error format `{ "detail": "..." }`. | `src/secureflow/core/middleware.py`<br>`src/secureflow/main.py` |
| **A06: Vulnerable & Outdated Components** | Vulnerabilities in third-party libraries and vendor scripts. | Pinned dependency versions in `requirements.txt`, Dependabot scanning (`.github/dependabot.yml`), self-hosted vendor assets (Chart.js, fonts). | `static/vendor/`<br>`.github/dependabot.yml` |
| **A07: Identification & Auth Failures** | Credential brute-forcing, missing MFA for privileged roles, token theft. | 5-attempt account lockout, TOTP MFA required for `supervisor` and `admin`, memory-only access tokens, HttpOnly/SameSite=Strict refresh cookies. | `src/secureflow/services/auth.py`<br>`src/secureflow/core/security.py` |
| **A08: Software & Data Integrity Failures** | Tampering with audit trail, unverified sensor telemetry. | SHA-256 hash-chained append-only audit log with sequential verify endpoint, HMAC signature verification for IoT sensor data and controller commands. | `src/secureflow/services/audit.py`<br>`src/secureflow/services/telemetry.py` |
| **A09: Security Logging & Monitoring Failures** | Silent security events, unmonitored attack simulations. | Structured JSON logging with correlation `request_id`, Prometheus metrics counters for failed auth, invalid signatures, replay attacks, and rate limits. | `src/secureflow/core/logging.py`<br>`src/secureflow/services/security_sim.py` |
| **A10: Server-Side Request Forgery (SSRF)** | Internal controller dispatch exploitation. | Controllers bound to whitelisted internal loopback and simulated endpoint targets; no user-supplied outbound URLs accepted. | `src/secureflow/services/signals.py` |

---

## 3. Code Review & Defect Log Summary

As logged in `docs/defects.md`, all identified static and dynamic defects were remediated prior to milestone sign-off:

1. **DEF-01 (High)**: Broad exception handling in Prometheus metric parsing -> Refactored to explicit tuple `(KeyError, AttributeError, ValueError)`.
2. **DEF-02 (Medium)**: Insecure `0.0.0.0` default host in development script -> Replaced with safe `127.0.0.1` binding.
3. **DEF-03 (High)**: URL parameter encoding issue during Hypothesis fuzzing -> Updated client harness to use structured query dictionary `params={...}` to ensure RFC 3986 compliance while validating server rejection.
4. **DEF-04 (Critical)**: Two-Person Rule edge case allowing same user to approve if role switched -> Added immutable `proposer_id` check against current user ID in database transaction.
