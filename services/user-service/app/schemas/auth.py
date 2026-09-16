"""
Pydantic Schemas — Authentication

Request and response shapes for login, token refresh, and logout.
"""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Returned after successful login or token refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token lifetime in seconds


class RefreshTokenRequest(BaseModel):
    """Client sends the refresh token to get a new access token."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """
    Client sends their refresh token on logout so we can revoke it.
    The access token will expire naturally (short TTL).
    """
    refresh_token: str


class MessageResponse(BaseModel):
    """Generic success message response."""
    message: str
    success: bool = True
