from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserBriefResponse


class UserPhotoResponse(BaseModel):
    """ Полная информация о фото пользователя """
    id: int
    user: UserBriefResponse
    image_path: str
    likes_count: int
    is_liked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PhotoListResponse(BaseModel):
    """ Список фото с общим количеством"""
    photos: list[UserPhotoResponse]
    total_count: int


class PhotoLikersResponse(BaseModel):
    """ Список тех, кто лайкнул фото"""
    users: list[UserBriefResponse]
    total_count: int


class PhotoReactionResponse(BaseModel):
    """ Ответ на лайк/анлайк фото"""
    is_liked: bool
    likes_count: int