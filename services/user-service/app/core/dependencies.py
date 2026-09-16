"""
FastAPI Dependencies

Reusable dependency functions injected via Depends().
These handle:
  - Database session lifecycle (one session per request, auto-committed/rolled-back)
  - Redis connection reuse
  - JWT token extraction and validation
  - Role-based access control enforcement

Using dependency injection keeps routers thin — they just declare
what they need and the framework wires it up.
"""

import logging
from typing import Annotated, Optional

import redis.asyncio as redis_client
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AccountInactiveError,
    InvalidTokenError,
    PermissionDeniedError,
    RateLimitExceededError,
)
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

# OAuth2 bearer scheme — extracts token from Authorization: Bearer <token>
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Database session dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncSession:
    """
    Yields a database session for the duration of one request.
    Commits on success, rolls back on any exception.
    Always closes the session when the request is done.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Redis connection dependency
# ---------------------------------------------------------------------------

_redis_pool: Optional[redis_client.Redis] = None


def get_redis() -> redis_client.Redis:
    """
    Returns the shared Redis connection pool.
    The pool is created once at startup and reused across requests.
    Individual commands borrow connections from the pool automatically.
    """
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis_client.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


# ---------------------------------------------------------------------------
# JWT token extraction and validation
# ---------------------------------------------------------------------------

async def get_current_user_payload(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
) -> dict:
    """
    Extract and validate the JWT from the Authorization header.
    Returns the decoded token payload on success.
    Raises 401 on missing, invalid, or expired tokens.
    """
    if credentials is None:
        raise InvalidTokenError("Authorization header missing")

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError as exc:
        # Log the specific error but return a generic message to the client
        logger.debug("JWT validation failed: %s", exc)
        raise InvalidTokenError()

    return payload


# ---------------------------------------------------------------------------
# Current user injection (with database lookup)
# ---------------------------------------------------------------------------

async def get_current_user(
    payload: Annotated[dict, Depends(get_current_user_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Load the full user object from the database using the JWT subject.

    We do a DB lookup here (rather than trusting only the JWT) to ensure:
    - Deactivated accounts cannot use an old valid JWT
    - The user record still exists

    This adds one DB query per authenticated request. The trade-off is
    acceptable because the alternative (trusting only JWT) means a deactivated
    account stays active until token expiry.
    """
    from app.repositories.user_repository import UserRepository

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError("Token missing subject claim")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)

    if user is None:
        raise InvalidTokenError("User account no longer exists")

    if not user.is_active:
        raise AccountInactiveError()

    return user


# ---------------------------------------------------------------------------
# Role-based access control helpers
# ---------------------------------------------------------------------------

def require_role(*allowed_roles: str):
    """
    Returns a dependency that enforces role-based access.

    Usage:
        @router.get("/admin/users")
        async def list_users(
            current_user = Depends(require_role("ADMIN"))
        ):
            ...
    """
    async def _check_role(
        current_user=Depends(get_current_user),
    ):
        if current_user.role.value not in allowed_roles:
            raise PermissionDeniedError(
                f"This endpoint requires one of these roles: {', '.join(allowed_roles)}"
            )
        return current_user

    return _check_role


# Convenience aliases
require_student = require_role("STUDENT")
require_teacher = require_role("TEACHER")
require_admin = require_role("ADMIN")
require_teacher_or_admin = require_role("TEACHER", "ADMIN")
require_any_authenticated = require_role("STUDENT", "TEACHER", "ADMIN")


# ---------------------------------------------------------------------------
# Rate limiting dependency
# ---------------------------------------------------------------------------

def rate_limit(max_requests: int, window_seconds: int = 60, key_prefix: str = "rl"):
    """
    Redis sliding-window rate limiter.

    Uses INCR + EXPIRE pattern:
    - First request in window: INCR creates key with count=1, then EXPIRE sets TTL
    - Subsequent requests: INCR increments count
    - When count exceeds max_requests: return 429

    The key includes the client IP so different users have separate limits.
    """
    async def _check_rate_limit(
        request=None,
        redis: redis_client.Redis = Depends(get_redis),
    ):
        # Extract client identifier (IP or user ID if available)
        client_ip = "unknown"
        if request:
            forwarded_for = request.headers.get("X-Forwarded-For")
            client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
                request.client.host if request.client else "unknown"
            )

        key = f"{key_prefix}:{client_ip}"

        current_count = await redis.incr(key)

        if current_count == 1:
            # First request in this window — set the expiry
            await redis.expire(key, window_seconds)

        if current_count > max_requests:
            raise RateLimitExceededError(
                f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s."
            )

    return _check_rate_limit


# Pre-built rate limiters for common endpoints
login_rate_limit = rate_limit(
    max_requests=settings.rate_limit_login,
    window_seconds=60,
    key_prefix="rate_limit:login",
)

register_rate_limit = rate_limit(
    max_requests=settings.rate_limit_register,
    window_seconds=60,
    key_prefix="rate_limit:register",
)

general_rate_limit = rate_limit(
    max_requests=settings.rate_limit_general,
    window_seconds=60,
    key_prefix="rate_limit:general",
)
