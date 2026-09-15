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
    """ Получить настройки фильтров пользователя """
    filters = (
        db.query(UserFilter)
        .filter(UserFilter.user_id == current_user.id)
        .all()
    )

    if not filters:
        return UserFilterResponse(
            categories=[],
            russia_only=False,
            available_only=False,
        )

    return UserFilterResponse(
        categories=[f.category for f in filters],
        russia_only=filters[0].russia_only,
        available_only=filters[0].available_only,
    )


@router.put("", response_model=UserFilterResponse)
def update_filters(
    data: UserFilterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Обновить настройки фильтров """

    if data.categories is not None:
        db.query(UserFilter).filter(
            UserFilter.user_id == current_user.id
        ).delete()

        russia = data.russia_only if data.russia_only is not None else False
        available = data.available_only if data.available_only is not None else False

        for category in data.categories:
            new_filter = UserFilter(
                user_id=current_user.id,
                category=category,
                russia_only=russia,
                available_only=available,
            )
            db.add(new_filter)

    elif data.russia_only is not None or data.available_only is not None:
        user_filters = (
            db.query(UserFilter)
            .filter(UserFilter.user_id == current_user.id)
            .all()
        )
        for uf in user_filters:
            if data.russia_only is not None:
                uf.russia_only = data.russia_only
            if data.available_only is not None:
                uf.available_only = data.available_only

    db.commit()

    filters = (
        db.query(UserFilter)
        .filter(UserFilter.user_id == current_user.id)
        .all()
    )

    if not filters:
        return UserFilterResponse(
            categories=[],
            russia_only=False,
            available_only=False,
        )

    return UserFilterResponse(
        categories=[f.category for f in filters],
        russia_only=filters[0].russia_only,
        available_only=filters[0].available_only,
    )


# /filters  GET - получить фильтры
# /filters  PUT - обновить фильтры
