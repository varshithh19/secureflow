"""Unit tests for Tamper-Evident Hash Chained Audit Log (SR-05 / THR-11)."""
from sqlalchemy.orm import Session

from secureflow.models import AuditLog
from secureflow.services.audit import (
    repair_audit_demo,
    tamper_audit_demo,
    verify_audit_chain,
    write_audit,
)


def test_audit_chain_verification_intact(db_session: Session):
    is_valid, count, broken_seq = verify_audit_chain(db_session)
    assert is_valid is True
    assert count >= 5
    assert broken_seq is None


def test_audit_chain_tamper_detection_and_repair(db_session: Session):
    # Ensure intact initial chain
    ok, count, _ = verify_audit_chain(db_session)
    assert ok is True

    # Tamper with an entry directly in the database
    res = tamper_audit_demo(db_session, actor="sana")
    tampered_seq = res["seq"]

    # Verify chain: must detect hash chain failure at tampered entry
    is_valid, _, broken_seq = verify_audit_chain(db_session)
    assert is_valid is False
    assert broken_seq == tampered_seq

    # Repair demo tamper
    repair_audit_demo(db_session)

    # Verify chain restored
    is_valid_after, _, _ = verify_audit_chain(db_session)
    assert is_valid_after is True
