import json


import uuid
from pathlib import Path
from fastapi import UploadFile, File
from app.config import settings

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackListResponse,
    FeedbackResponse,
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
    return feedback


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
        items=items,
        total_count=total_count,
        unread_count=unread_count,
    )


@admin_router.put("/{feedback_id}/read", response_model=FeedbackResponse)
def mark_as_read(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Отметить сообщение как прочитанное (только админ) """
    _require_admin(current_user)

    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if feedback is None:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")

    feedback.is_read = True
    db.commit()
    db.refresh(feedback)
    return feedback


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

    db.delete(feedback)
    db.commit()
    return MessageResponse(message="Сообщение удалено")

@user_router.post("/images")
async def upload_feedback_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """ Загрузить картинку для feedback. Возвращает путь. """
    # Проверка типа
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Только изображения")

    # Проверка размера (например, не больше 5 МБ)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Максимум 5 МБ")

    # Сохраняем с уникальным именем
    ext = Path(file.filename or "").suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = settings.FEEDBACK_IMAGES_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "wb") as f:
        f.write(contents)

    return {"image_path": filename}