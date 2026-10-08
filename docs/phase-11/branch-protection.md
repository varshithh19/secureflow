# Phase 11 - Branch Protection & Repository Security Rules

This document specifies the mandatory GitHub branch protection rules enforced for the `main` branch of SecureFlow.

---

## 1. Branch Protection Rules for `main`

1. **Require Pull Request Before Merging**:
   - Minimum approvals: 1 senior security/software engineer.
   - Dismiss stale pull request approvals when new commits are pushed.
   - Require review from Code Owners (`CODEOWNERS`).

2. **Require Status Checks to Pass Before Merging (Strict CI Gate)**:
   - `Code Quality & Linting` (Ruff)
   - `SAST, Dependency & Secret Scanning` (Bandit, pip-audit, Gitleaks)
   - `Unit, Integration & Fuzz Tests` (Pytest with $\ge 80\%$ coverage)
   - `Container Build & Vulnerability Scan` (Docker multi-stage build & Trivy scan)

3. **Require Signed Commits**:
   - All commits pushed to `main` must be GPG/SSH verified.

4. **Require Linear History**:
   - Force squash merging or rebase merging; prevent merge bubbles.

5. **Do Not Allow Force Pushes & Prevent Branch Deletion**:
   - Protects against accidental history rewrites and audit trail tampering.

---

## 2. Secrets Management & Least-Privilege Rules

- All third-party GitHub Actions are pinned to immutable full 40-character commit SHAs.
- No repository secrets or API credentials stored in source code.
- Gitleaks pre-commit hooks and CI scans prevent leakage of private keys or tokens.
