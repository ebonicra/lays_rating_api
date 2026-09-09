from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.chip_comment import ChipComment
from app.models.comment_reaction import CommentReaction
from app.models.chip_preference import ChipPreference
from app.models.news import News

from app.models.chip import Chip
from app.models.user import User
from app.schemas.chip_comment import (
    ChipCommentResponse,
    ChipCommentListResponse,
    ChipCommentCreate,
    ChipCommentUpdate,
    CommentReactionUpdate,
    CommentReactionResponse,
    CommentAuthorResponse,
)
from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/chips",
    tags=["Chip Comments"]
)


# ----- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ -----

def _get_user_reaction(db: Session, comment_id: int, user_id: int) -> CommentReactionResponse | None:
    """Получить реакцию пользователя на комментарий"""
    reaction = (
        db.query(CommentReaction)
        .filter(
            CommentReaction.comment_id == comment_id,
            CommentReaction.user_id == user_id,
        )
        .first()
    )
    if reaction is None:
        return None
    return CommentReactionResponse(is_liked=reaction.is_like)


def _comment_to_response(
    db: Session,
    comment: ChipComment,
    current_user_id: int,
) -> ChipCommentResponse:
    """Преобразовать модель комментария в ответ с реакцией пользователя"""

    # Получаем рейтинг пользователя к этому чипсу
    preference = (
        db.query(ChipPreference)
        .filter(
            ChipPreference.user_id == comment.user_id,
            ChipPreference.chip_id == comment.chip_id,
        )
        .first()
    )

    return ChipCommentResponse(
        id=comment.id,
        user=CommentAuthorResponse(
            id=comment.user.id,
            username=comment.user.display_name,
            avatar_url=f"/users/avatars/{comment.user.avatar_path}" if comment.user.avatar_path else None,
        ),
        text=comment.text,
        rating=preference.rating if preference else None,  # ← рейтинг из ChipPreference
        likes_count=comment.likes_count,
        dislikes_count=comment.dislikes_count,
        user_reaction=_get_user_reaction(db, comment.id, current_user_id),
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


# ----- ЭНДПОИНТЫ -----

@router.get("/{chip_id}/comments", response_model=ChipCommentListResponse)
def get_comments(
    chip_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("newest", pattern="^(newest|oldest|popular)$"),  # ← regex → pattern
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить список комментариев к чипсам с пагинацией"""
    
    chip = db.query(Chip).filter(Chip.id == chip_id).first()
    if chip is None:
        raise HTTPException(status_code=404, detail="Chip not found")
    
    query = db.query(ChipComment).filter(ChipComment.chip_id == chip_id)
    
    if sort_by == "newest":
        query = query.order_by(ChipComment.created_at.desc())
    elif sort_by == "oldest":
        query = query.order_by(ChipComment.created_at.asc())
    elif sort_by == "popular":
        query = query.order_by(
            (ChipComment.likes_count - ChipComment.dislikes_count).desc()
        )
    
    total_count = query.count()
    offset = (page - 1) * per_page
    comments = query.offset(offset).limit(per_page).all()
    
    comment_responses = [
        _comment_to_response(db, comment, current_user.id)
        for comment in comments
    ]
    
    return ChipCommentListResponse(
        comments=comment_responses,
        total_count=total_count,
    )


@router.post("/{chip_id}/comments", response_model=ChipCommentResponse)
def create_comment(
    chip_id: int,
    data: ChipCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать комментарий к чипсам"""
    
    chip = db.query(Chip).filter(Chip.id == chip_id).first()
    if chip is None:
        raise HTTPException(status_code=404, detail="Chip not found")
    
    comment = ChipComment(
        user_id=current_user.id,
        chip_id=chip_id,
        text=data.text,
        # rating убираем - его нет в модели
    )
    
    db.add(comment)
    db.commit()
    db.refresh(comment)

    news = News(
        event_type="friend_comment",
        user_id=current_user.id,
        chip_id=chip_id,
        comment_id=comment.id,  # ← добавили
        text=comment.text,
    )
    db.add(news)
    db.commit()

    return _comment_to_response(db, comment, current_user.id)


@router.put("/{chip_id}/comments/{comment_id}", response_model=ChipCommentResponse)
def update_comment(
    chip_id: int,
    comment_id: int,
    data: ChipCommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Редактировать свой комментарий"""
    
    comment = (
        db.query(ChipComment)
        .filter(
            ChipComment.id == comment_id,
            ChipComment.chip_id == chip_id,
        )
        .first()
    )
    
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")
    
    comment.text = data.text
    db.commit()
    db.refresh(comment)

    news = (
        db.query(News)
        .filter(News.comment_id == comment.id)
        .first()
    )
    if news:
        news.text = comment.text
        db.commit()
    
    return _comment_to_response(db, comment, current_user.id)


@router.delete("/{chip_id}/comments/{comment_id}")
def delete_comment(
    chip_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Удалить свой комментарий"""
    
    comment = (
        db.query(ChipComment)
        .filter(
            ChipComment.id == comment_id,
            ChipComment.chip_id == chip_id,
        )
        .first()
    )
    
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")
    
    db.delete(comment)
    db.commit()

    news = (
        db.query(News)
        .filter(News.comment_id == comment.id)
        .first()
    )
    if news:
        db.delete(news)
        db.commit()
    
    return {"message": "Comment deleted"}


@router.post("/{chip_id}/comments/{comment_id}/reaction", response_model=CommentReactionResponse)
def set_reaction(
    chip_id: int,
    comment_id: int,
    data: CommentReactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Поставить лайк или дизлайк на комментарий"""
    
    comment = (
        db.query(ChipComment)
        .filter(
            ChipComment.id == comment_id,
            ChipComment.chip_id == chip_id,
        )
        .first()
    )
    
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    existing_reaction = (
        db.query(CommentReaction)
        .filter(
            CommentReaction.comment_id == comment_id,
            CommentReaction.user_id == current_user.id,
        )
        .first()
    )
    
    if existing_reaction:
        if existing_reaction.is_like != data.is_like:
            if existing_reaction.is_like:
                comment.likes_count -= 1
            else:
                comment.dislikes_count -= 1
            
            existing_reaction.is_like = data.is_like
            if data.is_like:
                comment.likes_count += 1
            else:
                comment.dislikes_count += 1
    else:
        reaction = CommentReaction(
            user_id=current_user.id,
            comment_id=comment_id,
            is_like=data.is_like,
        )
        db.add(reaction)
        
        if data.is_like:
            comment.likes_count += 1
        else:
            comment.dislikes_count += 1
    
    db.commit()
    
    return CommentReactionResponse(is_liked=data.is_like)


@router.delete("/{chip_id}/comments/{comment_id}/reaction")
def remove_reaction(
    chip_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Убрать свою реакцию с комментария"""
    
    comment = (
        db.query(ChipComment)
        .filter(
            ChipComment.id == comment_id,
            ChipComment.chip_id == chip_id,
        )
        .first()
    )
    
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    reaction = (
        db.query(CommentReaction)
        .filter(
            CommentReaction.comment_id == comment_id,
            CommentReaction.user_id == current_user.id,
        )
        .first()
    )
    
    if reaction is None:
        raise HTTPException(status_code=404, detail="Reaction not found")
    
    if reaction.is_like:
        comment.likes_count -= 1
    else:
        comment.dislikes_count -= 1
    
    db.delete(reaction)
    db.commit()
    
    return {"message": "Reaction removed"}