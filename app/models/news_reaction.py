from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.news import News


class NewsReaction(Base):
    __tablename__ = "news_reactions"

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

    is_like: Mapped[bool] = mapped_column(Boolean, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    news: Mapped["News"] = relationship(back_populates="reactions")
    user: Mapped["User"] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("news_id", "user_id", name="uq_news_reaction_user"),
        Index("ix_news_reactions_news_like", "news_id", "is_like"),
    )