from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.chip import Chip
from app.models.chip_comment import ChipComment
from app.models.news import News
from app.models.user import User
from app.models.user_photo import UserPhoto
from app.schemas.user_follow import UserBriefResponse



def get_user_or_404(db: Session, user_id: int) -> User:
    """ Получить пользователя или выбросить 404 """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

def get_chip_or_404(db: Session, chip_id: int) -> Chip:
    """ Получить чипсы или выбросить 404 """
    chip = db.query(Chip).filter(Chip.id == chip_id).first()
    if chip is None:
        raise HTTPException(status_code=404, detail="Чипсы не найдены")
    return chip

def get_photo_or_404(db: Session, photo_id: int) -> UserPhoto:
    """ Получить фото или выбросить 404 """
    photo = db.query(UserPhoto).filter(UserPhoto.id == photo_id).first()
    if photo is None:
        raise HTTPException(status_code=404, detail="Фото не найдено")
    return photo

def get_photo_owned_by_user_or_404(
    db: Session,
    photo_id: int,
    user_id: int,
) -> UserPhoto:
    """ Получить фото или выбросить 404/403 """
    photo = get_photo_or_404(db, photo_id)
    if photo.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Можно изменять только свои фото",
        )
    return photo


def get_comment_or_404(db: Session, comment_id: int) -> ChipComment:
    """ Получить комментарий или выбросить 404 """
    comment = db.query(ChipComment).filter(ChipComment.id == comment_id).first()
    if comment is None:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    return comment

def get_comment_owned_by_user_or_404(
    db: Session,
    comment_id: int,
    user_id: int,
) -> ChipComment:
    """ Получить комментарий или выбросить 404/403 """
    comment = get_comment_or_404(db, comment_id)
    if comment.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Можно изменять только свои комментарии",
        )
    return comment

def get_news_or_404(db: Session, news_id: int) -> News:
    """ Получить новость или выбросить 404 """
    news = db.query(News).filter(News.id == news_id).first()
    if news is None:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    return news


def get_user_brief(user: User) -> UserBriefResponse:
    """Преобразовать User в краткую информацию"""
    return UserBriefResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=f"/users/avatars/{user.avatar_path}" if user.avatar_path else None,
    )