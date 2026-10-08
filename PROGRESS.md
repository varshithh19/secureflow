# SecureFlow DevSecOps Progress Checklist

## 1. Project Initialization & Architecture Setup
- [x] Initialized Git repository and configured local directory structure
- [x] Created Canonical Facts documentation (`docs/00-canonical-facts.md`)
- [x] Set up Python dependency specification (`pyproject.toml`, `requirements.txt`)
- [x] Created configuration management and `.env.example`

## 2. Frontend Modularization & Hardening
- [ ] Vendor assets self-hosted under `static/vendor/` (Barlow fonts, Chart.js)
- [ ] CSS extracted into `static/css/app.css` and all inline styles removed
- [ ] Modular JS created under `static/js/`:
  - `api.js` (Fetch with token refresh, CSRF headers, error normalization)
  - `state.js` (In-memory token, active route, selection)
  - `rbac.js` (Client-side permission table matching server)
  - `ui.js` (Rendering helpers, escaping, toasts, modals)
  - `views/*.js` (Dashboard, Signals, Emergency, Incidents, Alerts, Analytics, Sensors, Users, Audit, Security, Login)
  - `events.js` (Server-Sent Events connection and live dispatch)
  - `main.js` (App initialization, routing, session timer)
- [ ] `static/index.html` configured without inline scripts or inline styles for strict CSP
- [ ] Client-side XSS escaping verification test

## 3. Backend Implementation (FastAPI & SQLAlchemy)
- [ ] Core Modules:
  - Configuration (`src/secureflow/core/config.py`)
  - Security & Crypto (`src/secureflow/core/security.py`: Argon2, PyJWT 15m/8h rotation, pyotp TOTP)
  - Central RBAC Dependency (`src/secureflow/core/rbac.py`: deny-by-default permission check)
  - Rate Limiting (`src/secureflow/core/rate_limit.py`)
  - Middleware (`src/secureflow/core/middleware.py`: Request ID, JSON structured logging, Security Headers with strict CSP, CSRF protection)
- [ ] Database Models & Schemas:
  - SQLAlchemy 2 Models (`src/secureflow/models/`)
  - Pydantic v2 Validation Schemas (`src/secureflow/schemas/`)
  - Database Session & Engine (`src/secureflow/repositories/database.py`)
- [ ] Business Services:
  - Telemetry Service (HMAC-SHA256 signature check, 30s timestamp window, nonce replay cache, plausibility check)
  - Congestion Detection Strategy (Thresholds <35%, <60%, <80%, >=80%, Critical alert trigger with 5m dedup)
  - Signal Control Service (PROPOSED/APPROVED/APPLIED/REJECTED/EXPIRED, two-person rule, safe ranges)
  - Emergency Corridor Service (BFS graph routing, max 3 reqs/10m rate limit, auto-expiry)
  - Incident & Alert Management (Supervisor-only close, alert ack, notes)
  - Analytics Service (Parameterized SQL aggregations, formula injection neutralizer)
  - Tamper-Evident Audit Service (SHA-256 hash chaining, verification endpoint)
  - Security Simulation Service (THR-01 to THR-12 defense exercises)
  - SSE Event Broker (`src/secureflow/events/broker.py`)
- [ ] API Routers:
  - Auth, Me, Junctions, Events (SSE), Signals, Emergency, Incidents, Alerts, Sensors, Users, Audit, Analytics, Security, Telemetry, Healthz/Readyz/Metrics
- [ ] Seed Data Script (`scripts/seed.py`)

## 4. Phase 12 Requirement (Before/After Git History)
- [ ] Commit weak implementation tagged `v0-insecure` with:
  - VUL-01 (Hardcoded secret key)
  - VUL-03 (Signal change endpoint missing role check)
  - VUL-05 (SQL built with string concatenation in analytics filter)
  - VUL-06 (Verbose stack-trace error leakage)
- [ ] Commit secured implementation tagged `v1-secure`
- [ ] Document before-after analysis (`docs/phase-12/before-after.md`)

## 5. Simulators
- [ ] `simulator/sensor_sim.py` (HMAC-signed telemetry, rush hour simulation, attack flags `--spoof`, `--replay`, `--implausible`, `--flood`)
- [ ] `simulator/controller_sim.py` (Signed command verification, 6-phase cycling, default fallback)
- [ ] `simulator/emergency_sim.py` (Automated authenticated priority requests)

## 6. Comprehensive Testing Suite
- [ ] Unit Tests (crypto, nonces, RBAC, congestion strategy, plausibility, audit chain, signal validation, XSS escaping)
- [ ] Integration Tests (sensor registration -> signed telemetry -> congestion alert -> dashboard)
- [ ] System / E2E Tests (propose -> approve -> signed apply -> audit chain verify; self-approval prevention)
- [ ] Fuzz Tests (Hypothesis fuzzing on `/api/telemetry` and `/api/analytics` filters)
- [ ] Security Tests (Auth matrix for all endpoints/roles, rate limit, SQLi, JWT tampering)
- [ ] Coverage >= 80% achieved and reports generated in `evidence/`

## 7. Containers & Kubernetes
- [ ] Hardened multi-stage Dockerfile (`docker/Dockerfile`)
- [ ] `docker-compose.yml` (App, PostgreSQL, Simulators)
- [ ] Hardened Kubernetes manifests (`k8s/`):
  - Namespace, ConfigMap, Secret example
  - PostgreSQL Deployment & Service
  - App Deployment (readOnlyRootFilesystem, non-root, drop capabilities, seccomp RuntimeDefault, resource limits, probes)
  - Service, Ingress, NetworkPolicy, HPA
- [ ] Minikube deployment script (`scripts/minikube_deploy.sh`)

## 8. CI/CD & Monitoring Hardening
- [ ] GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- [ ] Dependabot configuration (`.github/dependabot.yml`)
- [ ] PR Template & CODEOWNERS
- [ ] Prometheus Alert Rules (`monitoring/alerts.yml`) & Grafana Dashboard (`monitoring/grafana-dashboard.json`)
- [ ] Security Documentation:
  - `docs/phase-11/branch-protection.md`
  - `docs/phase-15/logging-plan.md`
  - `docs/phase-15/hardening-checklist.md`
  - `docs/phase-15/physical-operational-controls.md`
  - `docs/phase-15/deployment-checklist.md`
  - `docs/defects.md`
  - `evidence/fuzz-report.md`
  - `Makefile` and `README.md`
