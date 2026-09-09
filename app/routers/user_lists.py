from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.follow import UserBriefResponse
from app.core.dependencies import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["User Lists"]
)


def _get_user_brief(user: User) -> UserBriefResponse:
    """Преобразовать User в краткую информацию"""
    return UserBriefResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=f"/users/avatars/{user.avatar_path}" if user.avatar_path else None,
    )


@router.get("/search")
def search_users(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Поиск пользователей по username"""
    users = (
        db.query(User)
        .filter(
            User.username.ilike(f"%{q}%"),
            User.id != current_user.id,  # исключаем себя
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
    """Получить всех пользователей (кроме себя)"""
    users = (
        db.query(User)
        .filter(User.id != current_user.id)
        .order_by(User.username)
        .all()
    )
    return [_get_user_brief(u) for u in users]