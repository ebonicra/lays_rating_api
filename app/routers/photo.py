import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.validators import (
    get_photo_or_404,
    get_photo_owned_by_user_or_404,
    get_user_or_404,
)
from app.database import get_db
from app.models.photo_reaction import PhotoReaction
from app.models.user import User
from app.models.user_photo import UserPhoto
from app.schemas.common import MessageResponse
from app.schemas.user import UserBriefResponse
from app.schemas.user_photo import (
    PhotoLikersResponse,
    PhotoListResponse,
    PhotoReactionResponse,
    UserPhotoResponse,
)

router = APIRouter(
    prefix="/photos",
    tags=["Photos"],
)


#  ФОТО ПОЛЬЗОВАТЕЛЯ

@router.get("/user/{user_id}", response_model=PhotoListResponse)
def get_user_photos(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Все фото пользователя """
    get_user_or_404(db, user_id)
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


# ЗАГРУЗКА / УДАЛЕНИЕ

@router.post("/upload", response_model=UserPhotoResponse)
async def upload_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Загрузить фото """

    photo_count = (
        db.query(UserPhoto)
        .filter(UserPhoto.user_id == current_user.id)
        .count()
    )
    if photo_count >= settings.MAX_PHOTOS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Максимум {settings.MAX_PHOTOS_PER_USER} фото",
        )

    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Допустимы только JPEG, PNG, WebP. Получен: .{ext}",
        )

    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой (макс {settings.MAX_FILE_SIZE // 1024 // 1024} МБ)",
        )

    filename = f"photo_{current_user.id}_{uuid.uuid4().hex}.{ext}"
    filepath = settings.USER_PHOTOS_DIR / filename

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


@router.delete("/{photo_id}", response_model=MessageResponse)
def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Удалить своё фото """

    photo = get_photo_owned_by_user_or_404(db, photo_id, current_user.id)

    filepath = settings.USER_PHOTOS_DIR / photo.image_path
    if filepath.exists():
        filepath.unlink()

    db.delete(photo)
    db.commit()

    return MessageResponse(message="Фото удалено")


@router.get("/images/{filename}")
def get_image(filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = settings.USER_PHOTOS_DIR / filename
    try:
        filepath.resolve().relative_to(settings.USER_PHOTOS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")

    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404)

    return FileResponse(filepath)

# ЛАЙКИ

@router.post("/{photo_id}/like", response_model=PhotoReactionResponse)
def toggle_like(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Поставить/убрать лайк """

    photo = get_photo_or_404(db, photo_id)

    existing = (
        db.query(PhotoReaction)
        .filter(
            PhotoReaction.photo_id == photo_id,
            PhotoReaction.user_id == current_user.id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        photo.likes_count = max(0, photo.likes_count - 1)
        is_liked = False
    else:
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
):
    """ Список тех, кто лайкнул фото """

    get_photo_or_404(db, photo_id)

    reactions = (
        db.query(PhotoReaction)
        .filter(PhotoReaction.photo_id == photo_id)
        .order_by(PhotoReaction.created_at.desc())
        .all()
    )
    return PhotoLikersResponse(
        users=[
            UserBriefResponse(
                id=r.user.id,
                username=r.user.username,
                display_name=r.user.display_name,
                avatar_url=r.user.avatar_url,
            )
            for r in reactions
        ],
        total_count=len(reactions),
    )


# ВСПОМОГАТЕЛЬНЫЕ

def _photo_to_response(
    db: Session,
    photo: UserPhoto,
    current_user_id: int,
) -> UserPhotoResponse:
    """
    🔧 Преобразовать модель фото в ответ.
    
    🔍 Проверяет:
    - Лайкнул ли текущий пользователь это фото
    """
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
        user=UserBriefResponse(
            id=photo.user.id,
            username=photo.user.username,
            display_name=photo.user.display_name,
            avatar_url=photo.user.avatar_url,
        ),
        image_path=photo.image_path,
        likes_count=photo.likes_count,
        is_liked=is_liked,
        created_at=photo.created_at,
    )



# /photos/user/{user_id}    GET    - все фото пользователя
# /photos/upload            POST   - загрузить фото
# /photos/{photo_id}        DELETE - удалить своё фото
# /photos/{photo_id}/like   POST   - поставить/убрать лайк
# /photos/{photo_id}/likes  GET    - кто лайкнул
# /photos/images/{file}     GET    - файл картинки