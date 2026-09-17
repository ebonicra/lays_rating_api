# app/models/user_filter.py

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserFilter(Base):
    __tablename__ = "user_filters"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    filter: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # ===== СВЯЗИ =====

    user: Mapped["User"] = relationship(
        back_populates="user_filters",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "filter", name="uq_user_filter"),
    )

    def __repr__(self) -> str:
        return f"<UserFilter user_id={self.user_id} filter={self.filter}>"