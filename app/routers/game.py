from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.game_record import GameRecord
from app.models.user import User
from app.schemas.game_record import (
    GameLeaderboardItem,
    GameLeaderboardResponse,
    GameRecordCreate,
    GameRecordResponse,
)
from app.schemas.user import UserBriefResponse

router = APIRouter(prefix="/game", tags=["Game"])


@router.post("/records", response_model=GameRecordResponse)
def save_score(
    data: GameRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Сохранить результат игры. Возвращает лучший счёт и флаг рекорда. """
    previous_best = current_user.best_game_score or 0
    is_new_record = data.score > previous_best

    record = GameRecord(
        user_id=current_user.id,
        score=data.score,
    )
    db.add(record)

    if is_new_record:
        current_user.best_game_score = data.score

    db.commit()
    db.refresh(record)

    return GameRecordResponse(
        id=record.id,
        user=UserBriefResponse(
            id=current_user.id,
            username=current_user.username,
            display_name=current_user.display_name,
            avatar_url=current_user.avatar_url,
        ),
        score=record.score,
        best_score=current_user.best_game_score,
        is_new_record=is_new_record,
        created_at=record.created_at,
    )


@router.get("/leaderboard", response_model=GameLeaderboardResponse)
def get_leaderboard(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Топ игроков по лучшему результату. """
    rows = (
        db.query(User)
        .filter(User.best_game_score > 0)
        .order_by(User.best_game_score.desc())
        .limit(limit)
        .all()
    )

    # games_played одним запросом
    user_ids = [u.id for u in rows]
    counts = {}
    if user_ids:
        for uid, cnt in (
            db.query(GameRecord.user_id, func.count(GameRecord.id))
            .filter(GameRecord.user_id.in_(user_ids))
            .group_by(GameRecord.user_id)
            .all()
        ):
            counts[uid] = cnt

    items = [
        GameLeaderboardItem(
            user=UserBriefResponse(
                id=u.id,
                username=u.username,
                display_name=u.display_name,
                avatar_url=u.avatar_url,
            ),
            best_score=u.best_game_score,
            games_played=counts.get(u.id, 0),
        )
        for u in rows
    ]

    return GameLeaderboardResponse(
        items=items,
        my_best=current_user.best_game_score or 0,
    )


@router.get("/records/me", response_model=list[GameRecordResponse])
def get_my_records(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Последние игры текущего пользователя. """
    records = (
        db.query(GameRecord)
        .filter(GameRecord.user_id == current_user.id)
        .order_by(GameRecord.created_at.desc())
        .limit(limit)
        .all()
    )

    best = current_user.best_game_score or 0
    return [
        GameRecordResponse(
            id=r.id,
            user=UserBriefResponse(
                id=current_user.id,
                username=current_user.username,
                display_name=current_user.display_name,
                avatar_url=current_user.avatar_url,
            ),
            score=r.score,
            best_score=best,
            is_new_record=False,
            created_at=r.created_at,
        )
        for r in records
    ]