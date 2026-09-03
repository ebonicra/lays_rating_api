from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


# models/follow.py
class Follow(Base):
    __tablename__ = "follows"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Кто подписался
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    
    # На кого подписался
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow
    )

    # Связи
    follower: Mapped["User"] = relationship(
        foreign_keys=[follower_id],
        back_populates="following",
    )

    following: Mapped["User"] = relationship(
        foreign_keys=[following_id],
        back_populates="followers",
    )

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id"),
    )