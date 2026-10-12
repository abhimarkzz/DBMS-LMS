from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.models.sql_models import User, Role


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_role_by_name(self, name: str) -> Optional[Role]:
        return self.db.query(Role).filter(Role.name == name.upper()).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).options(joinedload(User.role)).filter(User.email == email.lower()).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).options(joinedload(User.role)).filter(User.id == user_id).first()

    def create_user(self, email: str, password_hash: str, full_name: str, role_id: int) -> User:
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash,
            full_name=full_name.strip(),
            role_id=role_id,
            is_active=True
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        return self.db.query(User).options(joinedload(User.role)).offset(skip).limit(limit).all()

    def count_users(self) -> int:
        return self.db.query(User).count()
