from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User

security = HTTPBearer()


# БАЗОВАЯ АУТЕНТИФИКАЦИЯ

def get_current_user(
    credentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """ Получить текущего пользователя по JWT-токену """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    user_id = payload.get("user_id")

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user


# ПРАВА ДОСТУПА

def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """ Проверить, что текущий пользователь — админ или супер-админ """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Требуются права администратора",
        )
    return current_user


def get_current_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """ Проверить, что текущий пользователь — супер-админ """
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="Требуются права супер-админа",
        )
    return current_user