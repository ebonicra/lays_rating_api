from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.news_type import NewsType

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.chip import Chip
    from app.models.chip_comment import ChipComment
    from app.models.poll_vote import PollVote


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True,
    )

    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    chip_id: Mapped[int | None] = mapped_column(
        ForeignKey("chips.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("chip_comments.id"), nullable=True, index=True,
    )

    text: Mapped[str | None] = mapped_column(Text, nullable=True)

    extra_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # ===== СВЯЗИ =====

    user: Mapped["User | None"] = relationship(
        back_populates="news",
        foreign_keys=[user_id],   # ← обязательно
        lazy="selectin",
    )

    target_user: Mapped["User | None"] = relationship(
        back_populates="targeted_news",   # ← добавить обратную связь
        foreign_keys=[target_user_id],
        lazy="selectin",
    )
    
    target_user: Mapped["User | None"] = relationship(
        foreign_keys=[target_user_id],
        lazy="selectin",
    )

    chip: Mapped["Chip | None"] = relationship(
        back_populates="news",
        lazy="selectin",
    )

    comment: Mapped["ChipComment | None"] = relationship(
        lazy="selectin",
    )

    poll_votes: Mapped[list["PollVote"]] = relationship(
        back_populates="news",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_news_user_created", "user_id", "created_at"),
        Index("ix_news_event_created", "event_type", "created_at"),
        Index("ix_news_target_created", "target_user_id", "created_at"),
    )