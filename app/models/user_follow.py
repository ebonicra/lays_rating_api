from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserFollow(Base):
    __tablename__ = "user_follows"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Кто подписался
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # На кого подписался
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ===== СВЯЗИ =====

    follower: Mapped["User"] = relationship(
        foreign_keys=[follower_id],
        back_populates="following",
        lazy="selectin",
    )

    following: Mapped["User"] = relationship(
        foreign_keys=[following_id],
        back_populates="followers",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_user_follow"),
        Index("ix_user_follow_follower", "follower_id"),
        Index("ix_user_follow_following", "following_id"),
    )

    def __repr__(self) -> str:
        return f"<UserFollow follower={self.follower_id} → following={self.following_id}>"