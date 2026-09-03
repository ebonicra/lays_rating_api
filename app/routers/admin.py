from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chip import Chip
from app.models.user import User
from app.core.dependencies import get_current_admin
from app.schemas.chip import ChipUpdate, ChipAdminResponse

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)


@router.put("/chips/{chip_id}", response_model=ChipAdminResponse)
def update_chip(
    chip_id: int,
    data: ChipUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),  # ← только админ!
):
    """Обновить карточку чипсов"""
    
    chip = db.query(Chip).filter(Chip.id == chip_id).first()
    
    if chip is None:
        raise HTTPException(status_code=404, detail="Чипсы не найдены")
    
    # Обновляем только те поля, которые переданы (не None)
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(chip, field, value)
    
    db.commit()
    db.refresh(chip)
    
    return chip