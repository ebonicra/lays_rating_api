from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Тип события:
    # - friend_comment  (комментарий друга)
    # - game_record     (рекорд в игре)
    # - new_chip        (новый вкус)
    # - admin_post      (пост админа)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Кто автор (для friend_comment, game_record)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
    
    # Связанные чипсы (для friend_comment, new_chip)
    chip_id: Mapped[int | None] = mapped_column(
        ForeignKey("chips.id"),
        nullable=True,
    )
    
    # Текст новости
    text: Mapped[str | None] = mapped_column(Text, nullable=True)

    comment_id: Mapped[int | None] = mapped_column(  # ← добавили
        ForeignKey("chip_comments.id"), nullable=True
    )

    
    # Для рекордов — количество очков
    extra_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )