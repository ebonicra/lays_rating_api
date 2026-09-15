from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Для избежания циклических импортов
if TYPE_CHECKING:
    from app.models.follow import Follow
    from app.models.chip_preference import ChipPreference
    from app.models.user_category import UserCategory
    from app.models.chip_comment import ChipComment
    from app.models.comment_reaction import CommentReaction
    from app.models.user_photo import UserPhoto  # ← добавили
    from app.models.photo_reaction import PhotoReaction  # ← добавили
    from app.models.poll_vote import PollVote


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    username: Mapped[str] = mapped_column(
        String(50),  # Ограничим длину
        unique=True,
        index=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),  # Для хеша пароля
        nullable=False
    )

    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # Используем timezone-aware
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    avatar_path: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None
    )

    # Отношения с правильными названиями и типами
    chip_preferences: Mapped[list["ChipPreference"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"  # Оптимизация запросов
    )

    user_categories: Mapped[list["UserCategory"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    comments: Mapped[list["ChipComment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    comment_reactions: Mapped[list["CommentReaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Подписки (на кого я подписан)
    following: Mapped[list["Follow"]] = relationship(
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan",
    )

    # Подписчики (кто подписан на меня)
    followers: Mapped[list["Follow"]] = relationship(
        foreign_keys="Follow.following_id",
        back_populates="following",
        cascade="all, delete-orphan",
    )


    photos: Mapped[list["UserPhoto"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Реакции на фото
    photo_reactions: Mapped[list["PhotoReaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    poll_votes: Mapped[list["PollVote"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"

    @property
    def avatar_url(self) -> str | None:
        """Полный URL аватарки"""
        if self.avatar_path:
            return f"/users/avatars/{self.avatar_path}"
        return None