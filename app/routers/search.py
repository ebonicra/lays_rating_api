from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserBriefResponse

router = APIRouter(
    prefix="/search",
    tags=["Search"],
)

@router.get("/users", response_model=list[UserBriefResponse])
def search_users(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Поиск пользователей по username """
    users = (
        db.query(User)
        .filter(
            User.username.ilike(f"%{q}%"),
            User.id != current_user.id,
        )
        .limit(20)
        .all()
    )

    return users


@router.get("/all", response_model=list[UserBriefResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Список всех пользователей """
    users = (
        db.query(User)
        .filter(User.id != current_user.id)
        .order_by(User.username)
        .all()
    )
    
    return users


# /search/users  GET - поиск пользователей по username
# /search/all    GET - список всех пользователей (кроме себя)

