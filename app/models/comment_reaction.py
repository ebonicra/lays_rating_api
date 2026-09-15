from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.chip_comment import ChipComment
    from app.models.user import User


class CommentReaction(Base):
    """Лайк или дизлайк на комментарий"""
    __tablename__ = "comment_reactions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    comment_id: Mapped[int] = mapped_column(
        ForeignKey("chip_comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # True = лайк, False = дизлайк
    is_like: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ===== СВЯЗИ =====

    user: Mapped["User"] = relationship(
        back_populates="comment_reactions",
        lazy="selectin",
    )

    comment: Mapped["ChipComment"] = relationship(
        back_populates="reactions",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "comment_id", name="uq_user_comment_reaction"),
        Index("ix_comment_reactions_user_like", "user_id", "is_like"),
        Index("ix_comment_reactions_comment_like", "comment_id", "is_like"),
        Index("ix_comment_reactions_user_comment", "user_id", "comment_id"),
    )

    def __repr__(self) -> str:
        reaction_type = "👍" if self.is_like else "👎"
        return (
            f"<CommentReaction {reaction_type} "
            f"user_id={self.user_id} comment_id={self.comment_id}>"
        )

    # ===== PROPERTIES =====

    @property
    def reaction_type(self) -> str:
        return "like" if self.is_like else "dislike"

    @property
    def emoji(self) -> str:
        return "👍" if self.is_like else "👎"

    # ===== ХЕЛПЕРЫ =====

    def toggle(self) -> None:
        self.is_like = not self.is_like

    @classmethod
    def create_like(cls, user_id: int, comment_id: int) -> "CommentReaction":
        return cls(user_id=user_id, comment_id=comment_id, is_like=True)

    @classmethod
    def create_dislike(cls, user_id: int, comment_id: int) -> "CommentReaction":
        return cls(user_id=user_id, comment_id=comment_id, is_like=False)