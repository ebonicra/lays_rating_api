from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.user import UserBriefResponse


class CommentReactionResponse(BaseModel):
    """ Реакция текущего пользователя на комментарий """
    is_liked: bool | None = None

class ChipCommentResponse(BaseModel):
    """ Комментарий для отображения """
    id: int
    user: UserBriefResponse
    text: str
    rating: int | None = None
    likes_count: int = 0
    dislikes_count: int = 0
    user_reaction: CommentReactionResponse | None = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class ChipCommentListResponse(BaseModel):
    """ Список комментариев с общим количеством (для пагинации) """
    comments: list[ChipCommentResponse]
    total_count: int

class ChipCommentCreate(BaseModel):
    """ Создание комментария """
    chip_id: int
    text: str = Field(min_length=1, max_length=1000)


class ChipCommentUpdate(BaseModel):
    """ Редактирование своего комментария """
    text: str = Field(min_length=1, max_length=1000)


class CommentReactionUpdate(BaseModel):
    """ Поставить/изменить реакцию на комментарий """
    is_like: bool

class CommentReactionUser(BaseModel):
    """ Краткая инфа о пользователе, поставившем реакцию """
    id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None


class CommentReactionsListResponse(BaseModel):
    """ Список лайкнувших и дизлайкнувших комментарий """
    likes: list[CommentReactionUser]
    dislikes: list[CommentReactionUser]