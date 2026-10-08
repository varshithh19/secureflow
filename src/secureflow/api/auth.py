"""SecureFlow Authentication & Session API Routers."""
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from secureflow.core.rbac import AuthenticatedUser, get_current_user
from secureflow.models import User
from secureflow.repositories.database import get_db
from secureflow.schemas import LoginRequest, LoginResponse, MFARequest, UserSummary
from secureflow.services.auth import (
    authenticate_user,
    complete_mfa_login,
    issue_tokens_for_user,
    refresh_user_token,
)

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
me_router = APIRouter(prefix="/api/me", tags=["me"])


@auth_router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Authenticate username and password."""
    user, mfa_required, err = authenticate_user(db, payload.username, payload.password)
    if err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=err)

    if mfa_required:
        return LoginResponse(
            mfa_required=True,
            name=user.name,
            role=user.role
        )

    tokens = issue_tokens_for_user(user)
    # Set HttpOnly, Secure, SameSite=Strict refresh cookie
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=False,  # Allow http in development/lab testing
        samesite="strict",
        max_age=8 * 3600
    )
    return LoginResponse(
        access_token=tokens["access_token"],
        csrf_token=tokens["csrf_token"],
        user=UserSummary.model_validate(tokens["user"])
    )


@auth_router.post("/mfa", response_model=LoginResponse)
async def verify_mfa_code(
    payload: MFARequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Verify 6-digit TOTP MFA code."""
    user, err = complete_mfa_login(db, payload.username, payload.code)
    if err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=err)

    tokens = issue_tokens_for_user(user)
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=8 * 3600
    )
    return LoginResponse(
        access_token=tokens["access_token"],
        csrf_token=tokens["csrf_token"],
        user=UserSummary.model_validate(tokens["user"])
    )


@auth_router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Rotate and refresh access token via HttpOnly cookie."""
    refresh_tok = request.cookies.get("refresh_token")
    if not refresh_tok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing.")

    try:
        tokens = refresh_user_token(db, refresh_tok)
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=False,
            samesite="strict",
            max_age=8 * 3600
        )
        return {
            "access_token": tokens["access_token"],
            "csrf_token": tokens["csrf_token"]
        }
    except Exception as e:
        response.delete_cookie("refresh_token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.") from e


@auth_router.post("/logout")
async def logout(response: Response):
    """Clear session refresh cookie."""
    response.delete_cookie("refresh_token")
    return {"detail": "Logged out successfully."}


@me_router.get("", response_model=UserSummary)
async def get_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return currently authenticated user profile."""
    user = db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return UserSummary(
        id=user.id,
        name=user.name,
        role=user.role,
        mfa=user.mfa_enabled or user.role in ("supervisor", "admin"),
        locked=user.locked,
        fails=user.failed_attempts,
        last=user.last_login
    )
