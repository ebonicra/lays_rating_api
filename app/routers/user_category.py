from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_category import UserCategory
from app.models.user import User
from app.schemas.user_category import (
    UserCategoryResponse,
    UserCategoryUpdate,
)
from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/preferences",
    tags=["Preferences"],
)


@router.get("",response_model=UserCategoryResponse)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    preferences = (
        db.query(UserCategory)
        .filter(UserCategory.user_id == current_user.id)
        .all()
    )

    return {
        "categories": [
            item.category
            for item in preferences
        ]
    }


@router.put("", response_model=UserCategoryResponse)
def update_preferences(
    data: UserCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    (
        db.query(UserCategory)
        .filter(UserCategory.user_id == current_user.id)
        .delete()
    )

    for category in data.categories:
        preference = UserCategory(
            user_id=current_user.id,
            category=category,
        )
        db.add(preference)
    db.commit()
    return data