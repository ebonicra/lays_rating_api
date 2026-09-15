# routers/news.py
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func
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
from app.models.poll_vote import PollVote


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
            |
            (News.event_type == "poll")
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





        if news.event_type == "poll":
            extra_data = json.loads(news.extra_data) if news.extra_data else {}
            options = extra_data.get("options", [])
            
            # Считаем голоса для каждого варианта
            votes_by_option = {}
            for i in range(len(options)):
                count = (
                    db.query(func.count(PollVote.id))
                    .filter(
                        PollVote.news_id == news.id,
                        PollVote.option_index == i,
                    )
                    .scalar()
                )
                votes_by_option[i] = count or 0
            
            # Мой голос
            my_vote = (
                db.query(PollVote)
                .filter(
                    PollVote.news_id == news.id,
                    PollVote.user_id == current_user.id,
                )
                .first()
            )
            
            item["poll"] = {
                "question": extra_data.get("question", ""),
                "options": [
                    {
                        "text": opt.get("text", ""),
                        "image_path": opt.get("image_path"),
                        "votes": votes_by_option.get(i, 0),
                    }
                    for i, opt in enumerate(options)
                ],
                "total_votes": sum(votes_by_option.values()),
                "my_vote": my_vote.option_index if my_vote else None,
            }

        
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


@router.post("/{news_id}/vote")
def vote(
    news_id: int,
    option_index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Проголосовать в опросе"""
    
    news = db.query(News).filter(News.id == news_id).first()
    if news is None:
        raise HTTPException(status_code=404, detail="Опрос не найден")
    
    if news.event_type != "poll":
        raise HTTPException(status_code=400, detail="Это не опрос")
    
    # Проверяем, что вариант существует
    extra_data = json.loads(news.extra_data) if news.extra_data else {}
    options = extra_data.get("options", [])
    
    if option_index < 0 or option_index >= len(options):
        raise HTTPException(status_code=400, detail="Неверный вариант")
    
    # Проверяем, голосовал ли уже
    existing = (
        db.query(PollVote)
        .filter(
            PollVote.news_id == news_id,
            PollVote.user_id == current_user.id,
        )
        .first()
    )
    
    if existing:
        raise HTTPException(status_code=400, detail="Вы уже голосовали")
    
    vote = PollVote(
        news_id=news_id,
        user_id=current_user.id,
        option_index=option_index,
    )
    db.add(vote)
    db.commit()
    
    return {"message": "Голос учтён", "option_index": option_index}


@router.delete("/{news_id}/vote")
def remove_vote(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Убрать свой голос"""
    
    news = db.query(News).filter(News.id == news_id).first()
    if news is None:
        raise HTTPException(status_code=404, detail="Опрос не найден")
    
    if news.event_type != "poll":
        raise HTTPException(status_code=400, detail="Это не опрос")
    
    vote = (
        db.query(PollVote)
        .filter(
            PollVote.news_id == news_id,
            PollVote.user_id == current_user.id,
        )
        .first()
    )
    
    if vote is None:
        raise HTTPException(status_code=404, detail="Голос не найден")
    
    db.delete(vote)
    db.commit()
    
    return {"message": "Голос отменён"}


