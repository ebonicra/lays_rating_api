from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class GameRecord(Base):
    __tablename__ = "game_records"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    score: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="game_records",
        lazy="selectin",
    )

    __table_args__ = (
        # Для выборки «лучший результат пользователя»
        Index("ix_game_records_user_score", "user_id", "score"),
        # Для общего топа
        Index("ix_game_records_score_created", "score", "created_at"),
    )