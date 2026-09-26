from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.user import UserBriefResponse


class FeedbackCreate(BaseModel):
    type: str = Field(pattern="^(bug|suggestion|complaint|thanks|question|other)$")
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=2000)
    image_paths: list[str] | None = None  # см. пункт 3


class FeedbackResponse(BaseModel):
    id: int
    user: UserBriefResponse
    type: str
    title: str
    text: str
    image_paths: list[str] = []
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    items: list[FeedbackResponse]
    total_count: int
    unread_count: int