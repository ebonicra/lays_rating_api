from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.chip_comment import ChipComment


class CommentReaction(Base):
    """Лайк или дизлайк на комментарий"""
    __tablename__ = "comment_reactions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    comment_id: Mapped[int] = mapped_column(
        ForeignKey("chip_comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # True = лайк, False = дизлайк
    is_like: Mapped[bool] = mapped_column(
        nullable=False,
        index=True  # Для фильтрации по типу реакции
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True  # Для сортировки по дате
    )

    # Связи
    user: Mapped["User"] = relationship(
        back_populates="comment_reactions",
        lazy="selectin"
    )

    comment: Mapped["ChipComment"] = relationship(
        back_populates="reactions",
        lazy="selectin"
    )

    __table_args__ = (
        # Уникальность: один пользователь - одна реакция на комментарий
        UniqueConstraint(
            "user_id",
            "comment_id",
            name="uq_user_comment_reaction"
        ),
        
        # Индексы для частых запросов
        Index("ix_comment_reactions_user_like", "user_id", "is_like"),
        Index("ix_comment_reactions_comment_like", "comment_id", "is_like"),
        Index("ix_comment_reactions_user_comment", "user_id", "comment_id"),
    )

    def __repr__(self) -> str:
        reaction_type = "👍" if self.is_like else "👎"
        return f"<CommentReaction {reaction_type} user_id={self.user_id} comment_id={self.comment_id}>"

    @property
    def reaction_type(self) -> str:
        """Возвращает тип реакции в виде строки"""
        return "like" if self.is_like else "dislike"

    @property
    def emoji(self) -> str:
        """Возвращает эмодзи реакции"""
        return "👍" if self.is_like else "👎"

    def toggle(self) -> None:
        """Переключает реакцию (лайк ↔ дизлайк)"""
        self.is_like = not self.is_like

    @classmethod
    def create_like(cls, user_id: int, comment_id: int) -> "CommentReaction":
        """Создает лайк"""
        return cls(user_id=user_id, comment_id=comment_id, is_like=True)

    @classmethod
    def create_dislike(cls, user_id: int, comment_id: int) -> "CommentReaction":
        """Создает дизлайк"""
        return cls(user_id=user_id, comment_id=comment_id, is_like=False)