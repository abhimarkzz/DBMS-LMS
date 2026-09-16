"""
User Service — Profile Management Business Logic

Handles:
  - Fetching user profile (current user and admin lookups)
  - Updating profile fields
  - Admin operations (activate/deactivate accounts, list users)
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError, UserNotFoundError
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserListResponse, UserResponse, UserUpdateRequest

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def get_profile(self, user_id: str) -> UserResponse:
        """
        Return the full profile for a given user ID.
        Includes student or teacher sub-profile if present.
        """
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        return UserResponse.model_validate(user)

    async def update_profile(
        self,
        user_id: str,
        requesting_user_id: str,
        data: UserUpdateRequest,
    ) -> UserResponse:
        """
        Update a user's profile fields.

        Authorization rule:
          - A user can only update their own profile
          - Admins can update any profile (handled in the router by passing
            requesting_user_id == user_id for self-update, or admin's ID)

        We check this in the service, not only the router, so the rule is
        enforced even if called from another service in future.
        """
        if user_id != requesting_user_id:
            raise PermissionDeniedError("You can only update your own profile")

        user = await self.repo.update_profile(
            user_id=user_id,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
        )

        if user is None:
            raise UserNotFoundError()

        logger.info("Profile updated for user_id=%s", user_id)
        return UserResponse.model_validate(user)

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> UserListResponse:
        """Admin endpoint: paginated user list with optional filters."""
        users, total = await self.repo.list_users(
            page=page,
            page_size=page_size,
            role=role,
            is_active=is_active,
        )

        return UserListResponse(
            users=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def set_user_active_status(
        self, user_id: str, is_active: bool
    ) -> UserResponse:
        """Admin operation: activate or deactivate a user account."""
        user = await self.repo.set_active_status(user_id, is_active)

        if user is None:
            raise UserNotFoundError()

        action = "activated" if is_active else "deactivated"
        logger.info("User account %s: user_id=%s", action, user_id)

        return UserResponse.model_validate(user)
