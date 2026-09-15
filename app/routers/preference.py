from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.validators import get_chip_or_404
from app.database import get_db
from app.models.chip_preference import ChipPreference
from app.models.user import User
from app.schemas.chip_preference import (
    ChipPreferenceResponse,
    ChipPreferenceUpdate,
)

router = APIRouter(
    prefix="/preferences",
    tags=["Preferences"],
)


# ПРЕДПОЧТЕНИЯ ПО ЧИПСАМ

@router.get("/{chip_id}", response_model=ChipPreferenceResponse)
def get_preference(
    chip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Получить предпочтение текущего пользователя по чипсам """
    get_chip_or_404(db, chip_id)

    preference = (
        db.query(ChipPreference)
        .filter(
            ChipPreference.user_id == current_user.id,
            ChipPreference.chip_id == chip_id,
        )
        .first()
    )

    if preference is None:
        return ChipPreferenceResponse(
            rating=None,
            is_favorite=False,
            is_tried=False,
        )

    return preference


@router.put("/{chip_id}", response_model=ChipPreferenceResponse)
def update_preference(
    chip_id: int,
    data: ChipPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Обновить предпочтение по чипсам """
    get_chip_or_404(db, chip_id)

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


@router.delete("/{chip_id}/rating", response_model=ChipPreferenceResponse)
def delete_rating(
    chip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Удалить свою оценку по чипсам """
    get_chip_or_404(db, chip_id)

    preference = (
        db.query(ChipPreference)
        .filter(
            ChipPreference.user_id == current_user.id,
            ChipPreference.chip_id == chip_id,
        )
        .first()
    )
    if preference is None:
        raise HTTPException(status_code=404, detail="Предпочтение не найдено")

    preference.rating = None
    db.commit()
    db.refresh(preference)

    return preference


# /preferences/{chip_id}         GET    - получить предпочтение
# /preferences/{chip_id}         PUT    - обновить
# /preferences/{chip_id}/rating  DELETE - удалить оценку