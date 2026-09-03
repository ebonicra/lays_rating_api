from pydantic import BaseModel


class UserCategoryResponse(BaseModel):
    categories: list[str]


class UserCategoryUpdate(BaseModel):
    categories: list[str]