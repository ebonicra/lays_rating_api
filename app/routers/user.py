import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.common import MessageResponse

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)



# ПРОФИЛЬ

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Получить свой профиль"""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_profile(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Обновить имя и username """
    if data.display_name is not None:
        current_user.display_name = data.display_name

    if data.username is not None:
        existing = (
            db.query(User)
            .filter(
                User.username == data.username,
                User.id != current_user.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Username уже занят")
        current_user.username = data.username

    db.commit()
    db.refresh(current_user)

    return current_user

@router.delete("/me", response_model=MessageResponse)
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Удалить свой аккаунт """
    db.delete(current_user)
    db.commit()
    return MessageResponse(message="Аккаунт удалён")

# АВАТАРКИ

@router.get("/avatars/{filename}")
def get_avatar(filename: str):
    """Получить аватарку по имени файла"""
    filepath = settings.AVATARS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(str(filepath))


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Загрузить аватарку"""
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""

    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Допустимы только JPEG, PNG, WebP. Получен: .{ext}",
        )

    contents = await file.read()
    if len(contents) > settings.MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой (макс {settings.MAX_AVATAR_SIZE // 1024 // 1024} МБ)",
        )

    if current_user.avatar_path:
        old_path = settings.AVATARS_DIR / current_user.avatar_path
        if old_path.exists():
            old_path.unlink()

    filename = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = settings.AVATARS_DIR / filename

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
        filepath = settings.AVATARS_DIR / current_user.avatar_path
        if filepath.exists():
            filepath.unlink()

    current_user.avatar_path = None
    db.commit()

    return {"message": "Аватарка удалена"}



# ПУБЛИЧНЫЙ ПРОФИЛЬ

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Получить публичный профиль пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return user



# /users/me              GET      — свой профиль
# /users/me              PUT      — обновить профиль
# /users/avatars/{file}  GET      — получить файл аватарки
# /users/me/avatar       POST     — загрузить аватарку
# /users/me/avatar       DELETE   — удалить аватарку
# /users/{user_id}       GET      — публичный профиль