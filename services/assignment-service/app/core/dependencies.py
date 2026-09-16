import logging
from typing import Annotated, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTokenError, PermissionDeniedError
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_current_user_payload(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> dict:
    if credentials is None:
        raise InvalidTokenError("Authorization header missing")

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError as exc:
        logger.debug("JWT validation failed: %s", exc)
        raise InvalidTokenError("Invalid or expired token")

    return payload

class AuthenticatedUser:
    def __init__(self, user_id: str, role: str):
        self.user_id = user_id
        self.role = role

    @property
    def is_teacher(self):
        return self.role == "TEACHER"

    @property
    def is_student(self):
        return self.role == "STUDENT"

    @property
    def is_admin(self):
        return self.role == "ADMIN"

async def get_current_user(
    payload: Annotated[dict, Depends(get_current_user_payload)],
) -> AuthenticatedUser:
    """
    Stateless check. Extracts user_id and role from JWT.
    (Note: cross-service checking if user is still active can be done
    if we implemented a shared Redis token blacklist, but here we rely
    on short-lived access tokens).
    """
    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or not role:
        raise InvalidTokenError("Token missing sub or role")
    return AuthenticatedUser(user_id=user_id, role=role)

def require_role(*allowed_roles: str):
    async def _check_role(user: AuthenticatedUser = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise PermissionDeniedError(f"Requires one of roles: {', '.join(allowed_roles)}")
        return user
    return _check_role

require_teacher = require_role("TEACHER")
require_student = require_role("STUDENT")
require_admin = require_role("ADMIN")
require_teacher_or_admin = require_role("TEACHER", "ADMIN")
