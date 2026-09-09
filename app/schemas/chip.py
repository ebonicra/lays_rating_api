from pydantic import BaseModel
from datetime import datetime

class RatingResponse(BaseModel):
    average: float
    count: int
    user_rating: int | None = None


class ChipResponse(BaseModel):
    id: int
    name: str
    category: str
    description: str
    image_path: str

    collection: str | None
    release_year: int | None
    country: str | None
    available: bool
    rating: RatingResponse
    comment_count: int

    class Config:
        from_attributes = True


class ChipCreate(BaseModel):
    name: str
    category: str
    description: str
    image_path: str
    collection: str | None = None
    release_year: int | None = None
    country: str | None = None
    available: bool = True


class ChipUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    image_path: str | None = None
    collection: str | None = None
    release_year: int | None = None
    country: str | None = None
    available: bool | None = None
    
    class Config:
        from_attributes = True


class ChipAdminResponse(BaseModel):
    id: int
    name: str
    category: str
    description: str
    image_path: str
    collection: str
    release_year: int
    country: str
    available: bool
    
    class Config:
        from_attributes = True


class ChipCreate(BaseModel):
    name: str
    category: str
    description: str
    image_path: str | None = None
    collection: str
    country: str
    release_year: int
    available: bool = True
    
    class Config:
        from_attributes = True