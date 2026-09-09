# migrate.py
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

with db.bind.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE user_category ADD COLUMN russia_only BOOLEAN DEFAULT 0"))
        conn.commit()
        print("✅ Колонка russia_only добавлена")
    except Exception as e:
        print(f"ℹ️ russia_only: {e}")

    try:
        conn.execute(text("ALTER TABLE user_category ADD COLUMN available_only BOOLEAN DEFAULT 0"))
        conn.commit()
        print("✅ Колонка available_only добавлена")
    except Exception as e:
        print(f"ℹ️ available_only: {e}")

db.close()