from fastapi import FastAPI
from app.database import engine, Base
from app.models import chip, chip_comment, user, chip_preference, user_category, comment_reaction, follow
from app.routers import chip, chip_comment, user, admin, chip_preferences, user_category, follow


app = FastAPI()


@app.on_event("startup")
def startup():
    Base.metadata.create_all( #Создать таблицы, если их нет
        bind=engine
    )

app.include_router(chip.router)
app.include_router(user.router)
app.include_router(admin.router)
app.include_router(user_category.router)
app.include_router(chip_preferences.router)
app.include_router(chip_comment.router)
app.include_router(follow.router)



@app.get("/")
def root():
    return {
        "message": "Lays Rating backend is alive!"
    }

