from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine

from app.models import (
    chip_comment,
    chip_preference,
    chip,
    comment_reaction,
    news_type,
    news,
    photo_reaction,
    poll_vote,
    user_filter,
    user_follow,
    user_photo,
    user_role,
    user,
)

from app.routers import (
    auth,                # ← новый: /auth/register, /auth/login
    admin,               # ← /admin
    chip,                # ← /chips, /chips/{id}, /chips/images
    comment,             # ← /comments
    news,                # ← /news
    photo,               # ← /photos
    preference,          # ← /preferences/{chip_id}
    search,              # ← /search/users, /search/all
    stats,               # ← /stats/{id}, /stats/{id}/favorites
    user_filter,         # ← /filters
    user_follow,         # ← /follows/{id}, /follows/{id}/followers
    user,                # ← /users/me, /users/{id}, /users/avatars
)


def include_routers(app: FastAPI) -> None:
    app.include_router(auth.router)          # /auth/*
    app.include_router(search.router)        # /search/*
    app.include_router(user.router)          # /users/*
    app.include_router(user_follow.router)   # /follows/*
    app.include_router(user_filter.router)   # /filters
    app.include_router(stats.router)         # /stats/*
    app.include_router(chip.router)          # /chips/*
    app.include_router(preference.router)    # /preferences/*
    app.include_router(comment.router)       # /comments/*
    app.include_router(photo.router)         # /photos/*
    app.include_router(news.router)          # /news/*
    app.include_router(admin.router)         # /admin/*



@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Lays Rating API",
    description="Backend для приложения рейтинга чипсов",
    version="1.0.0",
    lifespan=lifespan,
)
include_routers(app)


@app.get("/")
def root():
    return {"message": "Lays Rating backend is alive!"}