from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.validators import (
    get_chip_or_404,
    get_comment_or_404,
    get_comment_owned_by_user_or_404,
)
from app.database import get_db
from app.models.chip_comment import ChipComment
from app.models.chip_preference import ChipPreference
from app.models.comment_reaction import CommentReaction
from app.models.news import News
from app.models.news_type import NewsType
from app.models.user import User
from app.schemas.chip_comment import (
    ChipCommentCreate,
    ChipCommentListResponse,
    ChipCommentResponse,
    ChipCommentUpdate,
    CommentReactionResponse,
    CommentReactionUpdate,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserBriefResponse

router = APIRouter(
    prefix="/comments",
    tags=["Comments"],
)


# КОММЕНТАРИИ

@router.get("", response_model=ChipCommentListResponse)
def get_comments(
    chip_id: int = Query(..., description="ID чипсов, к которым комментарии"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("newest", pattern="^(newest|oldest|popular)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """  Список комментариев к чипсам """
    get_chip_or_404(db, chip_id)

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

    return ChipCommentListResponse(
        comments=[
            _comment_to_response(db, c, current_user.id)
            for c in comments
        ],
        total_count=total_count,
    )


@router.post("", response_model=ChipCommentResponse)
def create_comment(
    data: ChipCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Создать комментарий к чипсам """
    get_chip_or_404(db, data.chip_id)

    comment = ChipComment(
        user_id=current_user.id,
        chip_id=data.chip_id,
        text=data.text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    news = News(
        event_type=NewsType.FRIEND_COMMENT.value,
        user_id=current_user.id,
        chip_id=data.chip_id,
        comment_id=comment.id,
        text=comment.text,
    )
    db.add(news)
    db.commit()

    return _comment_to_response(db, comment, current_user.id)


@router.put("/{comment_id}", response_model=ChipCommentResponse)
def update_comment(
    comment_id: int,
    data: ChipCommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Редактировать свой комментарий """
    comment = get_comment_owned_by_user_or_404(db, comment_id, current_user.id)

    comment.text = data.text
    db.commit()
    db.refresh(comment)

    news = db.query(News).filter(News.comment_id == comment.id).first()
    if news:
        news.text = comment.text
        db.commit()

    return _comment_to_response(db, comment, current_user.id)


@router.delete("/{comment_id}", response_model=MessageResponse)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Удалить свой комментарий """
    comment = get_comment_owned_by_user_or_404(db, comment_id, current_user.id)

    news = db.query(News).filter(News.comment_id == comment.id).first()
    if news:
        db.delete(news)

    db.delete(comment)
    db.commit()

    return MessageResponse(message="Комментарий удалён")


# РЕАКЦИИ НА КОММЕНТАРИИ

@router.post(
    "/{comment_id}/reaction",
    response_model=CommentReactionResponse,
)
def set_reaction(
    comment_id: int,
    data: CommentReactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Поставить лайк или дизлайк на комментарий """
    comment = get_comment_or_404(db, comment_id)

    existing = (
        db.query(CommentReaction)
        .filter(
            CommentReaction.comment_id == comment_id,
            CommentReaction.user_id == current_user.id,
        )
        .first()
    )

    if existing:
        if existing.is_like != data.is_like:
            if existing.is_like:
                comment.likes_count = max(0, comment.likes_count - 1)
                comment.dislikes_count += 1
            else:
                comment.dislikes_count = max(0, comment.dislikes_count - 1)
                comment.likes_count += 1
            existing.is_like = data.is_like
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


@router.delete(
    "/{comment_id}/reaction",
    response_model=MessageResponse,
)
def remove_reaction(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ Убрать свою реакцию с комментария """
    comment = get_comment_or_404(db, comment_id)

    reaction = (
        db.query(CommentReaction)
        .filter(
            CommentReaction.comment_id == comment_id,
            CommentReaction.user_id == current_user.id,
        )
        .first()
    )

    if reaction is None:
        raise HTTPException(status_code=404, detail="Реакция не найдена")

    if reaction.is_like:
        comment.likes_count = max(0, comment.likes_count - 1)
    else:
        comment.dislikes_count = max(0, comment.dislikes_count - 1)

    db.delete(reaction)
    db.commit()

    return MessageResponse(message="Реакция удалена")


# ВСПОМОГАТЕЛЬНЫЕ

def _get_user_reaction(
    db: Session,
    comment_id: int,
    user_id: int,
) -> CommentReactionResponse | None:
    """ Получить реакцию пользователя на комментарий """
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
    """ Преобразовать комментарий в ответ """
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
        user=UserBriefResponse(
            id=comment.user.id,
            username=comment.user.username,
            display_name=comment.user.display_name,
            avatar_url=comment.user.avatar_url,
        ),
        text=comment.text,
        rating=preference.rating if preference else None,
        likes_count=comment.likes_count,
        dislikes_count=comment.dislikes_count,
        user_reaction=_get_user_reaction(db, comment.id, current_user_id),
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )



# /comments                       GET    - список комментариев к чипсам (chip_id в query)
# /comments                       POST   - создать комментарий (chip_id в body)
# /comments/{comment_id}          PUT    - редактировать свой
# /comments/{comment_id}          DELETE - удалить свой
# /comments/{comment_id}/reaction POST   - поставить реакцию
# /comments/{comment_id}/reaction DELETE - убрать реакцию