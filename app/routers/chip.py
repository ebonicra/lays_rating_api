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
from app.schemas.chip import ChipResponse, ChipRatingWithUserResponse, ChipStatsResponse, ChipCategoryStats

router = APIRouter(
    prefix="/chips",
    tags=["Chips"],
)


# ЧИПСЫ

@router.get("/stats", response_model=ChipStatsResponse)
def get_chip_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Статистика по категориям чипсов (по всей базе, без фильтров):
    - total: сколько всего чипсов в категории
    - tried: сколько из них пользователь попробовал
    """
    # total по категориям
    total_rows = (
        db.query(Chip.category, func.count(Chip.id))
        .group_by(Chip.category)
        .all()
    )
    totals = {cat: cnt for cat, cnt in total_rows}

    # tried по категориям
    tried_rows = (
        db.query(Chip.category, func.count(ChipPreference.id))
        .join(
            ChipPreference,
            ChipPreference.chip_id == Chip.id,
        )
        .filter(
            ChipPreference.user_id == current_user.id,
            ChipPreference.is_tried.is_(True),
        )
        .group_by(Chip.category)
        .all()
    )
    trieds = {cat: cnt for cat, cnt in tried_rows}

    # Собираем итоговый словарь по всем категориям из enum,
    # чтобы фронт всегда получал запись для каждой категории
    stats: dict[str, ChipCategoryStats] = {}
    for ct in settings.DEFAULT_CATEGORIES:
        key = ct.value if hasattr(ct, "value") else str(ct)
        stats[key] = ChipCategoryStats(
            total=totals.get(ct.value if hasattr(ct, "value") else ct, 0),
            tried=trieds.get(ct.value if hasattr(ct, "value") else ct, 0),
        )

    return ChipStatsResponse(stats=stats)


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

    # Загружаем предпочтения одним запросом
    chip_ids = [chip.id for chip in chips]
    prefs = (
        db.query(ChipPreference)
        .filter(
            ChipPreference.user_id == current_user.id,
            ChipPreference.chip_id.in_(chip_ids),
        )
        .all()
    )
    prefs_map = {p.chip_id: p for p in prefs}

    return [
        _format_chip_response(db, chip, current_user.id, prefs_map)
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
    prefs = (
        db.query(ChipPreference)
        .filter(
            ChipPreference.user_id == current_user.id,
            ChipPreference.chip_id == chip.id,
        )
        .first()
    )
    prefs_map = {chip.id: prefs} if prefs else {}

    return _format_chip_response(db, chip, current_user.id, prefs_map)


@router.get("/{chip_id}/ratings", response_model=list[ChipRatingWithUserResponse])
def get_chip_ratings(
    chip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Список оценок чипса с пользователями """
    get_chip_or_404(db, chip_id)

    ratings = (
        db.query(ChipPreference)
        .filter(
            ChipPreference.chip_id == chip_id,
            ChipPreference.rating.isnot(None),
        )
        .order_by(ChipPreference.updated_at.desc())   # сортировка по дате
        .all()
    )

    return [
        {
            "user": {
                "id": r.user.id,
                "username": r.user.username,
                "display_name": r.user.display_name,
                "avatar_url": r.user.avatar_url,
            },
            "rating": r.rating,
            "created_at": r.updated_at,
        }
        for r in ratings
    ]


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
    prefs_map: dict[int, ChipPreference],
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

    pref = prefs_map.get(chip.id)
    user_rating = pref.rating if pref else None
    is_favorite = pref.is_favorite if pref else False
    is_tried = pref.is_tried if pref else False

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
            "user_rating": user_rating,
        },
        "comment_count": comment_count,
        "is_favorite": is_favorite,
        "is_tried": is_tried,
    }


# /chips               GET  - список чипсов (с фильтром по категориям)
# /chips/{chip_id}     GET  - конкретные чипсы
# /chips/images/{file} GET  - картинка чипсов