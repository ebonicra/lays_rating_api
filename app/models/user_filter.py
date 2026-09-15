from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserFilter(Base):
    __tablename__ = "user_filters"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    russia_only: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    available_only: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ===== СВЯЗИ =====

    user: Mapped["User"] = relationship(
        back_populates="user_filters",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_filter"),
    )

    def __repr__(self) -> str:
        return f"<UserFilter user_id={self.user_id} category={self.category}>"