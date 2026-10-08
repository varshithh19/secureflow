# SecureFlow - Canonical System Facts & Reference IDs

This document defines the canonical constants, identifiers, requirements, threats, and trust boundaries for the **SecureFlow Smart City Traffic Management System** (24CYS401 Lab).

---

## 1. Functional Requirements (FR)

| ID | Title | Description |
|---|---|---|
| **FR-01** | Sensor Registration | Onboard sensors with unique ID, type, location, and issue one-time secret key. |
| **FR-02** | Real-Time Telemetry Ingestion | Ingest live sensor readings (speed, count, occupancy) with sub-second processing. |
| **FR-03** | Congestion Detection | Calculate congestion levels (Low, Moderate, High, Severe) using standard thresholds. |
| **FR-04** | Signal Configuration with Approval | Propose and approve signal timing plans under a strict two-person rule. |
| **FR-05** | Emergency Priority Corridor | Calculate conflict-free emergency green corridors via BFS route finding. |
| **FR-06** | Real-Time Dashboards | Provide live situational awareness map and metrics over Server-Sent Events (SSE). |
| **FR-07** | Incident & Alert Management | Track operational incidents through structured lifecycles with supervisor close. |
| **FR-08** | Historical Traffic Analysis | Aggregate telemetry by hour and junction with parameterised reporting and safe CSV export. |

---

## 2. Security Requirements (SR) & Non-Functional Requirements (NFR)

| ID | Title | Implementation |
|---|---|---|
| **SR-01** | Device Authentication | Pre-shared HMAC-SHA256 secrets per device, stored hashed; TLS in transit. |
| **SR-02** | Signed Telemetry & Nonce Store | Cryptographic HMAC signature, 30s timestamp window, and single-use nonces with TTL. |
| **SR-03** | Server-Side RBAC | Deny-by-default role permission enforcement on every endpoint via FastAPI dependency. |
| **SR-04** | Two-Person Approval & Safe Bounds | Proposer cannot approve own signal changes; signal intervals clamped to SAFE constants. |
| **SR-05** | Tamper-Evident Audit Log | Append-only SHA-256 hash-chained log with automated chain verification. |
| **SR-06** | Rate Limiting | IP and identity-based request throttling (`slowapi`) on public and telemetry endpoints. |
| **SR-07** | Authenticated Emergency Preemption | Role-restricted emergency dispatch token with strict duration and vehicle rate limits. |
| **SR-08** | Telemetry Plausibility Checks | Speed/count limit verification, jump limits vs prior reading, and neighbour cross-checks. |
| **SR-09** | Input Validation & Query Parameterization | Pydantic v2 schemas, strict type enforcement, SQLAlchemy ORM parameterized queries. |
| **NFR-01** | Latency Performance | Telemetry ingestion and SSE broadcast latency strictly under 1 second. |
| **NFR-02** | Fail-Safe Default Operation | Controllers revert to local fixed-time plan upon loss of backend heartbeat. |

---

## 3. Threat Model Catalog (THR)

| Threat ID | Threat Name | STRIDE Category | Mitigation Control |
|---|---|---|---|
| **THR-01** | Spoofed Sensor Device | Spoofing | SR-01 (Device registry validation & HMAC check) |
| **THR-02** | False Traffic Data Injection | Tampering | SR-08 (Physical plausibility & neighbour checks) |
| **THR-03** | Replay of Captured Telemetry | Repudiation / Tampering | SR-02 (Timestamp +/-30s & unique nonce cache) |
| **THR-04** | Signal Change Without Approval | Elevation of Privilege | SR-04 (Two-person approval & controller signature verification) |
| **THR-05** | Privilege Escalation in Role Management | Elevation of Privilege | SR-03 (Server-side RBAC & self-role change prevention) |
| **THR-06** | Telemetry Flood Denial of Service | Denial of Service | SR-06 (SlowAPI rate limiting per IP and device) |
| **THR-07** | Session Hijacking & Token Theft | Information Disclosure | In-memory access token, HttpOnly/Secure/SameSite refresh cookie, CSRF tokens |
| **THR-08** | SQL / Query Parameter Injection | Tampering / Info Disclosure | SR-09 (SQLAlchemy parameterized queries & whitelist filters) |
| **THR-09** | Cross-Site Scripting (XSS) | Tampering | Strict CSP (no unsafe-inline), automated HTML escaping |
| **THR-10** | Forged Emergency Corridor Request | Spoofing / Tampering | SR-07 (Strict RBAC, dispatcher auth, 3 req / 10m vehicle limit) |
| **THR-11** | Audit Trail Manipulation | Tampering / Repudiation | SR-05 (SHA-256 hash chain & verify endpoint) |
| **THR-12** | SQL Injection in Analytics Filter | Tampering | SR-09 (Whitelist validation & ORM filters) |
| **THR-13** | Controller Network Partitioning | Denial of Service | NFR-02 (Local fallback plan & heartbeat alarms) |

