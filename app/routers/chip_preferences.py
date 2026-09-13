from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.chip_preference import ChipPreference
from app.models.chip import Chip
from app.models.user import User

from app.schemas.chip_preference import (
    ChipPreferenceResponse,
    ChipPreferenceUpdate,
)

from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/chips",
    tags=["Chip Preferences"]
)


@router.get("/{chip_id}/preference", response_model=ChipPreferenceResponse)
def get_preference(
    chip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preference = (
        db.query(ChipPreference)
        .filter(
            ChipPreference.user_id == current_user.id,
            ChipPreference.chip_id == chip_id,
        )
        .first()
    )

    if preference is None:
        return {
            "rating": None,
            "is_favorite": False,
            "is_tried": False,
        }

    return preference



@router.put("/{chip_id}/preference", response_model=ChipPreferenceResponse)
def update_preference(
    chip_id: int,
    data: ChipPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # Проверяем, существует ли чипс
    chip = db.query(Chip).filter(Chip.id == chip_id).first()
    if chip is None:
        raise HTTPException(status_code=404, detail="Chip not found")


    preference = (
        db.query(ChipPreference)
        .filter(
            ChipPreference.user_id == current_user.id,
            ChipPreference.chip_id == chip_id,
        )
        .first()
    )

    if preference is None:
        preference = ChipPreference(
            user_id=current_user.id,
            chip_id=chip_id,
        )
        db.add(preference)

    if data.rating is not None:
        preference.rating = data.rating

    if data.is_favorite is not None:
        preference.is_favorite = data.is_favorite

    if data.is_tried is not None:
        preference.is_tried = data.is_tried

    db.commit()
    db.refresh(preference)
    return preference

@router.delete("/{chip_id}/preference/rating")
def delete_rating(
    chip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preference = (
        db.query(ChipPreference)
        .filter(
            ChipPreference.user_id == current_user.id,
            ChipPreference.chip_id == chip_id,
        )
        .first()
    )

    if preference is None:
        raise HTTPException(status_code=404, detail="Оценка не найдена")

    preference.rating = None
    db.commit()
    db.refresh(preference)

    # Возвращаем словарь, а не модель — избегаем рекурсии
    return {
        "rating": preference.rating,
        "is_favorite": preference.is_favorite,
        "is_tried": preference.is_tried,
    }