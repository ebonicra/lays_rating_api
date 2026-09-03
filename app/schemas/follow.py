from pydantic import BaseModel
from datetime import datetime


class UserBriefResponse(BaseModel):
    """Краткая информация о пользователе для списков"""
    id: int
    username: str
    display_name: str
    avatar_url: str | None = None
    
    class Config:
        from_attributes = True


class FollowResponse(BaseModel):
    """Информация о подписке"""
    id: int
    follower_id: int
    following_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class FollowersListResponse(BaseModel):
    """Список подписчиков"""
    users: list[UserBriefResponse]
    total_count: int


class FollowingListResponse(BaseModel):
    """Список подписок"""
    users: list[UserBriefResponse]
    total_count: int


class IsFollowingResponse(BaseModel):
    """Проверка подписки"""
    is_following: bool
    followers_count: int
    following_count: int