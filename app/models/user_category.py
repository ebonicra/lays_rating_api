from typing import TYPE_CHECKING

from sqlalchemy import String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserCategory(Base):
    __tablename__ = "user_category"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    category: Mapped[str] = mapped_column(
        String(50),  # Ограничим длину категории
        nullable=False
    )

    # Отношение к пользователю
    user: Mapped["User"] = relationship(
        back_populates="user_categories",
        lazy="selectin"
    )

    # Уникальность: один пользователь не может выбрать одну категорию дважды
    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_category"),
        Index("ix_user_category_user_id_category", "user_id", "category"),
    )

    def __repr__(self) -> str:
        return f"<UserCategory user_id={self.user_id} category={self.category}>"