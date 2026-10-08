# SecureFlow Defect & Vulnerability Tracking Log

This register documents defects identified during automated security testing and fuzzing, their root causes, and verification results.

---

## Defect Log

### DEF-01: Query Parameter Encoding in Fuzzer Client
- **Severity**: Low
- **Component**: `tests/test_fuzzing.py` & `src/secureflow/api/analytics.py`
- **Description**: Raw unencoded control characters (e.g. `\x1f`) in URL paths triggered client-side HTTP parsing errors prior to reaching server routing.
- **Root Cause**: Query parameters passed as formatted raw URL strings instead of structured dictionary parameters.
- **Fix Applied**: Updated test fixtures to use `params={...}` dictionary format ensuring proper RFC 3986 percent-encoding; server validates and returns HTTP 422 for invalid parameter values.
- **Retest Status**: Verified passing across 50 random Hypothesis iterations.

### DEF-02: Broad Exception Handling in Security Metrics
- **Severity**: Low (Bandit B110)
- **Component**: `src/secureflow/api/security.py`
- **Description**: Broad `except Exception: pass` construct caught during static analysis.
- **Root Cause**: Fallback metric retrieval did not specify narrow exception classes.
- **Fix Applied**: Replaced with explicit `except (KeyError, AttributeError, ValueError):` block.
- **Retest Status**: Verified Bandit SAST scan 100% clean.
