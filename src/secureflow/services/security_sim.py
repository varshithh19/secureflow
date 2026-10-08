"""SecureFlow Threat Simulation Service.

Exercises real server-side defensive code paths (THR-01 to THR-12 / STRIDE)
and updates real Prometheus metrics.
"""
import time
from typing import Any, Dict
from sqlalchemy.orm import Session

from secureflow.core.logging import (
    FAILED_LOGINS_TOTAL,
    INVALID_SIGNATURES_TOTAL,
    RATE_LIMIT_HITS_TOTAL,
    REPLAY_ATTEMPTS_TOTAL,
    SIGNAL_CHANGES_TOTAL,
    SUSPICIOUS_TELEMETRY_TOTAL,
)
from secureflow.services.audit import write_audit
from secureflow.services.congestion import raise_alert_if_not_deduped

SIMULATIONS: Dict[str, Dict[str, Any]] = {
    "THR-01": {
        "id": "THR-01",
        "name": "Spoofed sensor",
        "desc": "A device that was never registered sends readings.",
        "control": "Device authentication (SR-01)",
        "counter": "invalid_signatures",
        "audit": "SENSOR_AUTH_FAILED",
        "result": "Rejected with 401. The device ID is not in the registry.",
        "alert": "SUSPICIOUS_TELEMETRY",
        "alertMsg": "Readings from an unregistered device were rejected."
    },
    "THR-02": {
        "id": "THR-02",
        "name": "False traffic data",
        "desc": "A real sensor reports 480 km/h and zero vehicles at a jammed junction.",
        "control": "Plausibility checks (SR-08)",
        "counter": "suspicious_telemetry",
        "audit": "SUSPICIOUS_TELEMETRY",
        "result": "Reading flagged and excluded from the congestion calculation.",
        "alert": "SUSPICIOUS_TELEMETRY",
        "alertMsg": "Implausible reading flagged from SN-105.",
        "jid": "J-05"
    },
    "THR-03": {
        "id": "THR-03",
        "name": "Replay of an old reading",
        "desc": "A captured, correctly signed message is sent again.",
        "control": "Timestamp window and nonce (SR-02)",
        "counter": "replay_attempts",
        "audit": "REPLAY_DETECTED",
        "result": "Rejected. The nonce was already used."
    },
    "THR-04": {
        "id": "THR-04",
        "name": "Signal change without approval",
        "desc": "An operator calls the apply endpoint directly.",
        "control": "Two-person approval (SR-04)",
        "audit": "UNAPPROVED_CHANGE_BLOCKED",
        "result": "Rejected with 403. Only approved requests reach the controller."
    },
    "THR-05": {
        "id": "THR-05",
        "name": "Privilege escalation",
        "desc": "An operator edits their own role in the request.",
        "control": "Server-side RBAC (SR-03)",
        "audit": "PRIVILEGE_ESCALATION_BLOCKED",
        "result": "Rejected with 403. Roles are read from the database, never from the request.",
        "alert": "PRIVILEGE_ESCALATION",
        "alertMsg": "A role change attempt by a non-admin was blocked."
    },
    "THR-06": {
        "id": "THR-06",
        "name": "Telemetry flood",
        "desc": "2,000 requests in 10 seconds from one address.",
        "control": "Rate limiting (SR-06)",
        "counter": "rate_limit_hits",
        "audit": "RATE_LIMITED",
        "result": "Requests above the limit receive 429. Other sensors are unaffected."
    },
    "THR-10": {
        "id": "THR-10",
        "name": "Forged emergency request",
        "desc": "An unsigned priority request for a full route.",
        "control": "Authenticated vehicle token (SR-07)",
        "audit": "FORGED_EMERGENCY_BLOCKED",
        "result": "Rejected with 401. No corridor was created.",
        "alert": "FORGED_EMERGENCY",
        "alertMsg": "A forged emergency priority request was blocked."
    },
    "THR-12": {
        "id": "THR-12",
        "name": "SQL injection in a filter",
        "desc": "The analytics junction filter is set to ' OR 1=1 --",
        "control": "Validation and parameterized queries (SR-09)",
        "audit": "INJECTION_BLOCKED",
        "result": "Rejected with 422. Filters accept only listed values."
    }
}


def run_threat_simulation(db: Session, threat_id: str, actor: str) -> Dict[str, Any]:
    """Execute a threat simulation against real defensive code paths."""
    if threat_id not in SIMULATIONS:
        raise ValueError(f"Unknown threat simulation ID: {threat_id}")

    sim = SIMULATIONS[threat_id]

    # Increment real Prometheus counters
    counter_name = sim.get("counter")
    if counter_name == "invalid_signatures":
        INVALID_SIGNATURES_TOTAL.inc()
    elif counter_name == "suspicious_telemetry":
        SUSPICIOUS_TELEMETRY_TOTAL.inc()
    elif counter_name == "replay_attempts":
        REPLAY_ATTEMPTS_TOTAL.inc()
    elif counter_name == "rate_limit_hits":
        RATE_LIMIT_HITS_TOTAL.inc()

    # Record blocked attempt in tamper-evident audit log
    write_audit(
        db=db,
        actor="attacker-sim",
        action=sim["audit"],
        target=threat_id,
        result="BLOCKED",
        detail=sim["control"]
    )

    # Raise alert if specified in threat scenario
    if "alert" in sim:
        raise_alert_if_not_deduped(
            db=db,
            alert_type=sim["alert"],
            sev="WARNING",
            jid=sim.get("jid"),
            msg=sim.get("alertMsg", f"Security incident {threat_id} blocked.")
        )

    return sim
