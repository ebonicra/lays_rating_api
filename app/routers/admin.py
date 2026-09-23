import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_admin, get_current_super_admin
from app.core.validators import get_chip_or_404, get_news_or_404, get_user_or_404
from app.database import get_db
from app.models.chip import Chip
from app.models.news import News
from app.models.news_type import NewsType
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.chip import ChipAdminResponse, ChipCreate, ChipUpdate
from app.schemas.common import MessageResponse
from app.schemas.news import NewsCreate
from app.schemas.user import UserBriefResponse

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# ЧИПСЫ

@router.post("/chips", response_model=ChipAdminResponse)
async def create_chip(
    name: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    collection: str | None = Form(None),
    release_year: int | None = Form(None),
    country: str | None = Form(None),
    available: bool = Form(True),
    image: UploadFile | None = File(None),  # ← картинка опциональна
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """ Создать новую карточку чипсов """
    image_path = None
    if image is not None:
        # Проверки
        ext = image.filename.split(".")[-1].lower() if "." in image.filename else ""
        if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(400, f"Неверный формат: .{ext}")
        
        contents = await image.read()
        if len(contents) > settings.MAX_FILE_SIZE:
            raise HTTPException(400, "Файл слишком большой")
        
        # Генерируем имя и сохраняем
        filename = f"chip_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = settings.CHIP_IMAGES_DIR / filename
        
        with open(filepath, "wb") as f:
            f.write(contents)
        
        image_path = filename
    
    # Создаём чипсы
    chip = Chip(
        name=name,
        category=category,
        description=description,
        image_path=image_path,  # ← может быть None
        collection=collection,
        release_year=release_year,
        country=country,
        available=available,
    )
    db.add(chip)
    db.commit()
    db.refresh(chip)
    
    # Создаём новость
    news = News(
        event_type=NewsType.NEW_CHIP.value,
        chip_id=chip.id,
        text=f"Новый вкус: {chip.name}!",
    )
    db.add(news)
    db.commit()
    
    return chip


@router.put("/chips/{chip_id}", response_model=ChipAdminResponse)
def update_chip(
    chip_id: int,
    data: ChipUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """ Обновить карточку чипсов """
    chip = get_chip_or_404(db, chip_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(chip, field, value)

    db.commit()
    db.refresh(chip)
    return chip


@router.delete("/chips/{chip_id}", response_model=MessageResponse)
def delete_chip(
    chip_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """ Удалить чипс """
    chip = get_chip_or_404(db, chip_id)

    # Удаляем картинку с диска
    if chip.image_path:
        filepath = settings.CHIP_IMAGES_DIR / chip.image_path
        if filepath.exists():
            filepath.unlink()

    db.delete(chip)
    db.commit()

    return MessageResponse(message="Чипс удалён")

@router.post("/chips/{chip_id}/image")
async def upload_chip_image(
    chip_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """ Загрузить картинку для чипсов """
    chip = get_chip_or_404(db, chip_id)

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

    # Удаляем старую картинку
    if chip.image_path:
        old_path = settings.CHIP_IMAGES_DIR / chip.image_path
        if old_path.exists():
            old_path.unlink()

    # Сохраняем новую
    filename = f"chip_{chip.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = settings.CHIP_IMAGES_DIR / filename

    with open(filepath, "wb") as f:
        f.write(contents)

    chip.image_path = filename
    db.commit()

    return {"image_path": filename}


# НОВОСТИ

@router.post("/news")
def create_news(
    data: NewsCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """ Создать новость """
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
):
    """ Загрузить картинку для новости """
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

    filename = f"news_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = settings.NEWS_IMAGES_DIR / filename

    with open(filepath, "wb") as f:
        f.write(contents)

    return {"image_path": filename}


@router.delete("/news/{news_id}", response_model=MessageResponse)
def delete_news(
    news_id: int,
    db: Session = Depends(get_db),
):
    """ Удалить новость"""
    news = get_news_or_404(db, news_id)

    db.delete(news)
    db.commit()

    return MessageResponse(message="Новость удалена")


# УПРАВЛЕНИЕ АДМИНАМИ

@router.get("/admins", response_model=list[UserBriefResponse])
def get_admins(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """ Список всех админов (включая супер-админов) """
    admins = (
        db.query(User)
        .filter(User.role.in_([
            UserRole.ADMIN.value,
            UserRole.SUPER_ADMIN.value,
        ]))
        .all()
    )
    return admins


@router.post("/admins/{user_id}", response_model=MessageResponse)
def make_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),  # ← только супер-админ!
):
    """ Назначить пользователя админом """
    user = get_user_or_404(db, user_id)

    if user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=400,
            detail="Пользователь уже супер-админ",
        )

    if user.role == UserRole.ADMIN.value:
        raise HTTPException(
            status_code=400,
            detail="Пользователь уже админ",
        )

    user.role = UserRole.ADMIN.value
    db.commit()

    return MessageResponse(message=f"{user.username} теперь админ")


@router.delete("/admins/{user_id}", response_model=MessageResponse)
def remove_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),  # ← только супер-админ!
):
    """ Снять админа """
    user = get_user_or_404(db, user_id)

    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Нельзя снять себя")

    if user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Нельзя снять супер-админа",
        )

    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=400,
            detail="Пользователь не является админом",
        )

    user.role = UserRole.USER.value
    db.commit()

    return MessageResponse(message=f"{user.username} больше не админ")



# /admin/chips                   POST   - создать чипсы
# /admin/chips/{chip_id}         PUT    - обновить чипсы
# /admin/chips/{chip_id}/image   POST   - загрузить картинку чипсов
# /admin/news                    POST   - создать новость
# /admin/news/upload-image       POST   - загрузить картинку новости
# /admin/news/{news_id}          DELETE - удалить новость
# /admin/admins                  GET    - список админов
# /admin/admins/{user_id}        POST   - назначить админа
# /admin/admins/{user_id}        DELETE - снять админа