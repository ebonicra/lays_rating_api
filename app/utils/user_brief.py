from app.models.user import User
from app.schemas.follow import UserBriefResponse


def get_user_brief(user: User) -> UserBriefResponse:
    """Преобразовать User в краткую информацию"""
    return UserBriefResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=f"/users/avatars/{user.avatar_path}" if user.avatar_path else None,
    )