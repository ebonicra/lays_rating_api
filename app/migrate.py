# migrate.py
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

with db.bind.connect() as conn:
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_photos (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                image_path VARCHAR NOT NULL,
                likes_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_photos_user_id ON user_photos(user_id)"))
        conn.commit()
        print("✅ Таблица user_photos создана")
    except Exception as e:
        print(f"ℹ️ user_photos: {e}")

    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS photo_reactions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                photo_id INTEGER NOT NULL REFERENCES user_photos(id) ON DELETE CASCADE,
                created_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, photo_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_photo_reactions_user_id ON photo_reactions(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_photo_reactions_photo_id ON photo_reactions(photo_id)"))
        conn.commit()
        print("✅ Таблица photo_reactions создана")
    except Exception as e:
        print(f"ℹ️ photo_reactions: {e}")

db.close()