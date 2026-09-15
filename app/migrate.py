# migrate.py
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

with db.bind.connect() as conn:
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS poll_votes (
                id INTEGER PRIMARY KEY,
                news_id INTEGER NOT NULL REFERENCES news(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                option_index INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                UNIQUE(news_id, user_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_poll_votes_news_id ON poll_votes(news_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_poll_votes_user_id ON poll_votes(user_id)"))
        conn.commit()
        print("✅ Таблица poll_votes создана")
    except Exception as e:
        print(f"ℹ️ {e}")

db.close()