"""
Test Configuration and Fixtures

Uses an in-memory SQLite database for fast, isolated tests.
Each test function gets a fresh database session — tests are independent.

FastAPI's TestClient is used synchronously; async tests use httpx.AsyncClient.
"""

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Point to a test environment before importing the app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test_db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("JWT_SECRET", "test-secret-key-that-is-at-least-32-characters-long")
os.environ.setdefault("APP_ENV", "test")

from app.core.dependencies import get_db
from app.main import app
from app.models.user import Base

# In-memory SQLite for tests — no Docker required, fast teardown
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create fresh tables for each test, then tear them down."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP test client with the test database injected via dependency override.
    Use this fixture to make API calls in tests.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared test data helpers
# ---------------------------------------------------------------------------

STUDENT_REGISTER_DATA = {
    "email": "teststudent@example.com",
    "password": "TestPass@123",
    "first_name": "Test",
    "last_name": "Student",
    "phone": "9000000099",
    "registration_number": "CSE2024TEST",
    "department": "Computer Science and Engineering",
    "semester": 3,
    "section": "A",
    "admission_year": 2024,
}

TEACHER_REGISTER_DATA = {
    "email": "testteacher@example.com",
    "password": "TestPass@123",
    "first_name": "Test",
    "last_name": "Teacher",
    "employee_id": "EMP-TEST-001",
    "department": "Computer Science and Engineering",
    "designation": "Assistant Professor",
}

ADMIN_REGISTER_DATA = {
    "email": "testadmin@example.com",
    "password": "TestPass@123",
    "first_name": "Test",
    "last_name": "Admin",
}
