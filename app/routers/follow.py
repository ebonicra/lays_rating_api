from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.follow import Follow
from app.models.news import News
from app.core.dependencies import get_current_user
from app.utils.user_brief import get_user_brief  # ← импортируем общую функцию

from app.schemas.follow import (
    FollowResponse,
    FollowersListResponse,
    FollowingListResponse,
    IsFollowingResponse,
)

router = APIRouter(
    prefix="/users",
    tags=["follows"]
)


@router.post("/{user_id}/follow", response_model=FollowResponse)
def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Подписаться на пользователя"""
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя подписаться на себя")
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    existing = (
        db.query(Follow)
        .filter(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id,
        )
        .first()
    )
    if existing:
        return existing
    
    follow = Follow(
        follower_id=current_user.id,
        following_id=user_id,
    )
    db.add(follow)
    db.commit()
    db.refresh(follow)

    news = News(
        event_type="new_follower",
        user_id=current_user.id,  # ← кто подписался
        chip_id=None,
    )
    db.add(news)
    db.commit()

    return follow


@router.delete("/{user_id}/follow")
def unfollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Отписаться от пользователя"""
    
    follow = (
        db.query(Follow)
        .filter(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id,
        )
        .first()
    )
    if follow is None:
        raise HTTPException(status_code=404, detail="Вы не подписаны на этого пользователя")
    
    db.delete(follow)
    db.commit()
    return {"message": "Вы отписались"}


@router.get("/{user_id}/followers", response_model=FollowersListResponse)
def get_followers(
    user_id: int,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
):
    """Список подписчиков пользователя"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    total_count = (
        db.query(func.count(Follow.id))
        .filter(Follow.following_id == user_id)
        .scalar()
    )
    
    follows = (
        db.query(Follow)
        .filter(Follow.following_id == user_id)
        .order_by(Follow.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    
    users = [get_user_brief(f.follower) for f in follows]  # ← общая функция
    return FollowersListResponse(
        users=users,
        total_count=total_count,
    )


@router.get("/{user_id}/following", response_model=FollowingListResponse)
def get_following(
    user_id: int,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
):
    """Список подписок пользователя"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    total_count = (
        db.query(func.count(Follow.id))
        .filter(Follow.follower_id == user_id)
        .scalar()
    )
    
    follows = (
        db.query(Follow)
        .filter(Follow.follower_id == user_id)
        .order_by(Follow.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    
    users = [get_user_brief(f.following) for f in follows]  # ← общая функция
    return FollowingListResponse(
        users=users,
        total_count=total_count,
    )


@router.get("/{user_id}/is-following", response_model=IsFollowingResponse)
def check_following(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Проверить, подписан ли текущий пользователь на user_id"""
    
    is_following = (
        db.query(Follow)
        .filter(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id,
        )
        .first()
        is not None
    )
    
    followers_count = (
        db.query(func.count(Follow.id))
        .filter(Follow.following_id == user_id)
        .scalar()
    )
    
    following_count = (
        db.query(func.count(Follow.id))
        .filter(Follow.follower_id == user_id)
        .scalar()
    )
    
    return IsFollowingResponse(
        is_following=is_following,
        followers_count=followers_count,
        following_count=following_count,
    )