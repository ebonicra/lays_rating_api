from datetime import datetime

from pydantic import BaseModel, Field

from app.models.user_role import UserRole


class UserCreate(BaseModel):
    """Регистрация нового пользователя"""
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6)
    display_name: str = Field(min_length=1, max_length=20)


class LoginRequest(BaseModel):
    """Вход в систему"""
    username: str
    password: str


class UserUpdate(BaseModel):
    """Обновление профиля"""
    display_name: str | None = Field(default=None, min_length=1, max_length=20)
    username: str | None = Field(default=None, min_length=3, max_length=20)


class UserResponse(BaseModel):
    """Публичная информация о пользователе"""
    id: int
    username: str
    display_name: str
    role: UserRole  # ← enum
    avatar_url: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Ответ после логина"""
    access_token: str
    token_type: str


class UserBriefResponse(BaseModel):
    """Краткая информация о пользователе (автор, подписчик, участник)"""
    id: int
    username: str
    display_name: str
    avatar_url: str | None = None

    class Config:
        from_attributes = True