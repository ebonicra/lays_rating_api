import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackListResponse,
    FeedbackResponse,
    FeedbackReadUpdate,
)
from app.schemas.user import UserBriefResponse


# ============================================================
# ХЕЛПЕР
# ============================================================

def _feedback_to_response(feedback: Feedback) -> FeedbackResponse:
    paths: list[str] = []
    if feedback.image_paths:
        try:
            paths = json.loads(feedback.image_paths)
        except (json.JSONDecodeError, TypeError):
            paths = []

    return FeedbackResponse(
        id=feedback.id,
        user=UserBriefResponse(
            id=feedback.user.id,
            username=feedback.user.username,
            display_name=feedback.user.display_name,
            avatar_url=feedback.user.avatar_url,
        ),
        type=feedback.type,
        title=feedback.title,
        text=feedback.text,
        image_paths=paths,
        is_read=feedback.is_read,
        created_at=feedback.created_at,
    )


# ============================================================
# ПОЛЬЗОВАТЕЛЬСКИЙ РОУТЕР  →  /feedback
# ============================================================

user_router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"],
)


@user_router.post("", response_model=FeedbackResponse)
def send_feedback(
    data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = Feedback(
        user_id=current_user.id,
        type=data.type,
        title=data.title,
        text=data.text,
        image_paths=json.dumps(data.image_paths or []),
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return _feedback_to_response(feedback)


@user_router.post("/images")
async def upload_feedback_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """ Загрузить картинку для feedback. Возвращает путь. """
    # Проверка расширения — как в чипсах
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Допустимы только JPEG, PNG, WebP. Получен: .{ext}",
        )

    # Проверка размера
    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=(
                "Файл слишком большой "
                f"(макс {settings.MAX_FILE_SIZE // 1024 // 1024} МБ)"
            ),
        )

    # Сохраняем
    filename = f"feedback_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = settings.FEEDBACK_IMAGES_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "wb") as f:
        f.write(contents)

    return {"image_path": filename}

@user_router.get("/images/{filename}")
def get_feedback_image(filename: str):
    filepath = settings.FEEDBACK_IMAGES_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(str(filepath))


# ============================================================
# АДМИНСКИЙ РОУТЕР  →  /admin/feedback
# ============================================================

admin_router = APIRouter(
    prefix="/admin/feedback",
    tags=["Admin / Feedback"],
)


def _require_admin(user: User) -> None:
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Не админ")


@admin_router.get("", response_model=FeedbackListResponse)
def get_feedback_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    type: str | None = Query(None),
    is_read: bool | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """ Список сообщений от пользователей (только админ) """
    _require_admin(current_user)

    query = db.query(Feedback)

    if type is not None:
        query = query.filter(Feedback.type == type)
    if is_read is not None:
        query = query.filter(Feedback.is_read.is_(is_read))

    total_count = query.count()
    unread_count = (
        db.query(func.count(Feedback.id))
        .filter(Feedback.is_read.is_(False))
        .scalar()
    ) or 0

    offset = (page - 1) * per_page
    items = (
        query.order_by(Feedback.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return FeedbackListResponse(
        items=[_feedback_to_response(f) for f in items],
        total_count=total_count,
        unread_count=unread_count,
    )

@admin_router.put("/{feedback_id}/read", response_model=FeedbackResponse)
def set_read_status(
    feedback_id: int,
    data: FeedbackReadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Поставить/снять отметку «прочитано» (только админ) """
    _require_admin(current_user)

    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if feedback is None:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")

    feedback.is_read = data.is_read
    db.commit()
    db.refresh(feedback)
    return _feedback_to_response(feedback)


@admin_router.delete("/{feedback_id}", response_model=MessageResponse)
def delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Удалить сообщение (только админ) """
    _require_admin(current_user)

    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if feedback is None:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")

    # Заодно можно удалить прикреплённые картинки с диска
    if feedback.image_paths:
        try:
            for name in json.loads(feedback.image_paths):
                p = settings.FEEDBACK_IMAGES_DIR / name
                if p.exists():
                    p.unlink()
        except (json.JSONDecodeError, TypeError, OSError):
            pass

    db.delete(feedback)
    db.commit()
    return MessageResponse(message="Сообщение удалено")