from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.chip import Chip
    from app.models.user import User


class ChipPreference(Base):
    __tablename__ = "chip_preferences"

    id: Mapped[int] = mapped_column(
        primary_key=True, 
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chip_id: Mapped[int] = mapped_column(
        ForeignKey("chips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    is_tried: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ===== СВЯЗИ =====

    user: Mapped["User"] = relationship(
        back_populates="chip_preferences",
        lazy="selectin",
    )

    chip: Mapped["Chip"] = relationship(
        back_populates="preferences",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "chip_id", name="uq_user_chip"),
        CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_rating_range"),
        Index("ix_chip_preferences_user_chip", "user_id", "chip_id"),
        Index("ix_chip_preferences_user_favorite", "user_id", "is_favorite"),
        Index("ix_chip_preferences_chip_rating", "chip_id", "rating"),
    )

    def __repr__(self) -> str:
        return (
            f"<ChipPreference user_id={self.user_id} "
            f"chip_id={self.chip_id} rating={self.rating}>"
        )

    @property
    def is_rated(self) -> bool:
        """Проверяет, поставлен ли рейтинг"""
        return self.rating is not None