"""
Pydantic Schemas — Request and Response Models

These define the API contract: what data comes in, what goes out.
They are completely separate from SQLAlchemy models.

Rules:
  - Never include password_hash in response schemas
  - Validate email format at the Pydantic level (DB has a backup constraint)
  - Use Optional fields for partial update payloads (PATCH semantics)
  - Use clear field descriptions for OpenAPI documentation
"""

import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---- Student and Teacher profile schemas ----

class StudentProfileResponse(BaseModel):
    student_id: UUID
    registration_number: str
    department: str
    semester: int
    section: Optional[str] = None
    admission_year: int

    model_config = {"from_attributes": True}


class TeacherProfileResponse(BaseModel):
    teacher_id: UUID
    employee_id: str
    department: str
    designation: str

    model_config = {"from_attributes": True}


# ---- Core User response ----

class UserResponse(BaseModel):
    """Safe user representation — never exposes password_hash."""
    user_id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    # Nested profiles (present only for STUDENT or TEACHER roles)
    student_profile: Optional[StudentProfileResponse] = None
    teacher_profile: Optional[TeacherProfileResponse] = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated list of users for admin endpoint."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


# ---- User update ----

class UserUpdateRequest(BaseModel):
    """
    PATCH payload for updating user profile.
    All fields are optional — only provided fields are updated.
    """
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class AdminUserStatusUpdate(BaseModel):
    """Admin-only: activate or deactivate a user account."""
    is_active: bool


# ---- Registration schemas ----

class _BaseRegistrationRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, value: str) -> str:
        """
        Enforce a minimum password policy:
        - At least 8 characters (enforced by min_length above)
        - At least one uppercase letter
        - At least one digit
        """
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit")
        return value


class StudentRegisterRequest(_BaseRegistrationRequest):
    """Registration payload for student accounts."""
    registration_number: str = Field(min_length=3, max_length=50)
    department: str = Field(min_length=2, max_length=100)
    semester: int = Field(ge=1, le=12)
    section: Optional[str] = Field(None, max_length=10)
    admission_year: int = Field(ge=1990, le=2100)


class TeacherRegisterRequest(_BaseRegistrationRequest):
    """Registration payload for teacher accounts (admin creates these)."""
    employee_id: str = Field(min_length=3, max_length=50)
    department: str = Field(min_length=2, max_length=100)
    designation: str = Field(
        default="Assistant Professor", min_length=2, max_length=100
    )


class AdminRegisterRequest(_BaseRegistrationRequest):
    """Registration payload for admin accounts (existing admin creates these)."""
    pass
