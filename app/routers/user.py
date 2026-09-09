from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from fastapi.responses import FileResponse

import os
import uuid
from app.database import get_db

from app.models.user import User
from app.models.user_category import UserCategory
from app.schemas.user import UserCreate, UserResponse, TokenResponse, LoginRequest, UserUpdate

from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.core.constants import DEFAULT_CATEGORIES

# Папка для аватарок
AVATARS_DIR = "uploads/avatars"
os.makedirs(AVATARS_DIR, exist_ok=True)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


# ===== АУТЕНТИФИКАЦИЯ =====

@router.post("/register", response_model=UserResponse)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
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

    # Добавляем дефолтные категории
    for category in DEFAULT_CATEGORIES:
        preference = UserCategory(
            user_id=user.id,
            category=category,
        )
        db.add(preference)
    db.commit()
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Вход в систему"""
    user = db.query(User).filter(User.username == data.username).first()
    
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"user_id": user.id})
    return {"access_token": token, "token_type": "bearer"}


# ===== ПРОФИЛЬ =====

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Получить свой профиль"""
    return current_user


@router.put("/me")
def update_profile(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить имя и username"""
    
    if data.display_name is not None:
        current_user.display_name = data.display_name
    
    if data.username is not None:
        # Проверяем, что username не занят
        existing = db.query(User).filter(
            User.username == data.username,
            User.id != current_user.id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username уже занят")
        current_user.username = data.username
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "display_name": current_user.display_name,
        "is_admin": current_user.is_admin,
        "avatar_url": f"/users/avatars/{current_user.avatar_path}" if current_user.avatar_path else None,
        "created_at": current_user.created_at,
    }


# ===== АВАТАРКИ =====

@router.get("/avatars/{filename}")
def get_avatar(filename: str):
    """Получить аватарку по имени файла"""
    filepath = os.path.join(AVATARS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return FileResponse(filepath)


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Загрузить аватарку"""
    print(f"Получен файл: {file.filename}, тип: {file.content_type}")
    
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    allowed_extensions = ["jpg", "jpeg", "png", "webp"]
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Допустимы только JPEG, PNG, WebP. Получен: .{ext}"
        )
    
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс 5 МБ)")
    
    # Удаляем старую аватарку
    if current_user.avatar_path:
        old_path = os.path.join(AVATARS_DIR, current_user.avatar_path)
        if os.path.exists(old_path):
            os.remove(old_path)
    
    filename = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(AVATARS_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(contents)
    
    current_user.avatar_path = filename
    db.commit()
    
    return {"avatar_path": filename}


@router.delete("/me/avatar")
def delete_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Удалить аватарку"""
    if current_user.avatar_path:
        filepath = os.path.join(AVATARS_DIR, current_user.avatar_path)
        if os.path.exists(filepath):
            os.remove(filepath)
    
    current_user.avatar_path = None
    db.commit()
    return {"message": "Аватарка удалена"}


# ===== ПУБЛИЧНЫЙ ПРОФИЛЬ (ПОСЛЕДНИЙ!) =====

@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить публичный профиль пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
        "avatar_url": f"/users/avatars/{user.avatar_path}" if user.avatar_path else None,
        "created_at": user.created_at,
    }