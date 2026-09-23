from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user_role import UserRole

if TYPE_CHECKING:
    from app.models.user_follow import UserFollow
    from app.models.chip_preference import ChipPreference
    from app.models.user_filter import UserFilter
    from app.models.chip_comment import ChipComment
    from app.models.comment_reaction import CommentReaction
    from app.models.user_photo import UserPhoto
    from app.models.photo_reaction import PhotoReaction
    from app.models.news import News
    from app.models.poll_vote import PollVote


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True, 
        index=True
    )

    username: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    display_name: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default=UserRole.USER.value,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    avatar_path: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    filter_russia_only: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    filter_available_only: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ===== СВЯЗИ =====

    user_filters: Mapped[list["UserFilter"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    news: Mapped[list["News"]] = relationship(
        back_populates="user",
        foreign_keys="News.user_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    targeted_news: Mapped[list["News"]] = relationship(
        back_populates="target_user",
        foreign_keys="News.target_user_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    chip_preferences: Mapped[list["ChipPreference"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    user_filters: Mapped[list["UserFilter"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    comments: Mapped[list["ChipComment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    comment_reactions: Mapped[list["CommentReaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Подписки: на кого я подписан
    following: Mapped[list["UserFollow"]] = relationship(
        foreign_keys="UserFollow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Подписчики: кто подписан на меня
    followers: Mapped[list["UserFollow"]] = relationship(
        foreign_keys="UserFollow.following_id",
        back_populates="following",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    photos: Mapped[list["UserPhoto"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    photo_reactions: Mapped[list["PhotoReaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    poll_votes: Mapped[list["PollVote"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ===== PROPERTIES =====

    @property
    def is_admin(self) -> bool:
        """Админ или супер-админ"""
        return self.role in (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value)

    @property
    def is_super_admin(self) -> bool:
        """Только супер-админ"""
        return self.role == UserRole.SUPER_ADMIN.value

    @property
    def avatar_url(self) -> str | None:
        """Относительный URL аватарки"""
        if self.avatar_path:
            return f"/users/avatars/{self.avatar_path}"
        return None

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username} role={self.role}>"