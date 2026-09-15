from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.validators import get_chip_or_404
from app.database import get_db
from app.models.chip import Chip
from app.models.chip_comment import ChipComment
from app.models.chip_preference import ChipPreference
from app.models.user import User
from app.schemas.chip import ChipResponse

router = APIRouter(
    prefix="/chips",
    tags=["Chips"],
)


# ЧИПСЫ

@router.get("", response_model=list[ChipResponse])
def get_chips(
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Список чипсов с рейтингом и комментариями """
    query = db.query(Chip)

    if categories:
        query = query.filter(Chip.category.in_(categories))

    chips = query.all()

    return [
        _format_chip_response(db, chip, current_user.id)
        for chip in chips
    ]


@router.get("/{chip_id}", response_model=ChipResponse)
def get_chip(
    chip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Информация о конкретных чипсах """
    chip = get_chip_or_404(db, chip_id)
    return _format_chip_response(db, chip, current_user.id)


# ОТДАЧА КАРТИНОК

@router.get("/images/{filename}")
def get_chip_image(filename: str):
    """ Получить картинку чипсов по имени файла """
    filepath = settings.CHIP_IMAGES_DIR / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(
        str(filepath),
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ВСПОМОГАТЕЛЬНЫЕ

def _format_chip_response(
    db: Session,
    chip: Chip,
    current_user_id: int,
) -> dict:
    """ Формирует ответ для чипсов с рейтингом """
    rating = (
        db.query(
            func.avg(ChipPreference.rating),
            func.count(ChipPreference.rating),
        )
        .filter(
            ChipPreference.chip_id == chip.id,
            ChipPreference.rating.isnot(None),
        )
        .first()
    )
    average = rating[0] or 0
    count = rating[1] or 0

    user_rating = (
        db.query(ChipPreference.rating)
        .filter(
            ChipPreference.chip_id == chip.id,
            ChipPreference.user_id == current_user_id,
        )
        .first()
    )

    comment_count = (
        db.query(func.count(ChipComment.id))
        .filter(ChipComment.chip_id == chip.id)
        .scalar()
    ) or 0

    return {
        "id": chip.id,
        "name": chip.name,
        "category": chip.category,
        "description": chip.description,
        "image_path": chip.image_path,
        "collection": chip.collection,
        "release_year": chip.release_year,
        "country": chip.country,
        "available": chip.available,
        "rating": {
            "average": round(float(average), 2),
            "count": count,
            "user_rating": user_rating[0] if user_rating else None,
        },
        "comment_count": comment_count,
    }


# /chips               GET  - список чипсов (с фильтром по категориям)
# /chips/{chip_id}     GET  - конкретные чипсы
# /chips/images/{file} GET  - картинка чипсов