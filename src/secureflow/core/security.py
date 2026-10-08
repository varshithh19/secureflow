"""SecureFlow Cryptography, Password Hashing, JWT & TOTP MFA Utilities.

Satisfies SR-01, SR-02, SR-05, TB2.
"""
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from secureflow.core.config import get_settings

# Argon2id Password Hasher with strong parameters
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return ph.hash(password)


def verify_password(hashed_password: str, plain_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, Exception):
        return False


def create_access_token(subject: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived JWT access token (15-minute default) stored in memory."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expire,
        "jti": secrets.token_hex(16)
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> Tuple[str, str]:
    """Create a long-lived JWT refresh token with a unique ID for rotation."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=settings.REFRESH_TOKEN_EXPIRE_HOURS)

    jti = secrets.token_hex(16)
    payload: Dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "iat": now,
        "exp": expire,
        "jti": jti
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str, expected_type: Optional[str] = "access") -> Dict[str, Any]:
    """Decode and validate a JWT token signature and expiration."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]}
        )
        if expected_type and payload.get("type") != expected_type:
            raise jwt.InvalidTokenError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")
        return payload
    except jwt.PyJWTError as e:
        raise jwt.InvalidTokenError(str(e)) from e


# TOTP Multi-Factor Authentication Utilities (pyotp)
def generate_totp_secret() -> str:
    """Generate a base32 TOTP secret key for MFA."""
    return pyotp.random_base32()


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code with +/- 1 time step tolerance (valid window 60s)."""
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code.strip(), valid_window=1)


# Cryptographic HMAC & Digest Utilities (TB1, TB4, SR-01, SR-02)
def compute_hmac_sha256(key: bytes, message: bytes) -> str:
    """Compute an HMAC-SHA256 hex digest for a message and secret key."""
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_hmac_sha256(key: bytes, message: bytes, expected_signature: str) -> bool:
    """Verify an HMAC-SHA256 signature using constant-time comparison."""
    computed = compute_hmac_sha256(key, message)
    return hmac.compare_digest(computed.lower(), expected_signature.lower())


def hash_device_secret(secret_hex: str) -> str:
    """Store device secrets hashed with SHA-256 so raw secrets are never persisted."""
    return hashlib.sha256(secret_hex.encode("utf-8")).hexdigest()


# Audit Log Tamper-Evident Hash Chaining (SR-05)
def compute_audit_hash(prev_hash: str, seq: int, ts: int, actor: str, action: str, target: str, result: str, detail: str) -> str:
    """Compute SHA-256 hash for an audit log entry chained to the previous entry."""
    payload = f"{prev_hash}|{seq}|{ts}|{actor}|{action}|{target}|{result}|{detail}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
