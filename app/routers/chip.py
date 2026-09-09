from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import os

from app.database import get_db
from app.models.chip import Chip
from app.models.chip_preference import ChipPreference
from app.models.chip_comment import ChipComment
from app.schemas.chip import ChipResponse
from app.core.dependencies import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/chips",
    tags=["chips"]
)

BASE_DIR = Path(__file__).resolve().parent.parent
CHIPS_DIR = BASE_DIR / "backend" / "uploads" / "chips"
os.makedirs(CHIPS_DIR, exist_ok=True)



@router.get("/", response_model=list[ChipResponse])
def get_chips(
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),  # ← добавил
    current_user: User = Depends(get_current_user),  # ← для user_rating
):
    query = db.query(Chip)
    if categories:
        query = query.filter(Chip.category.in_(categories))

    chips = query.all()
    result = []

    for chip in chips:
        rating = (
            db.query(
                func.avg(ChipPreference.rating),
                func.count(ChipPreference.rating)
            )
            .filter(
                ChipPreference.chip_id == chip.id,
                ChipPreference.rating.isnot(None)
            )
            .first()
        )

        average = rating[0] or 0
        count = rating[1]

        user_rating = (
            db.query(ChipPreference.rating)
            .filter(
                ChipPreference.chip_id == chip.id,
                ChipPreference.user_id == current_user.id  # ← вместо 1
            )
            .first()
        )

        comment_count = (
            db.query(func.count(ChipComment.id))
            .filter(ChipComment.chip_id == chip.id)
            .scalar()
        )

        result.append({
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
        })

    return result


@router.get("/{chip_id}", response_model=ChipResponse)
def get_chip(
    chip_id: int,
    db: Session = Depends(get_db),  # ← добавил
    current_user: User = Depends(get_current_user),  # ← для user_rating
):
    chip = db.query(Chip).filter(Chip.id == chip_id).first()

    if chip is None:
        raise HTTPException(status_code=404, detail="Chip not found")

    rating = (
        db.query(
            func.avg(ChipPreference.rating),
            func.count(ChipPreference.rating)
        )
        .filter(
            ChipPreference.chip_id == chip.id,
            ChipPreference.rating.isnot(None)
        )
        .first()
    )

    user_rating = (
        db.query(ChipPreference.rating)
        .filter(
            ChipPreference.chip_id == chip.id,
            ChipPreference.user_id == current_user.id  # ← вместо 1
        )
        .first()
    )

    comment_count = (
        db.query(func.count(ChipComment.id))
        .filter(ChipComment.chip_id == chip.id)
        .scalar()
    )

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
            "average": round(float(rating[0] or 0), 2),
            "count": rating[1],
            "user_rating": user_rating[0] if user_rating else None,
        },
        "comment_count": comment_count,
    }


@router.get("/images/{filename}")
def get_chip_image(filename: str):
    filepath = CHIPS_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return FileResponse(
        str(filepath),
        headers={"Cache-Control": "public, max-age=86400"},  # ← кэш на сутки
    )