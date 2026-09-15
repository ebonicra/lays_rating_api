from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserBriefResponse


class UserFollowResponse(BaseModel):
    """ Информация о подписке """
    id: int
    follower_id: int
    following_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FollowersListResponse(BaseModel):
    """ Список подписчиков (кто подписан на меня) """
    users: list[UserBriefResponse]
    total_count: int


class FollowingListResponse(BaseModel):
    """ Список подписок (на кого я подписан) """
    users: list[UserBriefResponse]
    total_count: int


class IsFollowingResponse(BaseModel):
    """ Проверка подписки + счётчики """
    is_following: bool
    followers_count: int
    following_count: int