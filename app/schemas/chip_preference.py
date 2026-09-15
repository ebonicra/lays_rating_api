from pydantic import BaseModel, Field


class ChipPreferenceResponse(BaseModel):
    """Предпочтения пользователя к чипсам"""
    rating: int | None = None
    is_favorite: bool = False
    is_tried: bool = False

    class Config:
        from_attributes = True


class ChipPreferenceUpdate(BaseModel):
    """Обновление предпочтений (все поля опциональные)"""
    rating: int | None = Field(default=None, ge=1, le=5)
    is_favorite: bool | None = None
    is_tried: bool | None = None