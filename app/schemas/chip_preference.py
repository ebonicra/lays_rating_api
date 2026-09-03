from pydantic import BaseModel


class ChipPreferenceResponse(BaseModel):
    rating: int | None
    is_favorite: bool
    is_tried: bool
    class Config:
        from_attributes = True

class ChipPreferenceUpdate(BaseModel):
    rating: int | None = None
    is_favorite: bool | None = None
    is_tried: bool | None = None