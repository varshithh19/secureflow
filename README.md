# SecureFlow - Smart City Traffic Management System

**SecureFlow** is a secure, end-to-end Smart City Traffic Operations platform developed for the Secure Software Engineering lab (24CYS401). It pairs an interactive, high-performance vanilla JavaScript frontend with a hardened, asynchronous Python 3.12 / FastAPI backend.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph TB2["TB2: Browser Client"]
        UI["Vanilla JS SPA (ES Modules)<br/>Memory JWT + HttpOnly Cookie"]
    end

    subgraph TB1["TB1: IoT Edge Zone"]
        Sensors["Traffic Sensors (SN-101..112)<br/>HMAC-SHA256 Signed Telemetry"]
    end

    subgraph Backend["FastAPI Secure Gateway (:8000)"]
        Auth["Auth & MFA Service (Argon2 / PyOTP)"]
        RBAC["Deny-by-Default Central RBAC"]
        Telemetry["Telemetry Ingestion & Plausibility"]
        Signals["Signal Service (Two-Person Rule)"]
        Emergency["Emergency Preemption (BFS Routing)"]
        Audit["Tamper-Evident SHA-256 Audit Log"]
        SSE["Server-Sent Events Broker"]
    end

    subgraph TB3["TB3: Data Layer"]
        DB[(PostgreSQL / SQLite Database)]
    end

    subgraph TB4["TB4: Field Controllers"]
        Controllers["Signal Controller Simulator (:8010)<br/>Signed Command Verification"]
    end

    UI -->|HTTPS / API Requests| RBAC
    RBAC --> Auth
    RBAC --> Signals
    RBAC --> Emergency
    RBAC --> Audit
    Sensors -->|Signed POST /api/telemetry| Telemetry
    Telemetry --> DB
    Signals --> DB
    Signals -->|HMAC Signed Plan| Controllers
    Emergency --> DB
    Audit --> DB
    SSE -->|Live Updates (SSE)| UI
```

---

## Features & Security Controls

1. **Strict Content-Security-Policy & Self-Hosted Assets**: Zero `'unsafe-inline'` or `'unsafe-eval'`. All fonts (Barlow) and Chart.js are self-hosted with no external CDN dependencies.
2. **In-Memory JWT & HttpOnly Refresh Cookie**: Short-lived access tokens kept in client memory only; rotation on 401 with CSRF protection (`X-CSRF-Token`).
3. **Two-Person Approval Rule (SR-04)**: Signal modifications proposed by an operator or supervisor can never be approved by the proposer.
4. **Cryptographic Telemetry Validation (SR-01 / SR-02)**: Edge sensors sign readings using HMAC-SHA256; timestamps are validated against a 30-second window with nonce replay caching.
5. **Physical Plausibility & Jump Detection (SR-08)**: Impossible speeds ($>160\text{ km/h}$), contradictory occupancy states, and extreme sudden jumps are automatically flagged and excluded from congestion calculations.
6. **Emergency Green Corridor Preemption (SR-07 / FR-05)**: Dispatchers generate conflict-free green routes computed via Breadth-First Search (BFS) with auto-expiration and rate limits.
7. **Tamper-Evident SHA-256 Audit Chain (SR-05)**: Every security and operational event is cryptographically hash-chained; the `/api/audit/verify` endpoint verifies chain integrity on demand.

---

## Quick Start & Setup

### 1. Local Python Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Seed initial database
python -m scripts.seed

# Start SecureFlow application (serves UI and API on http://127.0.0.1:8000)
python -m uvicorn secureflow.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Run with Docker Compose
```bash
# Starts PostgreSQL database, backend app, and traffic simulators
docker compose up --build
```

### 3. Deploy to Kubernetes / Minikube
```bash
bash scripts/minikube_deploy.sh
```

---

## Demo Accounts

All demo accounts share the password `Demo@1234`. Supervisors and Administrators require the MFA code `123456`.

| Username | Name | Role | Multi-Factor Authentication |
|---|---|---|:---:|
| `priya` | Priya Nair | Operator | No |
| `rahul` | Rahul Menon | Operator | No |
| `meera` | Meera Iyer | Supervisor | **Yes (123456)** |
| `arjun` | Arjun Rao | Supervisor | **Yes (123456)** |
| `sana` | Sana Khan | Administrator | **Yes (123456)** |
| `dev` | Dev Patel | Analyst | No |
| `kavya` | Kavya Reddy | Auditor | No |
| `ems` | Control EMS | Emergency Dispatcher | No |

---

## Step-by-Step Demo Script

### Demo 1: Two-Person Rule Signal Approval
1. Sign in as **Priya** (`priya` / `Demo@1234`).
2. Navigate to **Signals** (`#/signals`) and propose a timing change for **Station Square (J-05)**.
3. Switch role to **Meera** (Supervisor) via the sidebar demo box.
4. Review the change under **Change Requests** and click **Approve**.
5. Observe the live status update to `APPLIED` with signed command dispatch to the controller.

