from pydantic import BaseModel


class UserFilterResponse(BaseModel):
    """ Настройки фильтров пользователя """
    categories: list[str]
    russia_only: bool
    available_only: bool

class UserFilterUpdate(BaseModel):
    """ Обновление фильтров пользователя """
    categories: list[str] | None = None
    russia_only: bool | None = None
    available_only: bool | None = None