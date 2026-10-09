from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.sql_models import User
from app.repositories.user_repo import UserRepository
from app.services.auth_service import hash_password, verify_password, create_access_token


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def register(self, email: str, password: str, full_name: str, role_name: str = "STUDENT") -> dict:
        existing = self.user_repo.get_user_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email '{email}' already exists"
            )

        role = self.user_repo.get_role_by_name(role_name)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_name}' is invalid"
            )

        hashed = hash_password(password)
        user = self.user_repo.create_user(
            email=email,
            password_hash=hashed,
            full_name=full_name,
            role_id=role.id
        )

        token = create_access_token({"sub": str(user.id), "role": role.name, "email": user.email})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": role.name,
                "is_active": user.is_active,
                "created_at": user.created_at
            }
        }

    def login(self, email: str, password: str) -> dict:
        user = self.user_repo.get_user_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )

        role_name = user.role.name if user.role else "STUDENT"
        token = create_access_token({"sub": str(user.id), "role": role_name, "email": user.email})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": role_name,
                "is_active": user.is_active,
                "created_at": user.created_at
            }
        }

    def list_all_users(self, skip: int = 0, limit: int = 100) -> List[dict]:
        users = self.user_repo.list_users(skip=skip, limit=limit)
        return [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.name if u.role else "STUDENT",
                "is_active": u.is_active,
                "created_at": u.created_at
            }
            for u in users
        ]

    def change_password(self, user_id: int, current_password: str, new_password: str) -> dict:
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        if len(new_password.strip()) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 6 characters long"
            )

        if current_password == new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password cannot be identical to current password"
            )

        hashed = hash_password(new_password)
        user.password_hash = hashed
        self.db.commit()
        return {"status": "SUCCESS", "message": "Password changed successfully"}
