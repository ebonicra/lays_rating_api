from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.user import UserBriefResponse


class GameRecordCreate(BaseModel):
    score: int = Field(ge=0, le=100000)


class GameRecordResponse(BaseModel):
    id: int
    user: UserBriefResponse
    score: int
    best_score: int
    is_new_record: bool
    created_at: datetime


class GameLeaderboardItem(BaseModel):
    user: UserBriefResponse
    best_score: int
    games_played: int


class GameLeaderboardResponse(BaseModel):
    items: list[GameLeaderboardItem]
    my_best: int | None = None