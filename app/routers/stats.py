from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.validators import get_user_or_404
from app.database import get_db
from app.models.chip import Chip
from app.models.chip_comment import ChipComment
from app.models.chip_preference import ChipPreference
from app.models.user import User
from app.models.user_follow import UserFollow

router = APIRouter(
    prefix="/stats",
    tags=["Stats"],
)


#  ОБЩАЯ СТАТИСТИКА

@router.get("/{user_id}")
def get_user_stats(
    user_id: int,
    db: Session = Depends(get_db),
):
    """ Общая статистика пользователя """
    get_user_or_404(db, user_id)

    ratings_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == user_id,
        ChipPreference.rating.isnot(None),
    ).scalar() or 0

    favorites_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == user_id,
        ChipPreference.is_favorite == True,
    ).scalar() or 0

    tried_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == user_id,
        ChipPreference.is_tried == True,
    ).scalar() or 0

    comments_count = db.query(func.count(ChipComment.id)).filter(
        ChipComment.user_id == user_id,
    ).scalar() or 0

    avg_rating = db.query(func.avg(ChipPreference.rating)).filter(
        ChipPreference.user_id == user_id,
        ChipPreference.rating.isnot(None),
    ).scalar()

    followers_count = db.query(func.count(UserFollow.id)).filter(
        UserFollow.following_id == user_id,
    ).scalar() or 0

    following_count = db.query(func.count(UserFollow.id)).filter(
        UserFollow.follower_id == user_id,
    ).scalar() or 0

    return {
        "ratings_count": ratings_count,
        "favorites_count": favorites_count,
        "tried_count": tried_count,
        "comments_count": comments_count,
        "average_rating": round(float(avg_rating), 1) if avg_rating else 0.0,
        "followers_count": followers_count,
        "following_count": following_count,
    }


# ЛЮБИМЧИКИ

@router.get("/{user_id}/favorites")
def get_user_favorites(
    user_id: int,
    db: Session = Depends(get_db),
):
    """ Любимые чипсы пользователя"""
    get_user_or_404(db, user_id)
    favorites = (
        db.query(
            Chip,
            func.avg(ChipPreference.rating),
            func.count(ChipPreference.rating),
            func.count(ChipPreference.id).filter(ChipPreference.is_favorite == True),
        )
        .outerjoin(ChipPreference, ChipPreference.chip_id == Chip.id)
        .filter(
            Chip.id.in_(
                db.query(ChipPreference.chip_id)
                .filter(
                    ChipPreference.user_id == user_id,
                    ChipPreference.is_favorite == True,
                )
            ),
        )
        .group_by(Chip.id)
        .all()
    )

    return [
        {
            "id": chip.id,
            "name": chip.name,
            "average_rating": round(float(avg_rating or 0), 1),
            "rating_count": rating_count or 0,
            "favorite_count": favorite_count or 0,
            "image_path": chip.image_path,
        }
        for chip, avg_rating, rating_count, favorite_count in favorites
    ]


# ПРОБОВАЛ

@router.get("/{user_id}/tried")
def get_user_tried(
    user_id: int,
    db: Session = Depends(get_db),
):
    """ Чипсы, которые пробовал пользователь"""
    get_user_or_404(db, user_id)
    tried_chips = (
        db.query(
            Chip,
            func.avg(ChipPreference.rating),
            func.count(ChipPreference.rating),
            func.count(ChipPreference.id).filter(ChipPreference.is_tried == True),
        )
        .outerjoin(ChipPreference, ChipPreference.chip_id == Chip.id)
        .filter(
            Chip.id.in_(
                db.query(ChipPreference.chip_id)
                .filter(
                    ChipPreference.user_id == user_id,
                    ChipPreference.is_tried == True,
                )
            ),
        )
        .group_by(Chip.id)
        .all()
    )

    return [
        {
            "id": chip.id,
            "name": chip.name,
            "average_rating": round(float(avg_rating or 0), 1),
            "rating_count": rating_count or 0,
            "tried_count": tried_count or 0,
            "image_path": chip.image_path,
        }
        for chip, avg_rating, rating_count, tried_count in tried_chips
    ]


