from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.models.user_filter import UserFilter
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post("/register", response_model=UserResponse)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """ Регистрация нового пользователя """
    existing_user = db.query(User).filter(User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=data.username,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    for category in settings.DEFAULT_CATEGORIES:
        user_filter = UserFilter(
            user_id=user.id,
            category=category,
        )
        db.add(user_filter)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """ Вход в систему """
    user = db.query(User).filter(User.username == data.username).first()

    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"user_id": user.id})
    return {"access_token": token, "token_type": "bearer"}


# /auth/register  POST -  создаёт юзера + дефолтные фильтры
# /auth/login     POST -  проверяет пароль + возвращает JWT