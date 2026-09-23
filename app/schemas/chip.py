from datetime import datetime

from pydantic import BaseModel, Field


class RatingResponse(BaseModel):
    """ Рейтинг чипсов """
    average: float
    count: int
    user_rating: int | None = None


class ChipResponse(BaseModel):
    """ Полная информация о чипсах (для обычного пользователя) """
    id: int
    name: str
    category: str
    description: str
    image_path: str | None = None
    collection: str | None = None
    release_year: int | None = None
    country: str | None = None
    available: bool
    rating: RatingResponse
    comment_count: int
    is_favorite: bool
    is_tried: bool  

    class Config:
        from_attributes = True


class ChipAdminResponse(BaseModel):
    """ Информация о чипсах для админа (без рейтинга) """
    id: int
    name: str
    category: str
    description: str
    image_path: str | None = None
    collection: str | None = None
    release_year: int | None = None
    country: str | None = None
    available: bool
    class Config:
        from_attributes = True


class ChipCreate(BaseModel):
    """ Создание новых чипсов (только для админа) """
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=1000)
    image_path: str | None = None
    collection: str | None = None
    release_year: int | None = Field(default=None, ge=1900, le=2100)
    country: str | None = None
    available: bool = True


class ChipUpdate(BaseModel):
    """ Обновление чипсов (только для админа) """
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    image_path: str | None = None
    collection: str | None = None
    release_year: int | None = Field(default=None, ge=1900, le=2100)
    country: str | None = None
    available: bool | None = None


class ChipRatingUserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    avatar_url: str | None = None


class ChipRatingWithUserResponse(BaseModel):
    user: ChipRatingUserResponse
    rating: int
    created_at: datetime