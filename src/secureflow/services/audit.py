"""SecureFlow Tamper-Evident Audit Service.

Implements SR-05 and THR-11:
- Append-only hash chained audit log using SHA-256
- Automated chain verification
- Audit events for all security and operational actions
"""
import time
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.core.logging import AUDIT_CHAIN_VALID_GAUGE
from secureflow.core.security import compute_audit_hash
from secureflow.models import AuditLog


def write_audit(
    db: Session,
    actor: str,
    action: str,
    target: str,
    result: str = "OK",
    detail: str = "",
    ts: Optional[int] = None
) -> AuditLog:
    """Append a new tamper-evident audit record to the hash chain."""
    if ts is None:
        ts = int(time.time() * 1000)

    # Fetch last audit record in the chain
    last_entry = db.execute(
        select(AuditLog).order_by(AuditLog.seq.desc()).limit(1)
    ).scalar_one_or_none()

    prev_hash = last_entry.hash if last_entry else "0" * 64
    seq = (last_entry.seq + 1) if last_entry else 1

    entry_hash = compute_audit_hash(
        prev_hash=prev_hash,
        seq=seq,
        ts=ts,
        actor=actor,
        action=action,
        target=target,
        result=result,
        detail=detail
    )

    log_entry = AuditLog(
        seq=seq,
        ts=ts,
        actor=actor,
        action=action,
        target=target,
        result=result,
        detail=detail,
        prev_hash=prev_hash,
        hash=entry_hash
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def verify_audit_chain(db: Session) -> Tuple[bool, int, Optional[int]]:
    """Recompute and verify the entire SHA-256 hash chain from genesis to head.

    Returns:
        (is_valid, total_verified_count, broken_seq_number)
    """
    entries = db.execute(
        select(AuditLog).order_by(AuditLog.seq.asc())
    ).scalars().all()

    prev_hash = "0" * 64
    for entry in entries:
        if entry.prev_hash != prev_hash:
            AUDIT_CHAIN_VALID_GAUGE.set(0)
            return False, len(entries), entry.seq

        expected_hash = compute_audit_hash(
            prev_hash=entry.prev_hash,
            seq=entry.seq,
            ts=entry.ts,
            actor=entry.actor,
            action=entry.action,
            target=entry.target,
            result=entry.result,
            detail=entry.detail
        )
        if entry.hash != expected_hash:
            AUDIT_CHAIN_VALID_GAUGE.set(0)
            return False, len(entries), entry.seq

        prev_hash = entry.hash

    AUDIT_CHAIN_VALID_GAUGE.set(1)
    return True, len(entries), None


# Tamper & Repair Demo Helpers
_tampered_state: Dict[str, Any] = {"seq": None, "orig": None}


def tamper_audit_demo(db: Session, actor: str = "admin") -> Dict[str, Any]:
    """Intentionally alter a historical entry to demonstrate hash chain break."""
    entries = db.execute(
        select(AuditLog).order_by(AuditLog.seq.asc())
    ).scalars().all()

    if not entries:
        raise ValueError("No audit entries available to tamper.")

    target_idx = max(0, len(entries) - 4)
    target_entry = entries[target_idx]
    _tampered_state["seq"] = target_entry.seq
    _tampered_state["orig"] = target_entry.detail

    target_entry.detail = "edited by attacker"
    db.commit()

    write_audit(db, actor, "AUDIT_TAMPER_DEMO", f"#{target_entry.seq}", "WARN", "demo only")
    return {"seq": target_entry.seq, "orig": _tampered_state["orig"]}


def repair_audit_demo(db: Session) -> None:
    """Restore tampered entry to valid state."""
    if _tampered_state["seq"] is not None:
        entry = db.get(AuditLog, _tampered_state["seq"])
        if entry:
            entry.detail = _tampered_state["orig"]
            db.commit()
        _tampered_state["seq"] = None
        _tampered_state["orig"] = None
