"""
Security Utilities — JWT and Password Hashing

Centralizes all cryptographic operations so they can be reviewed
and updated in one place.

Password hashing: bcrypt via passlib (industry standard, adaptive cost)
JWT: python-jose with HS256 signature

Design note on refresh tokens:
  Refresh tokens are random secrets (UUID4 + extra entropy).
  We store a SHA-256 hash of the token in PostgreSQL, not the raw token.
  This means even a database breach cannot be used to forge sessions —
  the same principle as hashing passwords.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt with cost factor 12.
# Cost 12 takes ~250ms on modern hardware — slow enough to deter brute force,
# fast enough not to noticeably affect login UX.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain text password. Never store the result next to the input."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, role: str) -> str:
    """
    Create a short-lived JWT access token.

    Claims are minimal by design:
      sub  — user's UUID (principal identifier)
      role — user's role (avoids a DB lookup on every request)
      exp  — expiration time
      iat  — issued at
      jti  — unique token ID (useful for revocation lists in future)

    We do NOT include email, name, or other PII in the token.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.

    Raises JWTError if the token is invalid, expired, or tampered with.
    The caller should catch JWTError and return 401.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )

    if payload.get("type") != "access":
        raise JWTError("Token is not an access token")

    return payload


def create_refresh_token() -> tuple[str, str]:
    """
    Generate a refresh token.

    Returns a tuple: (raw_token, hashed_token)
      - raw_token: sent to the client (stored in HttpOnly cookie or response body)
      - hashed_token: stored in PostgreSQL (refresh_tokens table)

    Using secrets.token_urlsafe for cryptographically secure randomness.
    """
    raw_token = secrets.token_urlsafe(48)
    hashed = hash_token(raw_token)
    return raw_token, hashed


def hash_token(raw_token: str) -> str:
    """SHA-256 hash of a token string. Used for refresh token storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
