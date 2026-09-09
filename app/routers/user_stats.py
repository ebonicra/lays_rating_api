from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.chip_preference import ChipPreference
from app.models.chip_comment import ChipComment
from app.models.chip import Chip
from app.models.follow import Follow

from app.core.dependencies import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["User Stats"]
)


# ===== СТАТИСТИКА ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ =====

@router.get("/me/stats")
def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Общая статистика текущего пользователя"""
    
    ratings_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == current_user.id,
        ChipPreference.rating.isnot(None),
    ).scalar() or 0
    
    favorites_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == current_user.id,
        ChipPreference.is_favorite == True,
    ).scalar() or 0
    
    tried_count = db.query(func.count(ChipPreference.id)).filter(
        ChipPreference.user_id == current_user.id,
        ChipPreference.is_tried == True,
    ).scalar() or 0
    
    comments_count = db.query(func.count(ChipComment.id)).filter(
        ChipComment.user_id == current_user.id
    ).scalar() or 0
    
    avg_rating = db.query(func.avg(ChipPreference.rating)).filter(
        ChipPreference.user_id == current_user.id,
        ChipPreference.rating.isnot(None),
    ).scalar()

    followers_count = db.query(func.count(Follow.id)).filter(
        Follow.following_id == current_user.id
    ).scalar() or 0
    
    following_count = db.query(func.count(Follow.id)).filter(
        Follow.follower_id == current_user.id
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


@router.get("/me/favorites")
def get_favorite_chips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список любимых чипсов текущего пользователя"""
    
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
                    ChipPreference.user_id == current_user.id,
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
            "rating_count": rating_count if rating_count else 0,
            "favorite_count": favorite_count if favorite_count else 0,
            "image_path": chip.image_path,
        }
        for chip, avg_rating, rating_count, favorite_count in favorites
    ]


@router.get("/me/tried")
def get_tried_chips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список чипсов, которые пробовал текущий пользователь"""
    
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
                    ChipPreference.user_id == current_user.id,
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
            "rating_count": rating_count if rating_count else 0,
            "tried_count": tried_count if tried_count else 0,
            "image_path": chip.image_path,
        }
        for chip, avg_rating, rating_count, tried_count in tried_chips
    ]


@router.get("/me/ratings")
def get_my_ratings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список чипсов с оценками текущего пользователя"""
    
    # Мои оценки — чтобы получить id чипсов и мою оценку
    my_ratings = (
        db.query(ChipPreference.chip_id, ChipPreference.rating)
        .filter(
            ChipPreference.user_id == current_user.id,
            ChipPreference.rating.isnot(None),
        )
        .all()
    )
    
    if not my_ratings:
        return []
    
    chip_ids = [chip_id for chip_id, _ in my_ratings]
    my_rating_map = {chip_id: rating for chip_id, rating in my_ratings}
    
    # Общая статистика по этим чипсам (от ВСЕХ пользователей)
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
            "rating_count": rating_count if rating_count else 0,
            "my_rating": my_rating_map.get(chip.id),
            "image_path": chip.image_path,
        }
        for chip, avg_rating, rating_count in chips_data
    ]


# ===== ПУБЛИЧНАЯ СТАТИСТИКА =====

@router.get("/{user_id}/stats")
def get_public_user_stats(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Общая статистика другого пользователя"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
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
        ChipComment.user_id == user_id
    ).scalar() or 0
    
    avg_rating = db.query(func.avg(ChipPreference.rating)).filter(
        ChipPreference.user_id == user_id,
        ChipPreference.rating.isnot(None),
    ).scalar()
    
    followers_count = db.query(func.count(Follow.id)).filter(
        Follow.following_id == user_id
    ).scalar() or 0
    
    following_count = db.query(func.count(Follow.id)).filter(
        Follow.follower_id == user_id
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


@router.get("/{user_id}/favorites")
def get_public_favorite_chips(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список любимых чипсов другого пользователя"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    chips_data = (
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
            "rating_count": rating_count if rating_count else 0,
            "favorite_count": favorite_count if favorite_count else 0,
            "image_path": chip.image_path,
        }
        for chip, avg_rating, rating_count, favorite_count in chips_data
    ]


@router.get("/{user_id}/tried")
def get_public_tried_chips(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список чипсов, которые пробовал другой пользователь"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
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
            "rating_count": rating_count if rating_count else 0,
            "tried_count": tried_count if tried_count else 0,
            "image_path": chip.image_path,
        }
        for chip, avg_rating, rating_count, tried_count in tried_chips
    ]

@router.get("/{user_id}/ratings")
def get_public_ratings(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список чипсов с оценками другого пользователя"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Оценки пользователя
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
    
    # Общая статистика по этим чипсам (от ВСЕХ пользователей)
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
            "rating_count": rating_count if rating_count else 0,
            "my_rating": user_rating_map.get(chip.id),
            "image_path": chip.image_path,
        }
        for chip, avg_rating, rating_count in chips_data
    ]

@router.get("/{user_id}/friends-average-rating")
def get_friends_average_rating(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список друзей (подписок) с их средней оценкой"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Получаем подписки пользователя
    following_ids = (
        db.query(Follow.following_id)
        .filter(Follow.follower_id == user_id)
        .all()
    )
    friend_ids = [fid[0] for fid in following_ids]
    
    if not friend_ids:
        return []
    
    # Для каждого друга считаем среднюю оценку
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
            "avatar_url": f"/users/avatars/{friend.avatar_path}" if friend.avatar_path else None,
            "average_rating": round(float(avg_rating or 0), 1),
        })
    
    # Сортируем по убыванию средней оценки
    friends_data.sort(key=lambda x: x["average_rating"], reverse=True)
    
    return friends_data


@router.get("/{user_id}/commented-chips")
def get_commented_chips(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список чипсов, которые комментировал пользователь"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Получаем чипсы с количеством комментариев пользователя и реакциями
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
            "average_rating": 0,  # ← не используется
            "rating_count": 0,     # ← не используется
            "favorite_count": 0,   # ← не используется
            "tried_count": 0,      # ← не используется
            "my_rating": None,     # ← не используется
            "my_comments_count": comments_count,
            "reactions_count": reactions_count or 0,
            "image_path": chip.image_path,
        }
        for chip, comments_count, reactions_count in chips_data
    ]