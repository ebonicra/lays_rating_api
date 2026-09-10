from pydantic import BaseModel
from datetime import datetime


class PhotoAuthorResponse(BaseModel):
    """Краткая информация об авторе фото"""
    id: int
    username: str
    display_name: str
    avatar_url: str | None = None

    class Config:
        from_attributes = True


class UserPhotoResponse(BaseModel):
    """Информация о фото"""
    id: int
    user: PhotoAuthorResponse
    image_path: str
    likes_count: int
    is_liked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PhotoListResponse(BaseModel):
    """Список фото"""
    photos: list[UserPhotoResponse]
    total_count: int


class PhotoLikersResponse(BaseModel):
    """Список тех, кто лайкнул фото"""
    users: list[PhotoAuthorResponse]
    total_count: int


class PhotoReactionResponse(BaseModel):
    """Ответ на реакцию"""
    is_liked: bool
    likes_count: int