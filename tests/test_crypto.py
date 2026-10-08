"""Unit tests for SecureFlow Cryptography, Password Hashing, and TOTP MFA."""
import hashlib
import hmac
import pyotp
import pytest

from secureflow.core.security import (
    compute_audit_hash,
    compute_hmac_sha256,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    hash_device_secret,
    hash_password,
    verify_hmac_sha256,
    verify_password,
    verify_totp_code,
)


def test_argon2_password_hashing():
    raw_password = "SecurePassword@123"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, raw_password) is True
    assert verify_password(hashed, "WrongPassword@123") is False


def test_jwt_access_and_refresh_tokens():
    user_id = "priya"
    role = "operator"

    token = create_access_token(subject=user_id, role=role)
    payload = decode_token(token, expected_type="access")

    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert payload["type"] == "access"

    refresh_token, jti = create_refresh_token(subject=user_id)
    refresh_payload = decode_token(refresh_token, expected_type="refresh")

    assert refresh_payload["sub"] == user_id
    assert refresh_payload["type"] == "refresh"
    assert refresh_payload["jti"] == jti


def test_totp_mfa_generation_and_verification():
    secret = generate_totp_secret()
    assert len(secret) == 32

    totp = pyotp.TOTP(secret)
    current_code = totp.now()

    assert verify_totp_code(secret, current_code) is True
    assert verify_totp_code(secret, "000000") is False
    assert verify_totp_code("", current_code) is False


def test_hmac_sha256_telemetry_signature():
    key = b"test-secret-key-32-bytes-long"
    message = b"SN-101|J-01|25|45.50|0.4500|1700000000000|abc123nonce"

    signature = compute_hmac_sha256(key, message)
    assert len(signature) == 64
    assert verify_hmac_sha256(key, message, signature) is True
    assert verify_hmac_sha256(key, message, "0" * 64) is False
    assert verify_hmac_sha256(b"wrong-key", message, signature) is False


def test_audit_hash_chaining():
    prev = "0" * 64
    hash1 = compute_audit_hash(prev, 1, 1700000000, "admin", "LOGIN_SUCCESS", "auth", "OK", "MFA passed")
    assert len(hash1) == 64
    assert hash1 != prev

    hash2 = compute_audit_hash(hash1, 2, 1700000001, "priya", "SIGNAL_PROPOSED", "CR-001", "OK", "J-01")
    assert len(hash2) == 64
    assert hash2 != hash1
