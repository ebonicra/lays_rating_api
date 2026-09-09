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



@router.get("", response_model=UserCategoryResponse)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить настройки фильтров пользователя"""
    
    categories = (
        db.query(UserCategory.category)
        .filter(UserCategory.user_id == current_user.id)
        .all()
    )
    
    # Получаем фильтры из первой записи (если есть)
    first_record = (
        db.query(UserCategory)
        .filter(UserCategory.user_id == current_user.id)
        .first()
    )
    
    return {
        "categories": [c[0] for c in categories],
        "russia_only": first_record.russia_only if first_record else False,
        "available_only": first_record.available_only if first_record else False,
    }


@router.put("", response_model=UserCategoryResponse)
def update_preferences(
    data: UserCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить настройки фильтров"""
    
    # Обновляем категории
    if data.categories is not None:
        # Удаляем старые
        db.query(UserCategory).filter(
            UserCategory.user_id == current_user.id
        ).delete()
        
        # Добавляем новые
        for category in data.categories:
            new_category = UserCategory(
                user_id=current_user.id,
                category=category,
                russia_only=data.russia_only if data.russia_only is not None else False,
                available_only=data.available_only if data.available_only is not None else False,
            )
            db.add(new_category)
    
    # Обновляем фильтры
    if data.russia_only is not None or data.available_only is not None:
        user_categories = (
            db.query(UserCategory)
            .filter(UserCategory.user_id == current_user.id)
            .all()
        )
        for uc in user_categories:
            if data.russia_only is not None:
                uc.russia_only = data.russia_only
            if data.available_only is not None:
                uc.available_only = data.available_only
    
    db.commit()
    
    return {
        "categories": data.categories or [],
        "russia_only": data.russia_only if data.russia_only is not None else False,
        "available_only": data.available_only if data.available_only is not None else False,
    }