### Demo 2: Emergency Vehicle Green Wave Corridor
1. Sign in as **Control EMS** (`ems` / `Demo@1234`).
2. Navigate to **Emergency** (`#/emergency`).
3. Select vehicle `EV-AMB-12`, Origin `J-07 (Riverside)`, Destination `J-09 (Hospital Cross)`, and click **Request green corridor**.
4. Open the **Dashboard** map to see the animated green corridor flow across `J-07 -> J-08 -> J-09`.

### Demo 3: Live Attack Simulations (Security Center)
1. Sign in as **Sana** (Admin) or **Meera** (Supervisor).
2. Open **Security Center** (`#/security`).
3. Run one-click simulations (`THR-01` to `THR-12`) to exercise real defensive controls:
   - `THR-01`: Rejection of unregistered sensor device ID.
   - `THR-02`: Plausibility check flagging 480 km/h speed reading.
   - `THR-03`: Replay attack blocked by duplicate nonce detection.
   - `THR-04`: Direct signal change blocked without two-person approval.
   - `THR-06`: Rapid telemetry flood blocked by rate limiter.

### Demo 4: Audit Log Hash Chain Verification & Tamper Detection
1. Navigate to **Audit Log** (`#/audit`).
2. Click **Verify chain** $\rightarrow$ Observe `Chain intact. N entries verified.`
3. Click **Demo: tamper with an entry** $\rightarrow$ Simulates direct database tampering.
4. Click **Verify chain** $\rightarrow$ Detects broken hash chain at the tampered entry number.
5. Click **Undo demo tamper** $\rightarrow$ Re-verifying confirms the chain is intact again.

---

## Endpoint & Role Authorization Matrix

| Endpoint | Method | Required Permission | Allowed Roles |
|---|:---:|---|---|
| `/api/auth/login` | POST | Public | Anyone (lockout after 5 fails) |
| `/api/auth/mfa` | POST | Public | Enrolled users |
| `/api/me` | GET | Authenticated | All signed-in users |
| `/api/junctions` | GET | `dashboard.view` | All roles |
| `/api/events` | GET | `dashboard.view` | All roles (SSE Stream) |
| `/api/signal-requests` | POST | `signal.propose` | `operator`, `supervisor` |
| `/api/signal-requests/{id}/decision` | POST | `signal.approve` | `supervisor` (proposer excluded) |
| `/api/emergency` | POST | `emergency.create` | `emergency_dispatcher` |
| `/api/emergency/{id}` | DELETE | `emergency.cancel` | `emergency_dispatcher`, `supervisor` |
| `/api/incidents` | POST | `incident.write` | `operator`, `supervisor` |
| `/api/incidents/{id}/status` | PATCH | `incident.write` | `operator`, `supervisor` (close: supervisor only) |
| `/api/alerts/{id}/ack` | POST | `alert.view` | `operator`, `supervisor`, `admin` |
| `/api/admin/sensors` | POST | `sensor.manage` | `admin` |
| `/api/admin/users` | GET / PATCH | `user.manage` | `admin` |
| `/api/audit/verify` | GET | `audit.view` | `admin`, `auditor` |
| `/api/security/simulate/{id}` | POST | `security.simulate` | `supervisor`, `admin` |
| `/api/telemetry` | POST | Public (Device HMAC) | Edge Sensors |

---

## Test Results & DevSecOps Verification

Run all test suites and quality gates with:
```bash
# Run pytest with coverage report
make test

# Run security static analysis
make scan
```
- **Automated Tests**: 67 passed, 0 failed.
- **Code Coverage**: $\mathbf{86\%}$ (exceeds $80\%$ requirement).
- **SAST (Bandit)**: 0 issues identified.
- **Secrets (Gitleaks)**: 0 secrets detected.
