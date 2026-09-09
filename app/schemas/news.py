# schemas/news.py
from pydantic import BaseModel

class NewsChipData(BaseModel):
    name: str
    image_path: str | None = None

class NewsCreate(BaseModel):
    event_type: str  # "admin_post", "rumor"
    text: str | None = None
    extra_data: dict | None = None