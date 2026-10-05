from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.schemas.user_schema import UserResponse
from app.services.user_service import UserService
from app.services.auth_service import require_roles
from app.models.sql_models import User

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("", response_model=List[UserResponse])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(["ADMIN", "TEACHER"]))
):
    service = UserService(db)
    return service.list_all_users(skip=skip, limit=limit)
