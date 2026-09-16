"""
User Repository — Database Access Layer

All PostgreSQL queries for the user service go through here.
The repository pattern keeps SQL away from business logic.

Conventions:
  - All methods are async (use `await`)
  - Methods return ORM objects or None (never raise for "not found")
  - The caller (service layer) decides what to do when a record is missing
  - Queries use explicit SELECT columns where performance matters,
    full ORM loading for simple CRUD
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import RefreshToken, Student, Teacher, User, UserRoleAssignment

logger = logging.getLogger(__name__)


class UserRepository:
    """Handles all database operations related to users."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Load a user by UUID with their student/teacher profile eagerly loaded.
        Eager loading avoids N+1 queries when the caller accesses the profile.
        """
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.student_profile),
                selectinload(User.teacher_profile),
            )
            .where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Load a user by email address. Case-insensitive (email is lowercased in DB)."""
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.student_profile),
                selectinload(User.teacher_profile),
            )
            .where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Quick check without loading the full user object."""
        result = await self.db.execute(
            select(func.count()).where(func.lower(User.email) == email.lower())
        )
        return result.scalar() > 0

    async def create_student_user(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        phone: Optional[str],
        registration_number: str,
        department: str,
        semester: int,
        section: Optional[str],
        admission_year: int,
    ) -> User:
        """
        Create a student user and their student profile in a single transaction.
        Both records are created atomically — we never end up with a user
        without a profile.
        """
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role="STUDENT",
        )
        self.db.add(user)
        await self.db.flush()  # Flush to generate user_id without committing

        student = Student(
            user_id=user.user_id,
            registration_number=registration_number,
            department=department,
            semester=semester,
            section=section,
            admission_year=admission_year,
        )
        self.db.add(student)
        await self.db.flush()

        # Reload with profile to return a complete object
        return await self.get_by_id(str(user.user_id))

    async def create_teacher_user(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        phone: Optional[str],
        employee_id: str,
        department: str,
        designation: str,
    ) -> User:
        """Create a teacher user and their teacher profile atomically."""
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role="TEACHER",
        )
        self.db.add(user)
        await self.db.flush()

        teacher = Teacher(
            user_id=user.user_id,
            employee_id=employee_id,
            department=department,
            designation=designation,
        )
        self.db.add(teacher)
        await self.db.flush()

        return await self.get_by_id(str(user.user_id))

    async def create_admin_user(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        phone: Optional[str],
    ) -> User:
        """Create an admin user (no profile sub-table)."""
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role="ADMIN",
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update_last_login(self, user_id: str) -> None:
        """Record login timestamp. This also fires the audit trigger in PostgreSQL."""
        await self.db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )

    async def update_profile(
        self,
        user_id: str,
        first_name: Optional[str],
        last_name: Optional[str],
        phone: Optional[str],
    ) -> Optional[User]:
        """Update user's basic profile fields. Only updates fields that are provided."""
        update_values = {}
        if first_name is not None:
            update_values["first_name"] = first_name
        if last_name is not None:
            update_values["last_name"] = last_name
        if phone is not None:
            update_values["phone"] = phone

        if not update_values:
            return await self.get_by_id(user_id)  # No changes needed

        update_values["updated_at"] = datetime.now(timezone.utc)

        await self.db.execute(
            update(User).where(User.user_id == user_id).values(**update_values)
        )

        return await self.get_by_id(user_id)

    async def set_active_status(self, user_id: str, is_active: bool) -> Optional[User]:
        """Admin operation: activate or deactivate a user account."""
        await self.db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(is_active=is_active, updated_at=datetime.now(timezone.utc))
        )
        return await self.get_by_id(user_id)

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[User], int]:
        """
        Paginated user list for admin endpoint.
        Returns (list_of_users, total_count).
        """
        query = select(User).options(
            selectinload(User.student_profile),
            selectinload(User.teacher_profile),
        )

        if role:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        # Total count (without pagination)
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Paginated results
        query = query.order_by(User.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        users = result.scalars().all()

        return list(users), total


class RefreshTokenRepository:
    """Handles refresh token storage, validation, and revocation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
    ) -> RefreshToken:
        """Store a new refresh token hash."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=device_info,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_valid_token(self, token_hash: str) -> Optional[RefreshToken]:
        """
        Find a refresh token by its hash.
        Returns None if the token does not exist, is revoked, or has expired.
        """
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.revoked == False,  # noqa: E712
                    RefreshToken.expires_at > now,
                )
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, token_hash: str) -> bool:
        """
        Revoke a specific refresh token (logout).
        Returns True if the token was found and revoked.
        """
        result = await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(revoked=True, revoked_at=datetime.now(timezone.utc))
        )
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: str) -> int:
        """
        Revoke all active refresh tokens for a user.
        Used when: password changed, account deactivated, security breach.
        Returns the count of revoked tokens.
        """
        result = await self.db.execute(
            update(RefreshToken)
            .where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked == False,  # noqa: E712
                )
            )
            .values(revoked=True, revoked_at=datetime.now(timezone.utc))
        )
        return result.rowcount

    async def delete_expired(self, user_id: str) -> None:
        """
        Clean up expired tokens for a user to keep the table small.
        Called lazily during login (before creating a new token).
        """
        from sqlalchemy import delete

        now = datetime.now(timezone.utc)
        await self.db.execute(
            delete(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.expires_at < now,
                )
            )
        )
