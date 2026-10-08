"""SecureFlow User Administration & Audit Log API Routers."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureflow.core.constants import ROLES
from secureflow.core.rbac import AuthenticatedUser, require
from secureflow.models import AuditLog, User
from secureflow.repositories.database import get_db
from secureflow.schemas import (
    AuditEntryResponse,
    SetLockRequest,
    SetRoleRequest,
    UserSummary,
    VerifyAuditResponse,
)
from secureflow.services.audit import (
    repair_audit_demo,
    tamper_audit_demo,
    verify_audit_chain,
    write_audit,
)

users_router = APIRouter(prefix="/api/admin/users", tags=["users"])
audit_router = APIRouter(prefix="/api/audit", tags=["audit"])


# User Admin Endpoints
@users_router.get("", response_model=List[UserSummary])
async def list_users(
    user: AuthenticatedUser = Depends(require("user.manage")),
    db: Session = Depends(get_db)
):
    """List all registered system users and their roles."""
    users = db.execute(select(User).order_by(User.id.asc())).scalars().all()
    return [
        UserSummary(
            id=u.id,
            name=u.name,
            role=u.role,
            mfa=u.mfa_enabled or u.role in ("supervisor", "admin"),
            locked=u.locked,
            fails=u.failed_attempts,
            last=u.last_login
        )
        for u in users
    ]


@users_router.patch("/{user_id}/role", response_model=UserSummary)
async def update_role(
    user_id: str,
    payload: SetRoleRequest,
    user: AuthenticatedUser = Depends(require("user.manage")),
    db: Session = Depends(get_db)
):
    """Change a user's role (admin cannot change own role)."""
    if user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own role.")

    if payload.role not in ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role.")

    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    old_role = target.role
    target.role = payload.role
    db.commit()

    write_audit(db, user.id, "ROLE_CHANGED", target.id, "OK", f"{old_role} to {payload.role}")

    return UserSummary(
        id=target.id,
        name=target.name,
        role=target.role,
        mfa=target.mfa_enabled or target.role in ("supervisor", "admin"),
        locked=target.locked,
        fails=target.failed_attempts,
        last=target.last_login
    )


@users_router.patch("/{user_id}/lock", response_model=UserSummary)
async def set_lock(
    user_id: str,
    payload: SetLockRequest,
    user: AuthenticatedUser = Depends(require("user.manage")),
    db: Session = Depends(get_db)
):
    """Lock or unlock a user account."""
    if user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot lock your own account.")

    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    target.locked = payload.locked
    target.failed_attempts = 0
    db.commit()

    write_audit(db, user.id, "ACCOUNT_LOCKED" if payload.locked else "ACCOUNT_UNLOCKED", target.id, "OK")

    return UserSummary(
        id=target.id,
        name=target.name,
        role=target.role,
        mfa=target.mfa_enabled or target.role in ("supervisor", "admin"),
        locked=target.locked,
        fails=target.failed_attempts,
        last=target.last_login
    )


@users_router.post("/{user_id}/reset-mfa")
async def reset_mfa(
    user_id: str,
    user: AuthenticatedUser = Depends(require("user.manage")),
    db: Session = Depends(get_db)
):
    """Reset user TOTP MFA secret."""
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    write_audit(db, user.id, "MFA_RESET", target.id, "OK", "MFA secret reset")
    return {"detail": "MFA reset. The user must enrol again at next sign-in."}


# Audit Log Endpoints
@audit_router.get("", response_model=List[AuditEntryResponse])
async def list_audit(
    action: Optional[str] = None,
    user: AuthenticatedUser = Depends(require("audit.view")),
    db: Session = Depends(get_db)
):
    """List append-only audit log records."""
    query = select(AuditLog).order_by(AuditLog.seq.asc())
    if action and action != "all":
        query = query.filter(AuditLog.action.like(f"{action}%"))

    entries = db.execute(query).scalars().all()
    return [
        AuditEntryResponse(
            seq=e.seq,
            ts=e.ts,
            actor=e.actor,
            action=e.action,
            target=e.target,
            result=e.result,
            detail=e.detail,
            prev=e.prev_hash,
            hash=e.hash
        )
        for e in entries
    ]


@audit_router.get("/verify", response_model=VerifyAuditResponse)
async def verify_chain(
    user: AuthenticatedUser = Depends(require("audit.view")),
    db: Session = Depends(get_db)
):
    """Verify SHA-256 hash chain integrity."""
    ok, count, broken_seq = verify_audit_chain(db)
    if ok:
        return VerifyAuditResponse(ok=True, n=count)
    return VerifyAuditResponse(ok=False, seq=broken_seq, n=count)


@audit_router.post("/tamper")
async def tamper_demo(
    user: AuthenticatedUser = Depends(require("audit.view")),
    db: Session = Depends(get_db)
):
    """Tamper with a historical audit log record (demonstration only)."""
    try:
        res = tamper_audit_demo(db, user.id)
        return {"seq": res["seq"], "orig": res["orig"]}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@audit_router.post("/repair")
async def repair_demo(
    user: AuthenticatedUser = Depends(require("audit.view")),
    db: Session = Depends(get_db)
):
    """Repair tampered historical audit log record."""
    repair_audit_demo(db)
    return {"detail": "Repaired."}
