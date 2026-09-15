# models/poll_vote.py
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.news import News


class PollVote(Base):
    __tablename__ = "poll_votes"

    id: Mapped[int] = mapped_column(primary_key=True)
    news_id: Mapped[int] = mapped_column(
        ForeignKey("news.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    option_index: Mapped[int] = mapped_column(Integer, nullable=False)  # индекс варианта (0-3)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Связи
    user: Mapped["User"] = relationship(back_populates="poll_votes")
    news: Mapped["News"] = relationship(back_populates="poll_votes")

    __table_args__ = (
        UniqueConstraint("news_id", "user_id", name="uq_user_poll_vote"),
    )

    def __repr__(self) -> str:
        return f"<PollVote news_id={self.news_id} user_id={self.user_id} option={self.option_index}>"