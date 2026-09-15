from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


# check_same_thread нужен только для SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False


engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


def get_db():
    """FastAPI-зависимость: создаёт сессию и закрывает после запроса"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()