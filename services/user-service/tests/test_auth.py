"""
Tests — Authentication Endpoints

Covers: registration, login, token refresh, logout, /me endpoint
"""

import pytest
from httpx import AsyncClient

from tests.conftest import STUDENT_REGISTER_DATA


pytestmark = pytest.mark.asyncio


class TestStudentRegistration:
    """POST /api/v1/auth/register/student"""

    async def test_register_student_success(self, client: AsyncClient):
        """Happy path: valid data returns 201 with tokens."""
        response = await client.post(
            "/api/v1/auth/register/student",
            json=STUDENT_REGISTER_DATA,
        )
        assert response.status_code == 201

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_register_student_duplicate_email(self, client: AsyncClient):
        """Duplicate email should return 409 Conflict."""
        await client.post("/api/v1/auth/register/student", json=STUDENT_REGISTER_DATA)

        # Second registration with same email
        response = await client.post(
            "/api/v1/auth/register/student",
            json=STUDENT_REGISTER_DATA,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    async def test_register_student_weak_password_no_uppercase(self, client: AsyncClient):
        """Password without uppercase letter should fail validation."""
        data = {**STUDENT_REGISTER_DATA, "password": "weakpass123"}
        response = await client.post("/api/v1/auth/register/student", json=data)
        assert response.status_code == 422

    async def test_register_student_weak_password_no_digit(self, client: AsyncClient):
        """Password without digit should fail validation."""
        data = {**STUDENT_REGISTER_DATA, "password": "WeakPasswordOnly"}
        response = await client.post("/api/v1/auth/register/student", json=data)
        assert response.status_code == 422

    async def test_register_student_invalid_email(self, client: AsyncClient):
        """Invalid email format should return 422."""
        data = {**STUDENT_REGISTER_DATA, "email": "not-an-email"}
        response = await client.post("/api/v1/auth/register/student", json=data)
        assert response.status_code == 422

    async def test_register_student_missing_required_field(self, client: AsyncClient):
        """Missing registration_number should return 422."""
        data = {k: v for k, v in STUDENT_REGISTER_DATA.items() if k != "registration_number"}
        response = await client.post("/api/v1/auth/register/student", json=data)
        assert response.status_code == 422

    async def test_register_student_invalid_semester(self, client: AsyncClient):
        """Semester < 1 should fail validation."""
        data = {**STUDENT_REGISTER_DATA, "semester": 0}
        response = await client.post("/api/v1/auth/register/student", json=data)
        assert response.status_code == 422


class TestLogin:
    """POST /api/v1/auth/login"""

    async def _register_student(self, client: AsyncClient) -> dict:
        """Helper: register and return credentials."""
        await client.post("/api/v1/auth/register/student", json=STUDENT_REGISTER_DATA)
        return {
            "email": STUDENT_REGISTER_DATA["email"],
            "password": STUDENT_REGISTER_DATA["password"],
        }

    async def test_login_success(self, client: AsyncClient):
        """Valid credentials return 200 with token pair."""
        credentials = await self._register_student(client)

        response = await client.post("/api/v1/auth/login", json=credentials)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client: AsyncClient):
        """Wrong password returns 401 with AUTHENTICATION_FAILED code."""
        await self._register_student(client)

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": STUDENT_REGISTER_DATA["email"], "password": "WrongPass@999"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    async def test_login_non_existent_email(self, client: AsyncClient):
        """
        Non-existent email should return 401 — same as wrong password.
        The error message must NOT reveal whether the email exists.
        """
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "TestPass@123"},
        )
        assert response.status_code == 401
        # Verify the error message does NOT say "email not found"
        error_msg = response.json()["error"]["message"].lower()
        assert "email" not in error_msg or "password" in error_msg

    async def test_login_returns_consistent_error_for_wrong_credentials(
        self, client: AsyncClient
    ):
        """Wrong email and wrong password should return identical error shapes."""
        wrong_email_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "TestPass@123"},
        )
        await self._register_student(client)
        wrong_password_response = await client.post(
            "/api/v1/auth/login",
            json={"email": STUDENT_REGISTER_DATA["email"], "password": "Wrong@999"},
        )

        # Both should be 401 with the same error code
        assert wrong_email_response.status_code == wrong_password_response.status_code == 401
        assert (
            wrong_email_response.json()["error"]["code"]
            == wrong_password_response.json()["error"]["code"]
        )


class TestTokenRefresh:
    """POST /api/v1/auth/refresh"""

    async def _get_tokens(self, client: AsyncClient) -> dict:
        await client.post("/api/v1/auth/register/student", json=STUDENT_REGISTER_DATA)
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": STUDENT_REGISTER_DATA["email"],
                "password": STUDENT_REGISTER_DATA["password"],
            },
        )
        return login_resp.json()

    async def test_refresh_success(self, client: AsyncClient):
        """Valid refresh token returns new access + refresh tokens."""
        tokens = await self._get_tokens(client)

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 200
        new_tokens = response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

    async def test_refresh_rotates_token(self, client: AsyncClient):
        """New refresh token is different from the old one (rotation)."""
        tokens = await self._get_tokens(client)
        old_refresh = tokens["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        new_tokens = response.json()
        assert new_tokens["refresh_token"] != old_refresh

    async def test_refresh_token_cannot_be_reused(self, client: AsyncClient):
        """After rotation, the old refresh token must be invalid."""
        tokens = await self._get_tokens(client)
        old_refresh = tokens["refresh_token"]

        # Use the refresh token once
        await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})

        # Try to use it again — should fail
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert response.status_code == 401

    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Completely fake token returns 401."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "this-is-not-a-real-token"},
        )
        assert response.status_code == 401


class TestLogout:
    """POST /api/v1/auth/logout"""

    async def test_logout_success(self, client: AsyncClient):
        """Logout with valid refresh token returns 200."""
        await client.post("/api/v1/auth/register/student", json=STUDENT_REGISTER_DATA)
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": STUDENT_REGISTER_DATA["email"],
                "password": STUDENT_REGISTER_DATA["password"],
            },
        )
        tokens = login_resp.json()

        response = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_refresh_fails_after_logout(self, client: AsyncClient):
        """Cannot use refresh token after logging out."""
        await client.post("/api/v1/auth/register/student", json=STUDENT_REGISTER_DATA)
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": STUDENT_REGISTER_DATA["email"],
                "password": STUDENT_REGISTER_DATA["password"],
            },
        )
        tokens = login_resp.json()

        # Logout
        await client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})

        # Try to refresh — must fail
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 401


class TestGetMe:
    """GET /api/v1/auth/me"""

    async def test_get_me_success(self, client: AsyncClient):
        """Authenticated request returns user profile."""
        reg_resp = await client.post(
            "/api/v1/auth/register/student", json=STUDENT_REGISTER_DATA
        )
        token = reg_resp.json()["access_token"]

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        me = response.json()
        assert me["email"] == STUDENT_REGISTER_DATA["email"]
        assert me["role"] == "STUDENT"
        assert "password_hash" not in me
        assert me["student_profile"] is not None
        assert me["student_profile"]["registration_number"] == STUDENT_REGISTER_DATA["registration_number"]

    async def test_get_me_without_token(self, client: AsyncClient):
        """No Authorization header returns 401."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        """Tampered token returns 401."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken123"},
        )
        assert response.status_code == 401