# ОЦЕНКИ

@router.get("/{user_id}/ratings")
def get_user_ratings(
    user_id: int,
    db: Session = Depends(get_db),
):
    """ Оценки пользователя"""
    get_user_or_404(db, user_id)
    user_ratings = (
        db.query(ChipPreference.chip_id, ChipPreference.rating)
        .filter(
            ChipPreference.user_id == user_id,
            ChipPreference.rating.isnot(None),
        )
        .all()
    )

    if not user_ratings:
        return []

    chip_ids = [chip_id for chip_id, _ in user_ratings]
    user_rating_map = {chip_id: rating for chip_id, rating in user_ratings}

    chips_data = (
        db.query(
            Chip,
            func.avg(ChipPreference.rating),
            func.count(ChipPreference.rating),
        )
        .outerjoin(ChipPreference, ChipPreference.chip_id == Chip.id)
        .filter(Chip.id.in_(chip_ids))
        .group_by(Chip.id)
        .all()
    )

    return [
        {
            "id": chip.id,
            "name": chip.name,
            "average_rating": round(float(avg_rating or 0), 1),
            "rating_count": rating_count or 0,
            "user_rating": user_rating_map.get(chip.id),
            "image_path": chip.image_path,
        }
        for chip, avg_rating, rating_count in chips_data
    ]


# СРЕДНИЕ ОЦЕНКИ ДРУЗЕЙ

@router.get("/{user_id}/friends-average-rating")
def get_friends_average_rating(
    user_id: int,
    db: Session = Depends(get_db),
):
    """ Средние оценки друзей пользователя"""
    get_user_or_404(db, user_id)
    following_ids = (
        db.query(UserFollow.following_id)
        .filter(UserFollow.follower_id == user_id)
        .all()
    )
    friend_ids = [fid[0] for fid in following_ids]

    if not friend_ids:
        return []

    friends_data = []
    for friend_id in friend_ids:
        friend = db.query(User).filter(User.id == friend_id).first()
        if friend is None:
            continue

        avg_rating = db.query(func.avg(ChipPreference.rating)).filter(
            ChipPreference.user_id == friend_id,
            ChipPreference.rating.isnot(None),
        ).scalar()

        friends_data.append({
            "id": friend.id,
            "username": friend.username,
            "display_name": friend.display_name,
            "avatar_url": friend.avatar_url,
            "average_rating": round(float(avg_rating or 0), 1),
        })

    friends_data.sort(key=lambda x: x["average_rating"], reverse=True)
    return friends_data


# ЧИПСЫ, КОТОРЫЕ КОММЕНТИРОВАЛ

@router.get("/{user_id}/commented-chips")
def get_commented_chips(
    user_id: int,
    db: Session = Depends(get_db),
):
    """ Чипсы, которые комментировал пользователь"""
    get_user_or_404(db, user_id)
    chips_data = (
        db.query(
            Chip,
            func.count(ChipComment.id).filter(ChipComment.user_id == user_id),
            func.sum(ChipComment.likes_count + ChipComment.dislikes_count),
        )
        .join(ChipComment, ChipComment.chip_id == Chip.id)
        .filter(ChipComment.user_id == user_id)
        .group_by(Chip.id)
        .order_by(func.count(ChipComment.id).filter(ChipComment.user_id == user_id).desc())
        .all()
    )

    return [
        {
            "id": chip.id,
            "name": chip.name,
            "image_path": chip.image_path,
            "my_comments_count": comments_count or 0,
            "reactions_count": reactions_count or 0,
        }
        for chip, comments_count, reactions_count in chips_data
    ]


# /stats/{user_id}                          GET - общая статистика
# /stats/{user_id}/favorites                GET - любимчики
# /stats/{user_id}/tried                    GET - пробовал
# /stats/{user_id}/ratings                  GET - оценки
# /stats/{user_id}/friends-average-rating   GET - средние оценки друзей
# /stats/{user_id}/commented-chips          GET - комментированные чипсы