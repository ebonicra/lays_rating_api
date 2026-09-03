from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, CheckConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.chip import Chip
    from app.models.comment_reaction import CommentReaction


class ChipComment(Base):
    __tablename__ = "chip_comments"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    chip_id: Mapped[int] = mapped_column(
        ForeignKey("chips.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    text: Mapped[str] = mapped_column(
        Text,  # Используем Text вместо String для длинных комментариев
        nullable=False
    )

    # Счётчики для быстрого доступа (денормализация)
    likes_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    dislikes_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True  # Для сортировки по дате
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Связи
    user: Mapped["User"] = relationship(
        back_populates="comments",
        lazy="selectin"
    )

    chip: Mapped["Chip"] = relationship(
        back_populates="comments",
        lazy="selectin"
    )

    reactions: Mapped[list["CommentReaction"]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CommentReaction.created_at"  # Сортируем реакции по дате
    )

    __table_args__ = (
        CheckConstraint("LENGTH(text) > 0", name="ck_comment_not_empty"),
        CheckConstraint("LENGTH(text) <= 1000", name="ck_comment_max_length"),
        CheckConstraint("likes_count >= 0", name="ck_likes_non_negative"),
        CheckConstraint("dislikes_count >= 0", name="ck_dislikes_non_negative"),
        
        # Индексы для частых запросов
        Index("ix_chip_comments_chip_created", "chip_id", "created_at"),
        Index("ix_chip_comments_user_created", "user_id", "created_at"),
        Index("ix_chip_comments_likes", "chip_id", "likes_count"),
    )

    def __repr__(self) -> str:
        preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"<ChipComment id={self.id} user_id={self.user_id} chip_id={self.chip_id} text='{preview}'>"

    @property
    def total_reactions(self) -> int:
        """Общее количество реакций"""
        return self.likes_count + self.dislikes_count

    @property
    def rating(self) -> int:
        """Рейтинг комментария (лайки минус дизлайки)"""
        return self.likes_count - self.dislikes_count

    def add_like(self) -> None:
        """Увеличить счетчик лайков"""
        self.likes_count += 1

    def remove_like(self) -> None:
        """Уменьшить счетчик лайков"""
        if self.likes_count > 0:
            self.likes_count -= 1

    def add_dislike(self) -> None:
        """Увеличить счетчик дизлайков"""
        self.dislikes_count += 1

    def remove_dislike(self) -> None:
        """Уменьшить счетчик дизлайков"""
        if self.dislikes_count > 0:
            self.dislikes_count -= 1