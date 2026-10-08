# Phase 15 - Security Hardening Checklist

This checklist documents the defensive controls implemented across application, container, network, and host layers.

---

## 1. Application Layer Hardening
- [x] **Strict Content Security Policy (CSP)**: No `'unsafe-inline'` or `'unsafe-eval'`. All fonts, scripts, and CSS self-hosted.
- [x] **HTTP Security Headers**: Strict-Transport-Security (HSTS), X-Content-Type-Options (nosniff), X-Frame-Options (DENY), Referrer-Policy, Permissions-Policy.
- [x] **In-Memory JWT Tokens**: Access token kept in browser memory only; refresh token in HttpOnly, SameSite=Strict cookie.
- [x] **CSRF Protection**: Synchronizer token pattern with `X-CSRF-Token` headers.
- [x] **Generic Error Serialization**: No stack traces or internal exception details leaked to clients.
- [x] **Two-Person Rule**: Proposer cannot approve own signal change requests.

---

## 2. Container & Image Hardening
- [x] **Multi-Stage Build**: Compilation tools (gcc, build-essential) excluded from final runtime image.
- [x] **Non-Root Execution**: Runs under unprivileged user `secureflow` (UID 10001).
- [x] **Pinned Base Image**: `python:3.12-slim` pinned.
- [x] **Healthchecks**: Built-in container healthcheck via `/healthz`.

---

## 3. Kubernetes Pod Security Standards (Restricted)
- [x] `runAsNonRoot: true` and `runAsUser: 10001`
- [x] `readOnlyRootFilesystem: true` with `emptyDir` for writable `/tmp`
- [x] `allowPrivilegeEscalation: false`
- [x] `capabilities: drop: ["ALL"]`
- [x] `seccompProfile: type: "RuntimeDefault"`
- [x] `NetworkPolicy`: Default-deny ingress/egress, explicit pod-to-database communication only.
