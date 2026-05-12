# backend/app/core/security.py
"""
Security utilities:
  - Password hashing / verification (bcrypt via passlib)
  - JWT access-token and refresh-token creation / decoding
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _create_token(subject: str, expires_delta: timedelta, extra: dict[str, Any] | None = None) -> str:
    """
    Create a signed JWT.

    Args:
        subject:       The user identifier (UUID as string).
        expires_delta: How long until the token expires.
        extra:         Any additional claims to embed (e.g. {"type": "refresh"}).
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra:
        payload.update(extra)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str) -> str:
    """Short-lived token sent in the Authorization header."""
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra={"type": "access"},
    )


def create_refresh_token(user_id: str) -> str:
    """Longer-lived token stored in an httpOnly cookie."""
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        extra={"type": "refresh"},
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT.

    Returns the payload dict on success.
    Raises JWTError on invalid / expired tokens.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def decode_access_token(token: str) -> str:
    """
    Decode an *access* token and return the user_id (sub claim).

    Raises JWTError if the token is invalid, expired, or is not an access token.
    """
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    sub: str | None = payload.get("sub")
    if sub is None:
        raise JWTError("Token missing 'sub' claim")
    return sub


def decode_refresh_token(token: str) -> str:
    """
    Decode a *refresh* token and return the user_id (sub claim).

    Raises JWTError if the token is invalid, expired, or is not a refresh token.
    """
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Not a refresh token")
    sub: str | None = payload.get("sub")
    if sub is None:
        raise JWTError("Token missing 'sub' claim")
    return sub
