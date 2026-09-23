import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.validators import get_news_or_404
from app.database import get_db
from app.models.chip import Chip
from app.models.chip_comment import ChipComment
from app.models.chip_preference import ChipPreference
from app.models.comment_reaction import CommentReaction
from app.models.news import News
from app.models.news_type import NewsType
from app.models.poll_vote import PollVote
from app.models.user import User
from app.models.user_follow import UserFollow

router = APIRouter(
    prefix="/news",
    tags=["News"],
)


# ЛЕНТА НОВОСТЕЙ

@router.get("/feed")
def get_my_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Лента новостей текущего пользователя """
    # ID друзей (на кого подписан)
    friend_ids = [
        f[0] for f in
        db.query(UserFollow.following_id)
        .filter(UserFollow.follower_id == current_user.id)
        .all()
    ]

    news_query = (
        db.query(News)
        .outerjoin(User, News.user_id == User.id)
        .outerjoin(Chip, News.chip_id == Chip.id)
        .filter(
            # Новости от друзей (комментарии, игровые рекорды)
            (
                News.event_type.in_([
                    NewsType.FRIEND_COMMENT.value,
                    NewsType.GAME_RECORD.value,
                ])
                & (News.user_id.in_(friend_ids))
            )
            |
            # Мои подписчики (кто подписался на меня)
            (
                (News.event_type == NewsType.NEW_FOLLOWER.value)
                & (News.target_user_id == current_user.id)
            )
            |
            # Общие новости
            News.event_type.in_([
                NewsType.NEW_CHIP.value,
                NewsType.ADMIN_POST.value,
                NewsType.RUMOR.value,
                NewsType.POLL.value,
            ])
        )
        .order_by(News.created_at.desc())
        .limit(100)
        .all()
    )

    return [
        _format_news_item(db, news, current_user)
        for news in news_query
    ]


# ОТДАЧА КАРТИНОК

@router.get("/images/{filename}")
def get_news_image(filename: str):
    """ Получить картинку новости по имени файла"""

    filepath = settings.NEWS_IMAGES_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(str(filepath))


# ГОЛОСОВАНИЕ В ОПРОСАХ

@router.post("/{news_id}/vote")
def vote(
    news_id: int,
    option_index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Проголосовать в опросе """
    news = get_news_or_404(db, news_id)
    if news.event_type != NewsType.POLL.value:
        raise HTTPException(status_code=400, detail="Это не опрос")

    extra_data = _parse_extra_data(news.extra_data)
    options = extra_data.get("options", [])

    if option_index < 0 or option_index >= len(options):
        raise HTTPException(status_code=400, detail="Неверный вариант")

    existing_vote = (
        db.query(PollVote)
        .filter(
            PollVote.news_id == news_id,
            PollVote.user_id == current_user.id,
        )
        .first()
    )

    if existing_vote:
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
    """ Убрать свой голос в опросе """
    news = get_news_or_404(db, news_id)
    if news.event_type != NewsType.POLL.value:
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



# ВСПОМОГАТЕЛЬНЫЕ

def _format_news_item(
    db: Session,
    news: News,
    current_user: User,
) -> dict:
    """ Преобразовать новость в ответ """
    item = {
        "id": news.id,
        "event_type": news.event_type,
        "text": news.text,
        "created_at": news.created_at,
    }

    # Автор
    if news.user:
        item["user"] = {
            "id": news.user.id,
            "username": news.user.username,
            "display_name": news.user.display_name,
            "avatar_url": news.user.avatar_url,
        }

    # Чипсы
    if news.chip:
        item["chip"] = {
            "id": news.chip.id,
            "name": news.chip.name,
            "image_path": news.chip.image_path,
        }

    # Оценка пользователя к чипсам (для комментариев друзей)
    if news.user and news.chip:
        user_rating = (
            db.query(ChipPreference.rating)
            .filter(
                ChipPreference.user_id == news.user.id,
                ChipPreference.chip_id == news.chip.id,
            )
            .first()
        )
        if user_rating:
            item["user_rating"] = user_rating[0]

    # Опрос
    if news.event_type == NewsType.POLL.value:
        item["poll"] = _format_poll(db, news, current_user)

    # extra_data (для слухов, постов, опросов)
    if news.extra_data:
        item["extra_data"] = _parse_extra_data(news.extra_data)

    # Данные комментария (для friend_comment)
    if news.comment_id:
        comment = (
            db.query(ChipComment)
            .filter(ChipComment.id == news.comment_id)
            .first()
        )
        if comment:
            item["comment_id"] = comment.id
            item["likes_count"] = comment.likes_count
            item["dislikes_count"] = comment.dislikes_count

        my_reaction = (
            db.query(CommentReaction)
            .filter(
                CommentReaction.comment_id == news.comment_id,
                CommentReaction.user_id == current_user.id,
            )
            .first()
        )
        item["my_reaction"] = my_reaction.is_like if my_reaction else None

    return item


def _format_poll(
    db: Session,
    news: News,
    current_user: User,
) -> dict:
    """ Преобразовать опрос в ответ с подсчётом голосов """
    extra_data = _parse_extra_data(news.extra_data)
    options = extra_data.get("options", [])
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

    my_vote = (
        db.query(PollVote)
        .filter(
            PollVote.news_id == news.id,
            PollVote.user_id == current_user.id,
        )
        .first()
    )

    return {
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


def _parse_extra_data(extra_data: str | None) -> dict:
    """🔧 Безопасно распарсить JSON из extra_data"""
    if not extra_data:
        return {}
    try:
        return json.loads(extra_data)
    except (json.JSONDecodeError, TypeError):
        return {}



# /news/feed           GET    - лента новостей текущего пользователя
# /news/images/{file}  GET    - отдать картинку новости
# /news/{news_id}/vote POST   - проголосовать в опросе
# /news/{news_id}/vote DELETE - убрать свой голос