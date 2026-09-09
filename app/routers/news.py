# routers/news.py
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models.user import User
from app.models.chip import Chip
from app.models.news import News
from app.models.follow import Follow
from app.models.chip_comment import ChipComment
from app.models.comment_reaction import CommentReaction
from app.models.chip_preference import ChipPreference

from app.core.dependencies import get_current_user


BASE_DIR = Path(__file__).resolve().parent.parent
NEWS_DIR = BASE_DIR / "backend" / "uploads" / "news"
os.makedirs(NEWS_DIR, exist_ok=True)


router = APIRouter(
    prefix="/news",
    tags=["News"]
)


@router.get("/feed")
def get_my_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Лента новостей текущего пользователя"""
    
    # Получаем id друзей (на кого подписан)
    following_ids = (
        db.query(Follow.following_id)
        .filter(Follow.follower_id == current_user.id)
        .all()
    )
    friend_ids = [fid[0] for fid in following_ids]
    
    # Новости:
    # - friend_comment от друзей
    # - game_record от друзей
    # - new_chip (для всех)
    # - admin_post (для всех)
    news_query = (
        db.query(News, User, Chip)
        .outerjoin(User, News.user_id == User.id)
        .outerjoin(Chip, News.chip_id == Chip.id)
        .filter(
            (
                (News.event_type == "friend_comment") |
                (News.event_type == "game_record") |
                (News.event_type == "new_follower")
            ) & (News.user_id.in_(friend_ids))
            |
            (News.event_type == "new_chip")
            |
            (News.event_type == "admin_post")
            |
            (News.event_type == "rumor")
        )
        .order_by(News.created_at.desc())
        .limit(100)
        .all()
    )
    
    # Формируем ответ
    result = []
    for news, user, chip in news_query:
        item = {
            "id": news.id,
            "event_type": news.event_type,
            "text": news.text,
            "created_at": news.created_at,
        }
        
        if user:
            item["user"] = {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "avatar_url": f"/users/avatars/{user.avatar_path}" if user.avatar_path else None,
            }
        
        if chip:
            item["chip"] = {
                "id": chip.id,
                "name": chip.name,
                "image_path": chip.image_path,
            }



        if user and chip:
            # Получаем оценку пользователя для этого чипса
            user_rating = (
                db.query(ChipPreference.rating)
                .filter(
                    ChipPreference.user_id == user.id,
                    ChipPreference.chip_id == chip.id,
                )
                .first()
            )
            if user_rating:
                item["user_rating"] = user_rating[0]
        
        if news.extra_data:
            item["extra_data"] = json.loads(news.extra_data)

        if user and chip and news.comment_id:
            comment = db.query(ChipComment).filter(ChipComment.id == news.comment_id).first()
            if comment:
                item["likes_count"] = comment.likes_count
                item["dislikes_count"] = comment.dislikes_count
                item["comment_id"] = comment.id

        if news.comment_id:
            # Получаем реакцию текущего пользователя
            my_reaction = (
                db.query(CommentReaction)
                .filter(
                    CommentReaction.comment_id == news.comment_id,
                    CommentReaction.user_id == current_user.id,
                )
                .first()
            )
            if my_reaction:
                item["my_reaction"] = my_reaction.is_like  # True = лайк, False = дизлайк
            else:
                item["my_reaction"] = None
        
        result.append(item)
    
    return result

@router.get("/images/{filename}")
def get_news_image(filename: str):
    filepath = os.path.join(NEWS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(filepath)


