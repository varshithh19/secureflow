## SecureFlow Pull Request Quality & Security Gate

### 1. Summary of Changes
<!-- Describe what feature, bug fix, or security enhancement was made -->

### 2. DevSecOps & Security Verification Checklist
- [ ] Central RBAC permissions enforced (`require('...')`)
- [ ] Inputs validated using Pydantic v2 schemas and parameterized queries
- [ ] No secrets or hardcoded credentials committed
- [ ] Structured logging attached with `request_id`
- [ ] Unit & integration tests added (coverage >= 80%)
- [ ] Gitleaks & Bandit SAST passed clean
- [ ] HTML escaping preserved on all dynamic UI bindings

### 3. Related Requirements & Threat IDs
- Canonical IDs: (e.g. `SR-01`, `SR-04`, `THR-02`, `FR-05`)
