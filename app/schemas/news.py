from pydantic import BaseModel, Field


class NewsChipData(BaseModel):
    """ Данные о чипсах для новостей """
    name: str | None = None
    image_path: str | None = None


class PollOptionCreate(BaseModel):
    """ Один вариант ответа в опросе """
    text: str = Field(min_length=1, max_length=200)
    image_path: str | None = None


class PollCreate(BaseModel):
    """ Данные опроса """
    question: str = Field(min_length=1, max_length=500)
    options: list[PollOptionCreate] = Field(min_length=2, max_length=4)


class NewsCreate(BaseModel):
    """  Создание новости (только для админа) """
    event_type: str = Field(pattern="^(admin_post|rumor|poll)$")
    text: str | None = Field(default=None, max_length=2000)
    extra_data: dict | None = None


class NewsUpdate(BaseModel):
    text: str | None = Field(default=None, max_length=2000)
    extra_data: dict | None = None


class NewsReactionRequest(BaseModel):
    is_like: bool


class NewsReactionUser(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None


class NewsReactionsResponse(BaseModel):
    likes: list[NewsReactionUser]
    dislikes: list[NewsReactionUser]