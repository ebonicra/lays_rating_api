# make_admin.py или новый migrate.py
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

with db.bind.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN avatar_path VARCHAR(255)"))
        conn.commit()
        print("✅ Колонка avatar_path добавлена")
    except Exception as e:
        print(f"ℹ️ {e}")

db.close()