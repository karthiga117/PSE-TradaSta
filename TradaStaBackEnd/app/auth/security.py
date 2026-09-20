"""Password hash and JWT helpers for the auth layer."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.auth.exceptions import AuthenticationError
from app.core.config import get_settings


def validate_email(email: str) -> str:
    """Normalize and validate email addresses before database lookup."""
    normalized = (email or "").strip().lower()
    if not normalized or "@" not in normalized:
        raise AuthenticationError("A valid email address is required.")
    return normalized


def validate_password(password: str) -> str:
    """Ensure a password is strong enough for registration and login updates."""
    raw = (password or "").strip()
    if len(raw) < 8:
        raise AuthenticationError("Password must be at least 8 characters long.")
    if not any(ch.isalpha() for ch in raw) or not any(ch.isdigit() for ch in raw):
        raise AuthenticationError("Password must include letters and numbers.")
    return raw


def hash_password(password: str) -> str:
    """Hash a raw password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plain password against a stored hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_token(token: str) -> str:
    """Hash a refresh token before persisting it in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_token(user_id: str, *, token_type: str, role: str, expires_delta: timedelta) -> str:
    """Create a signed JWT containing only minimal claims."""
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise AuthenticationError("JWT secret is not configured.")
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "type": token_type,
        "jti": generate_rich_nonce(),
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, role: str) -> str:
    """Create a short-lived bearer token for protected resources."""
    settings = get_settings()
    token = create_token(
        user_id,
        token_type="access",
        role=role,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )
    return token


def create_refresh_token(user_id: str, role: str) -> str:
    """Create a long-lived refresh token for rotating session renewal."""
    settings = get_settings()
    token = create_token(
        user_id,
        token_type="refresh",
        role=role,
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    return token


def decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    """Validate a JWT signature, type, and expiry."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat", "type"]},
        )
    except jwt.PyJWTError as exc:  # pragma: no cover - delegated to caller
        raise AuthenticationError("Token verification failed.") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError(f"This token is not a valid {expected_type} token.")
    return payload


def generate_rich_nonce() -> str:
    """Return a cryptographically secure random value for opaque refresh token ids."""
    return secrets.token_urlsafe(32)
