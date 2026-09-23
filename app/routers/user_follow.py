from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.validators import get_user_or_404, get_user_brief
from app.database import get_db
from app.models.news import News
from app.models.news_type import NewsType
from app.models.user import User
from app.models.user_follow import UserFollow
from app.schemas.common import MessageResponse
from app.schemas.user_follow import (
    FollowersListResponse,
    FollowingListResponse,
    IsFollowingResponse,
    UserFollowResponse,
)

router = APIRouter(
    prefix="/follows",
    tags=["Follows"],
)


# ПОДПИСКИ

@router.post("/{user_id}", response_model=UserFollowResponse)
def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Подписаться на пользователя """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя подписаться на себя")

    get_user_or_404(db, user_id)
    existing = (
        db.query(UserFollow)
        .filter(
            UserFollow.follower_id == current_user.id,
            UserFollow.following_id == user_id,
        )
        .first()
    )
    if existing:
        return existing

    follow = UserFollow(
        follower_id=current_user.id,
        following_id=user_id,
    )
    db.add(follow)
    db.commit()
    db.refresh(follow)

    news = News(
        event_type=NewsType.NEW_FOLLOWER.value,
        user_id=current_user.id,
        target_user_id=user_id,
    )
    db.add(news)
    db.commit()

    return follow

@router.delete("/{user_id}", response_model=MessageResponse)
def unfollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Отписаться от пользователя"""
    follow = (
        db.query(UserFollow)
        .filter(
            UserFollow.follower_id == current_user.id,
            UserFollow.following_id == user_id,
        )
        .first()
    )
    if follow is None:
        raise HTTPException(
            status_code=404,
            detail="Вы не подписаны на этого пользователя",
        )

    db.delete(follow)
    db.commit()

    return MessageResponse(message="Вы отписались")


# СПИСКИ ПОДПИСОК

@router.get("/{user_id}/followers", response_model=FollowersListResponse)
def get_followers(
    user_id: int,
    db: Session = Depends(get_db),
):
    """ Список подписчиков пользователя """
    get_user_or_404(db, user_id)
    total_count = (
        db.query(func.count(UserFollow.id))
        .filter(UserFollow.following_id == user_id)
        .scalar()
    )

    follows = (
        db.query(UserFollow)
        .join(User, User.id == UserFollow.follower_id)
        .filter(UserFollow.following_id == user_id)
        .order_by(func.lower(User.display_name).asc())
        .all()
    )

    return FollowersListResponse(
        users=[get_user_brief(f.follower) for f in follows],
        total_count=total_count,
    )


@router.get("/{user_id}/following", response_model=FollowingListResponse)
def get_following(
    user_id: int,
    db: Session = Depends(get_db),
):
    """ Список подписок пользователя """
    get_user_or_404(db, user_id)
    total_count = (
        db.query(func.count(UserFollow.id))
        .filter(UserFollow.follower_id == user_id)
        .scalar()
    )

    follows = (
        db.query(UserFollow)
        .join(User, User.id == UserFollow.following_id)
        .filter(UserFollow.follower_id == user_id)
        .order_by(func.lower(User.display_name).asc())
        .all()
    )

    return FollowingListResponse(
        users=[get_user_brief(f.following) for f in follows],
        total_count=total_count,
    )


# ПРОВЕРКА ПОДПИСКИ

@router.get("/{user_id}/is-following", response_model=IsFollowingResponse)
def check_following(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Проверить, подписан ли текущий пользователь на `user_id` """
    get_user_or_404(db, user_id)

    is_following = (
        db.query(UserFollow)
        .filter(
            UserFollow.follower_id == current_user.id,
            UserFollow.following_id == user_id,
        )
        .first()
        is not None
    )

    followers_count = (
        db.query(func.count(UserFollow.id))
        .filter(UserFollow.following_id == user_id)
        .scalar()
    )

    following_count = (
        db.query(func.count(UserFollow.id))
        .filter(UserFollow.follower_id == user_id)
        .scalar()
    )

    return IsFollowingResponse(
        is_following=is_following,
        followers_count=followers_count,
        following_count=following_count,
    )


# /follows/{user_id}               POST   - подписаться
# /follows/{user_id}               DELETE - отписаться
# /follows/{user_id}/followers     GET    - подписчики юзера
# /follows/{user_id}/following     GET    - на кого подписан юзер
# /follows/{user_id}/is-following  GET    - проверка подписки