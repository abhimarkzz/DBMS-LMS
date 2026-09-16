"""
Users Router — Self-service profile operations

Endpoints:
  GET   /api/v1/users/me           — Get own profile (alias for /auth/me)
  PATCH /api/v1/users/me           — Update own profile
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_any_authenticated
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get own profile",
)
async def get_my_profile(
    current_user=Depends(get_current_user),
):
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update own profile",
)
async def update_my_profile(
    data: UserUpdateRequest,
    current_user=Depends(get_current_user),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    Update the authenticated user's profile.
    Only first_name, last_name, and phone can be changed here.
    Email and role changes require admin operations.
    """
    service = UserService(db)
    return await service.update_profile(
        user_id=str(current_user.user_id),
        requesting_user_id=str(current_user.user_id),
        data=data,
    )
