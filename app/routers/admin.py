import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid
from pathlib import Path

from app.database import get_db
from app.models.chip import Chip
from app.models.news import News
from app.models.user import User
from app.core.dependencies import get_current_admin
from app.schemas.chip import ChipUpdate, ChipAdminResponse, ChipCreate
from app.schemas.news import NewsCreate


BASE_DIR = Path(__file__).resolve().parent.parent
NEWS_DIR = BASE_DIR / "backend" / "uploads" / "news"
os.makedirs(NEWS_DIR, exist_ok=True)


router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

# Папка для картинок чипсов
BASE_DIR = Path(__file__).resolve().parent.parent
CHIPS_DIR = BASE_DIR / "backend" / "uploads" / "chips"
os.makedirs(CHIPS_DIR, exist_ok=True)


@router.put("/chips/{chip_id}", response_model=ChipAdminResponse)
def update_chip(
    chip_id: int,
    data: ChipUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Обновить карточку чипсов"""
    
    chip = db.query(Chip).filter(Chip.id == chip_id).first()
    
    if chip is None:
        raise HTTPException(status_code=404, detail="Чипсы не найдены")
    
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(chip, field, value)
    
    db.commit()
    db.refresh(chip)
    
    return chip


@router.post("/chips/{chip_id}/image")
async def upload_chip_image(
    chip_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Загрузить картинку для чипсов"""
    
    chip = db.query(Chip).filter(Chip.id == chip_id).first()
    if chip is None:
        raise HTTPException(status_code=404, detail="Чипсы не найдены")
    
    # Проверяем расширение
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "png"
    allowed = ["jpg", "jpeg", "png", "webp"]
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Неверный формат")
    
    # Проверяем размер
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой")
    
    # Удаляем старую картинку
    if chip.image_path:
        old_path = CHIPS_DIR / chip.image_path
        if old_path.exists():
            old_path.unlink()
    
    # Сохраняем новую
    filename = f"chip_{chip.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = CHIPS_DIR / filename
    
    with open(filepath, "wb") as f:
        f.write(contents)
    
    chip.image_path = filename
    db.commit()
    
    return {"image_path": filename}


@router.post("/chips", response_model=ChipAdminResponse)
def create_chip(
    data: ChipCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Создать новую карточку чипсов"""
    
    chip = Chip(
        name=data.name,
        category=data.category,
        description=data.description,
        image_path=data.image_path if data.image_path else "",
        collection=data.collection,
        country=data.country,
        release_year=data.release_year,
        available=data.available,
    )
    db.add(chip)
    db.commit()
    db.refresh(chip)


    news = News(
        event_type="new_chip",
        chip_id=chip.id,
        text=f"Новый вкус: {chip.name}!",
    )
    db.add(news)
    db.commit()

    return chip

@router.post("/news")
def create_news(
    data: NewsCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Создать новость"""
    
    extra_data = None
    if data.extra_data:
        extra_data = json.dumps(data.extra_data)
    
    news = News(
        event_type=data.event_type,
        user_id=current_admin.id,
        text=data.text,
        extra_data=extra_data,
    )
    db.add(news)
    db.commit()
    db.refresh(news)
    
    return {"id": news.id, "message": "Новость создана"}


@router.post("/news/upload-image")
async def upload_news_image(
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin),
):
    """Загрузить картинку для новости"""
    
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "png"
    allowed = ["jpg", "jpeg", "png", "webp"]
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Неверный формат")
    
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой")
    
    filename = f"news_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(NEWS_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(contents)
    
    return {"image_path": filename}



@router.delete("/news/{news_id}")
def delete_news(
    news_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Удалить новость (только для админов)"""
    
    news = db.query(News).filter(News.id == news_id).first()
    if news is None:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    
    db.delete(news)
    db.commit()
    
    return {"message": "Новость удалена"}


@router.get("/admins")
def get_admins(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Список всех админов"""
    admins = db.query(User).filter(User.is_admin == True).all()
    return [
        {
            "id": admin.id,
            "username": admin.username,
            "display_name": admin.display_name,
            "avatar_url": f"/users/avatars/{admin.avatar_path}" if admin.avatar_path else None,
        }
        for admin in admins
    ]


@router.post("/admins/{user_id}")
def make_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Назначить пользователя админом"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    user.is_admin = True
    db.commit()
    return {"message": f"{user.username} теперь админ"}


@router.delete("/admins/{user_id}")
def remove_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Снять админа"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Нельзя снять себя")
    
    user.is_admin = False
    db.commit()
    return {"message": f"{user.username} больше не админ"}