"""
Admin Router — User management for administrators

Endpoints:
  GET   /api/v1/admin/users                    — List all users (paginated)
  GET   /api/v1/admin/users/{user_id}          — Get any user's profile
  PATCH /api/v1/admin/users/{user_id}/status   — Activate/deactivate account
"""

import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin
from app.schemas.user import AdminUserStatusUpdate, UserListResponse, UserResponse
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List all users",
    dependencies=[Depends(require_admin)],
)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    role: Optional[str] = Query(default=None, description="Filter by role: STUDENT, TEACHER, ADMIN"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
):
    """
    Admin-only: List all users with optional role and status filters.
    Supports pagination.
    """
    service = UserService(db)
    return await service.list_users(
        page=page,
        page_size=page_size,
        role=role,
        is_active=is_active,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get any user's profile",
    dependencies=[Depends(require_admin)],
)
async def get_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin-only: Look up any user's full profile by UUID."""
    service = UserService(db)
    return await service.get_profile(str(user_id))


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
    summary="Activate or deactivate a user account",
    dependencies=[Depends(require_admin)],
)
async def set_user_status(
    user_id: UUID,
    data: AdminUserStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Admin-only: Activate or deactivate a user account.
    Deactivated users cannot log in and their active tokens become invalid
    on the next request (checked in get_current_user dependency).
    """
    service = UserService(db)
    return await service.set_user_active_status(str(user_id), data.is_active)
