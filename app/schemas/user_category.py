from pydantic import BaseModel


class UserCategoryResponse(BaseModel):
    categories: list[str]
    russia_only: bool  # ← добавили
    available_only: bool  # ← добавили


class UserCategoryUpdate(BaseModel):
    categories: list[str] | None = None
    russia_only: bool | None = None  # ← добавили
    available_only: bool | None = None  # ← добавили