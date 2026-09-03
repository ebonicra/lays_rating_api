from pydantic import BaseModel, Field
from datetime import datetime



class CommentReactionResponse(BaseModel):
    is_liked: bool | None = None  # None — нет реакции, True — лайк, False — дизлайк
    
    class Config:
        from_attributes = True


class CommentAuthorResponse(BaseModel):
    id: int
    username: str
    avatar_url: str | None = None
    
    class Config:
        from_attributes = True


class ChipCommentResponse(BaseModel):
    """Комментарий для отображения"""
    id: int
    user: CommentAuthorResponse
    text: str
    rating: int | None  # Оценка, которую автор поставил чипсам
    likes_count: int
    dislikes_count: int
    user_reaction: CommentReactionResponse | None = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChipCommentListResponse(BaseModel):
    comments: list[ChipCommentResponse]
    total_count: int





# ----- Запросы -----

class ChipCommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    
    class Config:
        from_attributes = True


class ChipCommentUpdate(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    
    class Config:
        from_attributes = True


class CommentReactionUpdate(BaseModel):
    is_like: bool
    
    class Config:
        from_attributes = True