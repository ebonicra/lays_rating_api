import os
from pathlib import Path


# Корень проекта (папка backend)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """Настройки приложения"""
    
    # База данных: URL из переменной окружения или SQLite локально
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'lays_rating.db'}",
    )
    
    # Пути к папкам с файлами
    UPLOADS_DIR      = BASE_DIR / "uploads"
    AVATARS_DIR      = UPLOADS_DIR / "avatars"        # аватарки пользователей
    CHIP_IMAGES_DIR  = UPLOADS_DIR / "chip_images"    # картинки чипсов
    NEWS_IMAGES_DIR  = UPLOADS_DIR / "news_images"    # картинки новостей
    USER_PHOTOS_DIR  = UPLOADS_DIR / "user_photos"    # фото пользователей
    
    # Лимиты
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5 МБ
    MAX_PHOTOS_PER_USER: int = 20
    MAX_AVATAR_SIZE: int = 5 * 1024 * 1024
    
    # Разрешённые форматы
    ALLOWED_IMAGE_EXTENSIONS: list[str] = ["jpg", "jpeg", "png", "webp"]
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # неделя

    DEFAULT_CATEGORIES: list[str] = ["classic", "stix", "maxx", "stax", "baked", "ridged"]


# Экземпляр настроек — создаётся ОДИН раз при импорте модуля
settings = Settings()


# Создаём папки, если их нет
for directory in [
    settings.AVATARS_DIR,
    settings.CHIP_IMAGES_DIR,
    settings.NEWS_IMAGES_DIR,
    settings.USER_PHOTOS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)