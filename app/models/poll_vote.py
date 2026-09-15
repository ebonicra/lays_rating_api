from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.news import News
    from app.models.user import User


class PollVote(Base):
    """Голос пользователя в опросе"""
    __tablename__ = "poll_votes"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    news_id: Mapped[int] = mapped_column(
        ForeignKey("news.id", ondelete="CASCADE"),
        nullable=False,
        # index=True покрыт UniqueConstraint ниже
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # ← нужен для поиска голосов юзера
    )

    # Индекс выбранного варианта (0-3)
    option_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ===== СВЯЗИ =====

    user: Mapped["User"] = relationship(
        back_populates="poll_votes",
        lazy="selectin",
    )

    news: Mapped["News"] = relationship(
        back_populates="poll_votes",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("news_id", "user_id", name="uq_user_poll_vote"),
    )

    def __repr__(self) -> str:
        return (
            f"<PollVote news_id={self.news_id} "
            f"user_id={self.user_id} option={self.option_index}>"
        )