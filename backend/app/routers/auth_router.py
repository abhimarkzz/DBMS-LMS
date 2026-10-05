from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.schemas.user_schema import UserRegister, UserLogin, TokenResponse, UserResponse
from app.services.user_service import UserService
from app.services.auth_service import get_current_user
from app.services.notification_service import NotificationService
from app.models.sql_models import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    service = UserService(db)
    res = service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role_name=payload.role
    )
    # Log registration in MongoDB
    await NotificationService.log_activity(
        user_id=res["user"]["id"],
        user_name=res["user"]["full_name"],
        action="USER_REGISTERED",
        details=f"Registered as {res['user']['role']}"
    )
    return res


@router.post("/login", response_model=TokenResponse)
async def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    service = UserService(db)
    res = service.login(email=payload.email, password=payload.password)
    # Log login in MongoDB
    await NotificationService.log_activity(
        user_id=res["user"]["id"],
        user_name=res["user"]["full_name"],
        action="USER_LOGIN",
        details=f"Logged in as {res['user']['role']}"
    )
    return res


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.name if current_user.role else "STUDENT",
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }
