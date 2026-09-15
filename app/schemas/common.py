from pydantic import BaseModel


class MessageResponse(BaseModel):
    """ Простой ответ с сообщением """
    message: str