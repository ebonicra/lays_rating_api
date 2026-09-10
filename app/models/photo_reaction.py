from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.user_photo import UserPhoto


class PhotoReaction(Base):
    __tablename__ = "photo_reactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    photo_id: Mapped[int] = mapped_column(
        ForeignKey("user_photos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Связи
    user: Mapped["User"] = relationship(back_populates="photo_reactions")
    photo: Mapped["UserPhoto"] = relationship(back_populates="reactions")

    __table_args__ = (
        UniqueConstraint("user_id", "photo_id", name="uq_user_photo_reaction"),
    )

    def __repr__(self) -> str:
        return f"<PhotoReaction user_id={self.user_id} photo_id={self.photo_id}>"