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
from app.models.news_reaction import NewsReaction
from app.models.news_type import NewsType
from app.models.poll_vote import PollVote
from app.models.user import User
from app.models.user_follow import UserFollow
from app.schemas.news import (
    NewsReactionRequest,
    NewsReactionUser,
    NewsReactionsResponse,
)

router = APIRouter(
    prefix="/news",
    tags=["News"],
)

REACTABLE_EVENTS = {
    NewsType.ADMIN_POST.value,
    NewsType.RUMOR.value,
    NewsType.POLL.value,
}


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

    news_list = (
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

    # Батч-подсчёт реакций для всей ленты (2 запроса вместо 2*N)
    news_ids = [n.id for n in news_list]
    reactions_map = _load_reactions_for_news(db, news_ids, current_user.id)

    return [
        _format_news_item(
            db,
            news,
            current_user,
            reactions_map.get(news.id),
        )
        for news in news_list
    ]


# ОТДАЧА КАРТИНОК

@router.get("/images/{filename}")
def get_news_image(filename: str):
    """ Получить картинку новости по имени файла """
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


# РЕАКЦИИ НА НОВОСТИ

@router.post("/{news_id}/reaction")
def set_reaction(
    news_id: int,
    payload: NewsReactionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Поставить лайк/дизлайк новости.
    Если реакция уже стоит:
      - та же    → снимаем
      - другая   → меняем
    """
    news = get_news_or_404(db, news_id)

    if news.event_type not in REACTABLE_EVENTS:
        raise HTTPException(
            status_code=400,
            detail="На эту новость нельзя реагировать",
        )

    existing = (
        db.query(NewsReaction)
        .filter(
            NewsReaction.news_id == news_id,
            NewsReaction.user_id == current_user.id,
        )
        .first()
    )

    if existing and existing.is_like == payload.is_like:
        # Та же реакция — снимаем
        db.delete(existing)
        db.commit()
        my_reaction = None
    elif existing:
        # Меняем
        existing.is_like = payload.is_like
        db.commit()
        my_reaction = payload.is_like
    else:
        # Новая
        db.add(NewsReaction(
            news_id=news_id,
            user_id=current_user.id,
            is_like=payload.is_like,
        ))
        db.commit()
        my_reaction = payload.is_like

    likes_count, dislikes_count = _count_reactions(db, news_id)

    return {
        "news_likes_count": likes_count,
        "news_dislikes_count": dislikes_count,
        "my_news_reaction": my_reaction,
    }


@router.get("/{news_id}/reactions", response_model=NewsReactionsResponse)
def get_reactions(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Список пользователей, лайкнувших/дизлайкнувших новость """
    news = get_news_or_404(db, news_id)

    if news.event_type not in REACTABLE_EVENTS:
        raise HTTPException(
            status_code=400,
            detail="На эту новость нельзя реагировать",
        )

    rows = (
        db.query(NewsReaction)
        .filter(NewsReaction.news_id == news_id)
        .order_by(NewsReaction.created_at.desc())
        .all()
    )

    likes: list[NewsReactionUser] = []
    dislikes: list[NewsReactionUser] = []
    for r in rows:
        if r.user is None:
            continue
        item = NewsReactionUser(
            id=r.user.id,
            username=r.user.username,
            display_name=r.user.display_name,
            avatar_url=r.user.avatar_url,
        )
        (likes if r.is_like else dislikes).append(item)

    return NewsReactionsResponse(likes=likes, dislikes=dislikes)


# ВСПОМОГАТЕЛЬНЫЕ

def _count_reactions(db: Session, news_id: int) -> tuple[int, int]:
    """ Вернуть (likes_count, dislikes_count) для одной новости """
    rows = (
        db.query(NewsReaction.is_like, func.count(NewsReaction.id))
        .filter(NewsReaction.news_id == news_id)
        .group_by(NewsReaction.is_like)
        .all()
    )
    likes = 0
    dislikes = 0
    for is_like, count in rows:
        if is_like:
            likes = count
        else:
            dislikes = count
    return likes, dislikes


def _load_reactions_for_news(
    db: Session,
    news_ids: list[int],
    user_id: int,
) -> dict[int, dict]:
    """
    Батч-подсчёт реакций для ленты.
    Возвращает {news_id: {"likes": int, "dislikes": int, "my": bool | None}}.
    """
    if not news_ids:
        return {}

    result: dict[int, dict] = {
        nid: {"likes": 0, "dislikes": 0, "my": None}
        for nid in news_ids
    }

    # Счётчики лайков/дизлайков по всем новостям сразу
    agg = (
        db.query(
            NewsReaction.news_id,
            NewsReaction.is_like,
            func.count(NewsReaction.id),
        )
        .filter(NewsReaction.news_id.in_(news_ids))
        .group_by(NewsReaction.news_id, NewsReaction.is_like)
        .all()
    )
    for news_id, is_like, count in agg:
        if is_like:
            result[news_id]["likes"] = count
        else:
            result[news_id]["dislikes"] = count

    # Мои реакции по всем новостям сразу
    mine = (
        db.query(NewsReaction.news_id, NewsReaction.is_like)
        .filter(
            NewsReaction.news_id.in_(news_ids),
            NewsReaction.user_id == user_id,
        )
        .all()
    )
    for news_id, is_like in mine:
        result[news_id]["my"] = is_like

    return result


def _format_news_item(
    db: Session,
    news: News,
    current_user: User,
    reactions: dict | None = None,
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

    # Данные комментария (для friend_comment) — отдельные ключи
    if news.comment_id:
        comment = (
            db.query(ChipComment)
            .filter(ChipComment.id == news.comment_id)
            .first()
        )
        if comment:
            item["comment_id"] = comment.id
            item["comment_likes_count"] = comment.likes_count
            item["comment_dislikes_count"] = comment.dislikes_count

        my_comment_reaction = (
            db.query(CommentReaction)
            .filter(
                CommentReaction.comment_id == news.comment_id,
                CommentReaction.user_id == current_user.id,
            )
            .first()
        )
        item["my_comment_reaction"] = (
            my_comment_reaction.is_like if my_comment_reaction else None
        )

    # Реакции новости — отдельные ключи (только для реагируемых типов)
    if news.event_type in REACTABLE_EVENTS and reactions is not None:
        item["news_likes_count"] = reactions["likes"]
        item["news_dislikes_count"] = reactions["dislikes"]
        item["my_news_reaction"] = reactions["my"]

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


# /news/feed                    GET    - лента новостей текущего пользователя
# /news/images/{file}           GET    - отдать картинку новости
# /news/{news_id}/vote          POST   - проголосовать в опросе
# /news/{news_id}/vote          DELETE - убрать свой голос
# /news/{news_id}/reaction      POST   - поставить/сменить/снять реакцию
# /news/{news_id}/reactions     GET    - список лайкнувших/дизлайкнувших