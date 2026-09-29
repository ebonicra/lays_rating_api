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

router = APIRouter(
    prefix="/game",
    tags=["Game"],
)


@router.post("/records", response_model=GameRecordResponse)
def save_score(
    data: GameRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Сохранить результат игры """
    record = GameRecord(
        user_id=current_user.id,
        score=data.score,
    )
    db.add(record)
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
        created_at=record.created_at,
    )


@router.get("/leaderboard", response_model=GameLeaderboardResponse)
def get_leaderboard(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Топ игроков по лучшему результату.
    Одна строка на пользователя: его максимальный score.
    """
    # Подзапрос: user_id -> max(score), count(*)
    subq = (
        db.query(
            GameRecord.user_id.label("user_id"),
            func.max(GameRecord.score).label("best_score"),
            func.count(GameRecord.id).label("games_played"),
        )
        .group_by(GameRecord.user_id)
        .subquery()
    )

    rows = (
        db.query(
            User,
            subq.c.best_score,
            subq.c.games_played,
        )
        .join(subq, subq.c.user_id == User.id)
        .order_by(subq.c.best_score.desc())
        .limit(limit)
        .all()
    )

    items = [
        GameLeaderboardItem(
            user=UserBriefResponse(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
            ),
            best_score=best_score,
            games_played=games_played,
        )
        for user, best_score, games_played in rows
    ]

    # Мой лучший результат
    my_best = (
        db.query(func.max(GameRecord.score))
        .filter(GameRecord.user_id == current_user.id)
        .scalar()
    )

    return GameLeaderboardResponse(
        items=items,
        my_best=my_best,
    )


@router.get("/records/me", response_model=list[GameRecordResponse])
def get_my_records(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Последние результаты текущего пользователя """
    records = (
        db.query(GameRecord)
        .filter(GameRecord.user_id == current_user.id)
        .order_by(GameRecord.created_at.desc())
        .limit(limit)
        .all()
    )

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
            created_at=r.created_at,
        )
        for r in records
    ]