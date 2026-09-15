from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.chip_preference import ChipPreference
    from app.models.chip_comment import ChipComment
    from app.models.news import News


class Chip(Base):
    __tablename__ = "chips"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    image_path: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )

    collection: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    release_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # ===== СВЯЗИ =====

    news: Mapped[list["News"]] = relationship(
        back_populates="chip",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    preferences: Mapped[list["ChipPreference"]] = relationship(
        back_populates="chip",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    comments: Mapped[list["ChipComment"]] = relationship(
        back_populates="chip",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_chip_name"),
        Index("ix_chips_category_available", "category", "available"),
        Index("ix_chips_name_category", "name", "category"),
    )

    def __repr__(self) -> str:
        return f"<Chip id={self.id} name={self.name} category={self.category}>"