---

## 4. Trust Boundaries (TB)

- **TB1 (IoT Zone to Gateway)**: Edge sensors communicating over TLS / HMAC-signed HTTP to `/api/telemetry`.
- **TB2 (Browser to API)**: Web operator browser to FastAPI backend via HTTPS, JWT in memory, HttpOnly refresh cookie, and CSRF token.
- **TB3 (App to Database)**: Backend application layer to PostgreSQL over TLS with least-privilege credentials.
- **TB4 (Backend to Signal Controller)**: Signed cryptographic commands sent to physical/simulated controllers.
- **TB5 (Emergency Vehicle Channel)**: Emergency dispatcher station to backend dispatch API.

---

## 5. Role-Based Access Control (RBAC) Matrix

| Permission | operator | supervisor | admin | analyst | auditor | emergency_dispatcher |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `dashboard.view` | Yes | Yes | Yes | Yes | Yes | Yes |
| `signal.view` | Yes | Yes | Yes | - | - | - |
| `signal.propose` | Yes | Yes | - | - | - | - |
| `signal.approve` | - | Yes | - | - | - | - |
| `emergency.view` | Yes | Yes | Yes | - | - | Yes |
| `emergency.create` | - | - | - | - | - | Yes |
| `emergency.cancel` | - | Yes | - | - | - | Yes |
| `incident.view` | Yes | Yes | Yes | - | - | - |
| `incident.write` | Yes | Yes | - | - | - | - |
| `alert.view` | Yes | Yes | Yes | - | - | - |
| `analytics.view` | Yes | Yes | Yes | Yes | - | - |
| `sensor.view` | Yes | Yes | Yes | - | - | - |
| `sensor.manage` | - | - | Yes | - | - | - |
| `user.manage` | - | - | Yes | - | - | - |
| `audit.view` | - | - | Yes | - | Yes | - |
| `security.view` | - | Yes | Yes | - | Yes | - |
| `security.simulate` | - | Yes | Yes | - | - | - |

---

## 6. Safety Constants (SAFE)

- **North-South Green (`ns`)**: 10 s to 120 s
- **East-West Green (`ew`)**: 10 s to 120 s
- **Amber (`yellow`)**: 3 s to 5 s
- **All-Red (`allred`)**: 1 s to 5 s
- **Maximum Cycle Length (`cycle`)**: 240 s
- **Calculation**: $\text{Cycle} = \text{ns} + \text{ew} + 2 \times (\text{yellow} + \text{allred})$

---

## 7. Junction & Road Topology

- **Junctions (9)**:
  - `J-01`: Central Plaza (100, 80)
  - `J-02`: Harbour Road (300, 80)
  - `J-03`: Tech Park Gate (500, 80)
  - `J-04`: Old Market (100, 210)
  - `J-05`: Station Square (300, 210)
  - `J-06`: University Gate (500, 210)
  - `J-07`: Riverside (100, 340)
  - `J-08`: Airport Link (300, 340)
  - `J-09`: Hospital Cross (500, 340)
- **Road Edges (12)**:
  - `J-01` <-> `J-02`, `J-02` <-> `J-03`
  - `J-04` <-> `J-05`, `J-05` <-> `J-06`
  - `J-07` <-> `J-08`, `J-08` <-> `J-09`
  - `J-01` <-> `J-04`, `J-04` <-> `J-07`
  - `J-02` <-> `J-05`, `J-05` <-> `J-08`
  - `J-03` <-> `J-06`, `J-06` <-> `J-09`
