from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func

from fastapi.responses import FileResponse

import os
import uuid
from app.database import get_db

from app.models.user import User
from app.models.user_category import UserCategory
from app.models.chip_preference import ChipPreference
from app.models.chip_comment import ChipComment
from app.models.follow import Follow
from app.schemas.user import UserCreate, UserResponse, TokenResponse, LoginRequest
from app.schemas.follow import UserBriefResponse
from app.schemas.user import UserUpdate

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


def _get_user_brief(user: User) -> UserBriefResponse:
    """Преобразовать User в краткую информацию"""
    return UserBriefResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=f"/users/avatars/{user.avatar_path}" if user.avatar_path else None,
    )


# ===== АУТЕНТИФИКАЦИЯ =====

@router.post("/register", response_model=UserResponse)
def register(data: UserCreate, db: Session = Depends(get_db)):
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
    user = db.query(User).filter(User.username == data.username).first()
    
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"user_id": user.id})
    return {"access_token": token, "token_type": "bearer"}


# ===== ТЕКУЩИЙ ПОЛЬЗОВАТЕЛЬ =====

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


#Обновить имя и username
@router.put("/me")
def update_profile(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
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

@router.get("/me/stats")
def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):    
    ratings_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == current_user.id,
        ChipPreference.rating.isnot(None),
    ).scalar() or 0
    
    favorites_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == current_user.id,
        ChipPreference.is_favorite == True,
    ).scalar() or 0
    
    tried_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == current_user.id,
        ChipPreference.is_tried == True,
    ).scalar() or 0
    
    comments_count = db.query(func.count(ChipComment.id)).filter(
        ChipComment.user_id == current_user.id
    ).scalar() or 0
    
    avg_rating = db.query(func.avg(ChipPreference.rating)).filter(
        ChipPreference.user_id == current_user.id,
        ChipPreference.rating.isnot(None),
    ).scalar()

    followers_count = db.query(func.count(Follow.id)).filter(
        Follow.following_id == current_user.id
    ).scalar() or 0
    
    following_count = db.query(func.count(Follow.id)).filter(
        Follow.follower_id == current_user.id
    ).scalar() or 0
    
    return {
        "ratings_count": ratings_count,
        "favorites_count": favorites_count,
        "tried_count": tried_count,
        "comments_count": comments_count,
        "average_rating": round(float(avg_rating), 1) if avg_rating else 0.0,
        "followers_count": followers_count,
        "following_count": following_count,
    }


# ===== АВАТАРКИ =====

@router.get("/avatars/{filename}")
def get_avatar(filename: str):
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
    if current_user.avatar_path:
        filepath = os.path.join(AVATARS_DIR, current_user.avatar_path)
        if os.path.exists(filepath):
            os.remove(filepath)
    
    current_user.avatar_path = None
    db.commit()
    return {"message": "Аватарка удалена"}


# ===== ПОИСК И СПИСКИ (ДО /{user_id}!) =====

@router.get("/search")
def search_users(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    users = (
        db.query(User)
        .filter(
            User.username.ilike(f"%{q}%"),
            User.id != current_user.id,
        )
        .limit(20)
        .all()
    )
    return [_get_user_brief(u) for u in users]


@router.get("/list")
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    users = (
        db.query(User)
        .filter(User.id != current_user.id)
        .order_by(User.username)
        .all()
    )
    return [_get_user_brief(u) for u in users]


# ===== ПУБЛИЧНЫЙ ПРОФИЛЬ (ПОСЛЕДНИЙ!) =====

@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
        "avatar_url": f"/users/avatars/{user.avatar_path}" if user.avatar_path else None,
    }

#Публичная статистика пользователя"""
@router.get("/{user_id}/stats")
def get_public_user_stats(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    ratings_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == user_id,
        ChipPreference.rating.isnot(None),
    ).scalar() or 0
    
    favorites_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == user_id,
        ChipPreference.is_favorite == True,
    ).scalar() or 0
    
    tried_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == user_id,
        ChipPreference.is_tried == True,
    ).scalar() or 0
    
    comments_count = db.query(func.count(ChipComment.id)).filter(
        ChipComment.user_id == user_id
    ).scalar() or 0
    
    avg_rating = db.query(func.avg(ChipPreference.rating)).filter(
        ChipPreference.user_id == user_id,
        ChipPreference.rating.isnot(None),
    ).scalar()
    
    followers_count = db.query(func.count(Follow.id)).filter(
        Follow.following_id == user_id
    ).scalar() or 0
    
    following_count = db.query(func.count(Follow.id)).filter(
        Follow.follower_id == user_id
    ).scalar() or 0
    
    return {
        "ratings_count": ratings_count,
        "favorites_count": favorites_count,
        "tried_count": tried_count,
        "comments_count": comments_count,
        "average_rating": round(float(avg_rating), 1) if avg_rating else 0.0,
        "followers_count": followers_count,
        "following_count": following_count,
    }