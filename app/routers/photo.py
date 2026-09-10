import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.user_photo import UserPhoto
from app.models.photo_reaction import PhotoReaction
from app.schemas.photo import (
    UserPhotoResponse,
    PhotoListResponse,
    PhotoLikersResponse,
    PhotoReactionResponse,
    PhotoAuthorResponse,
)
from app.core.dependencies import get_current_user


BASE_DIR = Path(__file__).resolve().parent.parent
PHOTOS_DIR = BASE_DIR / "uploads" / "user_photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

MAX_PHOTOS_PER_USER = 20


router = APIRouter(
    prefix="/photos",
    tags=["Photos"]
)


def _photo_to_response(
    db: Session,
    photo: UserPhoto,
    current_user_id: int,
) -> UserPhotoResponse:
    """Преобразовать модель фото в ответ"""
    
    is_liked = (
        db.query(PhotoReaction)
        .filter(
            PhotoReaction.photo_id == photo.id,
            PhotoReaction.user_id == current_user_id,
        )
        .first()
        is not None
    )

    return UserPhotoResponse(
        id=photo.id,
        user=PhotoAuthorResponse(
            id=photo.user.id,
            username=photo.user.username,
            display_name=photo.user.display_name,
            avatar_url=f"/users/avatars/{photo.user.avatar_path}" if photo.user.avatar_path else None,
        ),
        image_path=photo.image_path,
        likes_count=photo.likes_count,
        is_liked=is_liked,
        created_at=photo.created_at,
    )


@router.get("/user/{user_id}", response_model=PhotoListResponse)
def get_user_photos(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить все фото пользователя"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    photos = (
        db.query(UserPhoto)
        .filter(UserPhoto.user_id == user_id)
        .order_by(UserPhoto.created_at.desc())
        .all()
    )
    
    return PhotoListResponse(
        photos=[_photo_to_response(db, p, current_user.id) for p in photos],
        total_count=len(photos),
    )


@router.post("/upload", response_model=UserPhotoResponse)
async def upload_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Загрузить фото"""
    
    # Проверяем лимит
    photo_count = (
        db.query(UserPhoto)
        .filter(UserPhoto.user_id == current_user.id)
        .count()
    )
    
    if photo_count >= MAX_PHOTOS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Максимум {MAX_PHOTOS_PER_USER} фото"
        )
    
    # Проверяем формат
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "jpg"
    allowed = ["jpg", "jpeg", "png", "webp"]
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Допустимы только JPEG, PNG, WebP")
    
    # Проверяем размер
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс 5 МБ)")
    
    # Сохраняем файл
    filename = f"photo_{current_user.id}_{uuid.uuid4().hex}.{ext}"
    filepath = PHOTOS_DIR / filename
    
    with open(filepath, "wb") as f:
        f.write(contents)
    
    # Создаём запись в БД
    photo = UserPhoto(
        user_id=current_user.id,
        image_path=filename,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    
    return _photo_to_response(db, photo, current_user.id)


@router.delete("/{photo_id}")
def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Удалить своё фото"""
    
    photo = db.query(UserPhoto).filter(UserPhoto.id == photo_id).first()
    if photo is None:
        raise HTTPException(status_code=404, detail="Фото не найдено")
    
    if photo.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Можно удалять только свои фото")
    
    # Удаляем файл
    filepath = PHOTOS_DIR / photo.image_path
    if filepath.exists():
        filepath.unlink()
    
    db.delete(photo)
    db.commit()
    
    return {"message": "Фото удалено"}


@router.post("/{photo_id}/like", response_model=PhotoReactionResponse)
def toggle_like(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Поставить/убрать лайк"""
    
    photo = db.query(UserPhoto).filter(UserPhoto.id == photo_id).first()
    if photo is None:
        raise HTTPException(status_code=404, detail="Фото не найдено")
    
    existing = (
        db.query(PhotoReaction)
        .filter(
            PhotoReaction.photo_id == photo_id,
            PhotoReaction.user_id == current_user.id,
        )
        .first()
    )
    
    if existing:
        # Убираем лайк
        db.delete(existing)
        photo.likes_count = max(0, photo.likes_count - 1)
        is_liked = False
    else:
        # Ставим лайк
        reaction = PhotoReaction(
            user_id=current_user.id,
            photo_id=photo_id,
        )
        db.add(reaction)
        photo.likes_count += 1
        is_liked = True
    
    db.commit()
    
    return PhotoReactionResponse(
        is_liked=is_liked,
        likes_count=photo.likes_count,
    )


@router.get("/{photo_id}/likes", response_model=PhotoLikersResponse)
def get_photo_likers(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить список тех, кто лайкнул фото"""
    
    photo = db.query(UserPhoto).filter(UserPhoto.id == photo_id).first()
    if photo is None:
        raise HTTPException(status_code=404, detail="Фото не найдено")
    
    reactions = (
        db.query(PhotoReaction)
        .filter(PhotoReaction.photo_id == photo_id)
        .order_by(PhotoReaction.created_at.desc())
        .all()
    )
    
    return PhotoLikersResponse(
        users=[
            PhotoAuthorResponse(
                id=r.user.id,
                username=r.user.username,
                display_name=r.user.display_name,
                avatar_url=f"/users/avatars/{r.user.avatar_path}" if r.user.avatar_path else None,
            )
            for r in reactions
        ],
        total_count=len(reactions),
    )


@router.get("/images/{filename}")
def get_photo_image(filename: str):
    """Получить изображение по имени файла"""
    filepath = PHOTOS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(str(filepath))