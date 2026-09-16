"""
Authentication Router

Endpoints:
  POST /api/v1/auth/register/student  — Register a student (public)
  POST /api/v1/auth/register/teacher  — Register a teacher (admin only)
  POST /api/v1/auth/register/admin    — Register an admin (admin only)
  POST /api/v1/auth/login             — Login, receive JWT pair
  POST /api/v1/auth/refresh           — Refresh access token
  POST /api/v1/auth/logout            — Revoke refresh token
  GET  /api/v1/auth/me                — Get current user profile
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    get_db,
    login_rate_limit,
    register_rate_limit,
    require_admin,
)
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.user import (
    AdminRegisterRequest,
    StudentRegisterRequest,
    TeacherRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/register/student",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
    dependencies=[Depends(register_rate_limit)],
)
async def register_student(
    data: StudentRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Open endpoint — any visitor can register as a student.

    Returns JWT tokens on success so the student is immediately logged in.
    Rate limited to prevent registration spam.
    """
    service = AuthService(db)
    return await service.register_student(data)


@router.post(
    "/register/teacher",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new teacher account (Admin only)",
)
async def register_teacher(
    data: TeacherRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin=Depends(require_admin),
):
    """
    Admin-only: Create a teacher account.
    Teachers are added by an admin, not via public self-registration.
    """
    service = AuthService(db)
    return await service.register_teacher(data)


@router.post(
    "/register/admin",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new admin account (Admin only)",
)
async def register_admin(
    data: AdminRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin=Depends(require_admin),
):
    """Admin-only: Create another admin account."""
    service = AuthService(db)
    return await service.register_admin(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    dependencies=[Depends(login_rate_limit)],
)
async def login(
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Returns an access token (short-lived, 60 min) and a refresh token
    (long-lived, 7 days).

    The access token should be stored in memory only.
    The refresh token should be stored in an HttpOnly cookie by the client.
    """
    service = AuthService(db)
    return await service.login(data.email, data.password)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    The old refresh token is revoked (token rotation).

    Call this when the access token expires (401 response) to get a new one
    without requiring the user to re-login.
    """
    service = AuthService(db)
    return await service.refresh_access_token(data.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (revoke refresh token)",
)
async def logout(
    data: LogoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Revoke the provided refresh token.
    The access token will expire on its own (short TTL).

    The client should also delete its locally stored tokens.
    """
    service = AuthService(db)
    await service.logout(data.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_current_user_profile(
    current_user=Depends(get_current_user),
):
    """
    Returns the full profile of the currently authenticated user.
    Includes student or teacher sub-profile if applicable.
    """
    return UserResponse.model_validate(current_user)
