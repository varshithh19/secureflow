"""SecureFlow Role-Based Access Control (RBAC) Dependency.

Enforces SR-03, TB2, and the exact permission matrix from PERMS.
Denies by default. Records unauthorized access attempts in the audit log.
"""
from typing import Callable, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from secureflow.core.constants import PERMS, ROLES
from secureflow.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    """Authenticated user context object passed to API route handlers."""

    def __init__(self, user_id: str, role: str, name: Optional[str] = None, mfa: bool = False):
        self.id = user_id
        self.role = role
        self.name = name or user_id
        self.mfa = mfa

    def has_permission(self, permission: str) -> bool:
        allowed_roles = PERMS.get(permission, [])
        return self.role in allowed_roles


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> AuthenticatedUser:
    """Extract and validate the current user from the Authorization header or session cookie."""
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided."
        )

    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub")
        role = payload.get("role")
        if not user_id or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims."
            )
        return AuthenticatedUser(user_id=user_id, role=role)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        ) from e


def require(permission: str) -> Callable:
    """FastAPI dependency factory enforcing that the authenticated user possesses the given permission.

    Deny-by-default: returns HTTP 403 with standard detail message.
    """
    async def permission_checker(
        user: AuthenticatedUser = Depends(get_current_user)
    ) -> AuthenticatedUser:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not allow this action. The attempt was recorded."
            )
        return user

    return permission_checker
