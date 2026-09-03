from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.chip import Chip


class ChipPreference(Base):
    __tablename__ = "chip_preferences"

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

    rating: Mapped[int | None] = mapped_column(
        nullable=True
        # Валидацию через CheckConstraint добавим в __table_args__
    )

    is_favorite: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True  # Для частых запросов "показать избранное"
    )

    is_tried: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True  # Для фильтрации по пробованным
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 👇 РАСКОММЕНТИРУЙ ЭТО!
    # Отношения
    user: Mapped["User"] = relationship(
        back_populates="chip_preferences",  # Это имя должно быть в User
        lazy="selectin"
    )

    chip: Mapped["Chip"] = relationship(
        back_populates="preferences",  # Это имя должно быть в Chip
        lazy="selectin"
    )

    __table_args__ = (
        # Уникальность: один пользователь - один чипс
        UniqueConstraint("user_id", "chip_id", name="uq_user_chip"),
        
        # Валидация рейтинга
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_rating_range"),
        
        # Индексы для частых запросов
        Index("ix_chip_preferences_user_chip", "user_id", "chip_id"),
        Index("ix_chip_preferences_user_favorite", "user_id", "is_favorite"),
        Index("ix_chip_preferences_chip_rating", "chip_id", "rating"),
    )

    def __repr__(self) -> str:
        return f"<ChipPreference user_id={self.user_id} chip_id={self.chip_id} rating={self.rating}>"

    @property
    def is_rated(self) -> bool:
        """Проверяет, поставлен ли рейтинг"""
        return self.rating is not None