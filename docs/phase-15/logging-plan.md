# Phase 15 - Logging & Monitoring Plan

This plan defines the structured logging and metrics architecture for SecureFlow.

---

## 1. Structured JSON Logging Architecture

All application log events are emitted to standard output in structured JSON format with uniform fields:
- `timestamp`: ISO-8601 UTC timestamp
- `level`: Log severity (INFO, WARNING, ERROR, CRITICAL)
- `logger`: Originating logger name (`secureflow`)
- `message`: Human-readable summary
- `request_id`: Unique correlation UUID (`X-Request-ID`) attached via middleware
- `actor`: Authenticated user or device identity
- `action`: Canonical operation identifier (e.g. `SIGNAL_CHANGE_APPROVED`)
- `target`: Target entity ID (e.g. `CR-002`, `SN-105`)
- `ip`: Client IP address

---

## 2. Key Monitored Security Metrics (Prometheus)

| Metric Name | Type | Purpose |
|---|---|---|
| `failed_logins_total` | Counter | Tracks failed sign-in attempts for brute force detection |
| `invalid_signatures_total` | Counter | Detects sensor spoofing and telemetry tampering (THR-01) |
| `replay_attempts_total` | Counter | Counts blocked replayed nonces and stale timestamps (THR-03) |
| `rate_limit_hits_total` | Counter | Monitored for traffic flooding / DoS attempts (THR-06) |
| `suspicious_telemetry_total` | Counter | Counts implausible sensor readings (THR-02) |
| `signal_changes_total{status}` | Counter | Tracks proposed, approved, applied, and rejected timing plans |
| `emergency_requests_total` | Counter | Volume of green wave emergency requests |
| `audit_chain_valid` | Gauge | Continuous integrity status of the SHA-256 audit hash chain (1=valid, 0=tampered) |
| `ingest_latency_seconds` | Histogram | Telemetry ingestion latency distribution (p50, p95, p99) |
