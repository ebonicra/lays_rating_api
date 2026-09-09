from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import String, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.chip_preference import ChipPreference
    from app.models.chip_comment import ChipComment


class Chip(Base):
    __tablename__ = "chips"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(200),  # Ограничим длину названия
        nullable=False,
        index=True  # Для быстрого поиска по названию
    )

    category: Mapped[str] = mapped_column(
        String(50),  # Ограничим длину категории
        nullable=False,
        index=True  # Для фильтрации по категории
    )

    description: Mapped[str] = mapped_column(
        String(1000),  # Длинное описание
        nullable=False
    )

    image_path: Mapped[str] = mapped_column(
        String(500),  # Путь к изображению
        nullable=False
    )

    collection: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    release_year: Mapped[int | None] = mapped_column(
        nullable=True
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    available: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True  # Для фильтрации по доступности
    )

    # Отношения пользователя к чипсам
    preferences: Mapped[list["ChipPreference"]] = relationship(
        back_populates="chip",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    comments: Mapped[list["ChipComment"]] = relationship(
        back_populates="chip",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Уникальность: не может быть двух чипсов с одинаковым названием
    __table_args__ = (
        UniqueConstraint("name", name="uq_chip_name"),
        Index("ix_chips_category_available", "category", "available"),
        Index("ix_chips_name_category", "name", "category"),
    )

    def __repr__(self) -> str:
        return f"<Chip id={self.id} name={self.name} category={self.category}>"
