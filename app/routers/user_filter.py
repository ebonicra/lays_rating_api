from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.user_filter import UserFilter
from app.schemas.user_filter import (
    UserFilterResponse,
    UserFilterUpdate,
)

router = APIRouter(
    prefix="/filters",
    tags=["Filters"],
)


@router.get("", response_model=UserFilterResponse)
def get_filters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить настройки фильтров пользователя."""
    filters = (
        db.query(UserFilter)
        .filter(UserFilter.user_id == current_user.id)
        .all()
    )

    return UserFilterResponse(
        filters=[f.filter for f in filters],
        russia_only=current_user.filter_russia_only,
        available_only=current_user.filter_available_only,
    )


@router.put("", response_model=UserFilterResponse)
def update_filters(
    data: UserFilterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить настройки фильтров.

    Все поля опциональны — можно обновить любое подмножество.
    `filters` заменяет список целиком (не мержит).
    """
    # Флаги — на уровне пользователя
    if data.russia_only is not None:
        current_user.filter_russia_only = data.russia_only
    if data.available_only is not None:
        current_user.filter_available_only = data.available_only

    # Список фильтров — если передан, полностью заменяем
    if data.filters is not None:
        db.query(UserFilter).filter(
            UserFilter.user_id == current_user.id
        ).delete(synchronize_session=False)

        for name in data.filters:
            db.add(UserFilter(
                user_id=current_user.id,
                filter=name,
            ))

    db.commit()
    db.refresh(current_user)

    return get_filters(db=db, current_user=current_user)