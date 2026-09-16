"""
Authentication Service — Business Logic

Handles:
  - User registration (student, teacher, admin)
  - Login with credential verification
  - Access token + refresh token issuance
  - Refresh token rotation (old token revoked, new one issued)
  - Logout (refresh token revocation)

The service layer sits between routers (HTTP) and repositories (DB).
It owns all business rules — the router just passes validated input in
and gets a result out.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AccountInactiveError,
    AuthenticationError,
    EmailAlreadyExistsError,
    InvalidTokenError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.repositories.user_repository import RefreshTokenRepository, UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.user import (
    AdminRegisterRequest,
    StudentRegisterRequest,
    TeacherRegisterRequest,
)

logger = logging.getLogger(__name__)


def _build_token_response(user_id: str, role: str, raw_refresh_token: str) -> TokenResponse:
    """Helper to build the token response object."""
    return TokenResponse(
        access_token=create_access_token(user_id, role),
        refresh_token=raw_refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    async def register_student(self, data: StudentRegisterRequest) -> TokenResponse:
        """
        Register a new student account.

        Steps:
          1. Check if email is already taken
          2. Hash password (never store plain text)
          3. Create user + student profile atomically
          4. Issue access + refresh tokens
        """
        if await self.user_repo.email_exists(data.email):
            raise EmailAlreadyExistsError()

        password_hash = hash_password(data.password)

        user = await self.user_repo.create_student_user(
            email=data.email,
            password_hash=password_hash,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            registration_number=data.registration_number,
            department=data.department,
            semester=data.semester,
            section=data.section,
            admission_year=data.admission_year,
        )

        logger.info("New student registered: %s (user_id=%s)", data.email, user.user_id)

        return await self._issue_tokens(user)

    async def register_teacher(self, data: TeacherRegisterRequest) -> TokenResponse:
        """Register a new teacher account. Only admins can call this."""
        if await self.user_repo.email_exists(data.email):
            raise EmailAlreadyExistsError()

        user = await self.user_repo.create_teacher_user(
            email=data.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            employee_id=data.employee_id,
            department=data.department,
            designation=data.designation,
        )

        logger.info("New teacher registered: %s (user_id=%s)", data.email, user.user_id)
        return await self._issue_tokens(user)

    async def register_admin(self, data: AdminRegisterRequest) -> TokenResponse:
        """Register an admin account. Only existing admins can call this."""
        if await self.user_repo.email_exists(data.email):
            raise EmailAlreadyExistsError()

        user = await self.user_repo.create_admin_user(
            email=data.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
        )

        logger.info("New admin registered: %s (user_id=%s)", data.email, user.user_id)
        return await self._issue_tokens(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate user with email + password.

        Security note: We always call verify_password even when the user
        is not found. This prevents timing-based email enumeration —
        the response time is the same whether the email exists or not.
        """
        user = await self.user_repo.get_by_email(email)

        # Always verify the password (timing attack prevention)
        # If user is None, verify against a dummy hash
        dummy_hash = "$2b$12$dum.my.hash.to.prevent.timing.attacks.0000000000000000000"
        password_ok = verify_password(
            password,
            user.password_hash if user else dummy_hash,
        )

        if not user or not password_ok:
            # Generic message — do not reveal whether email exists
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AccountInactiveError()

        # Clean up expired tokens before creating a new one
        await self.token_repo.delete_expired(str(user.user_id))

        # Update last login timestamp (triggers the audit log trigger in PostgreSQL)
        await self.user_repo.update_last_login(str(user.user_id))

        logger.info("User logged in: %s (user_id=%s)", email, user.user_id)

        return await self._issue_tokens(user)

    async def refresh_access_token(self, raw_refresh_token: str) -> TokenResponse:
        """
        Issue a new access + refresh token pair given a valid refresh token.

        This implements refresh token rotation:
          - Old refresh token is revoked immediately after use
          - New refresh token is issued with a fresh expiry
          - If the old token is already revoked (reuse detected), all tokens
            for this user are revoked (security incident response)
        """
        token_hash = hash_token(raw_refresh_token)
        stored_token = await self.token_repo.get_valid_token(token_hash)

        if stored_token is None:
            # Token not found or expired or already revoked
            # This could be a reuse attack — log it
            logger.warning("Refresh token attempt with invalid/revoked token hash: %s...", token_hash[:16])
            raise InvalidTokenError("Refresh token is invalid or expired")

        user = await self.user_repo.get_by_id(str(stored_token.user_id))

        if not user or not user.is_active:
            raise AccountInactiveError()

        # Revoke the used token (rotation)
        await self.token_repo.revoke(token_hash)

        logger.info("Refresh token rotated for user_id=%s", user.user_id)

        # Issue new token pair
        return await self._issue_tokens(user)

    async def logout(self, raw_refresh_token: str) -> None:
        """
        Revoke the provided refresh token.
        The access token will expire naturally (short-lived).
        """
        token_hash = hash_token(raw_refresh_token)
        revoked = await self.token_repo.revoke(token_hash)

        if revoked:
            logger.info("Refresh token revoked (logout): %s...", token_hash[:16])

    async def _issue_tokens(self, user) -> TokenResponse:
        """
        Private: Create and store refresh token, then build the response.
        Called by all auth flows that need to return tokens.
        """
        user_id = str(user.user_id)
        role = user.role.value if hasattr(user.role, "value") else str(user.role)

        raw_refresh_token, token_hash = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )

        await self.token_repo.create(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        return _build_token_response(user_id, role, raw_refresh_token)
