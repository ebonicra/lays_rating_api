"""
Загрузка чипсов из seed/chips.json в БД.

Идемпотентно: чипсы с существующим name не перезаписываются и не дублируются.

Запуск (из корня backend, где лежит app/):
    python seed_chips.py

Флаги:
    --dry-run       — только показать, что будет сделано, без записи в БД
    --with-news     — создать новость NEW_CHIP для каждого нового чипса
    --update        — обновлять существующие чипсы данными из JSON
"""

import app.models
import argparse
import json
import sys
from pathlib import Path

from app.database import SessionLocal
from app.models.chip import Chip
from app.models.news import News
from app.models.news_type import NewsType


SEED_FILE = Path(__file__).parent / "seed" / "chips.json"


def load_seed(path: Path) -> list[dict]:
    if not path.exists():
        print(f"❌ Файл не найден: {path}")
        sys.exit(1)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка в JSON: {e}")
        sys.exit(1)

    if not isinstance(data, list):
        print("❌ JSON должен быть массивом объектов.")
        sys.exit(1)

    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed чипсов из JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Не писать в БД.")
    parser.add_argument("--with-news", action="store_true", help="Создавать новость NEW_CHIP.")
    parser.add_argument("--update", action="store_true", help="Обновлять существующие.")
    return parser.parse_args()


def create_chip_from_data(db, data: dict, with_news: bool) -> Chip:
    chip = Chip(
        name=data["name"],
        category=data["category"],
        description=data["description"],
        image_path=data.get("image_path"),
        collection=data.get("collection"),
        country=data.get("country"),
        release_year=data.get("release_year"),
        available=data.get("available", True),
    )
    db.add(chip)
    db.flush()  # чтобы получить chip.id

    if with_news:
        news = News(
            event_type=NewsType.NEW_CHIP.value,
            chip_id=chip.id,
            text=f"Новый вкус: {chip.name}!",
        )
        db.add(news)

    return chip


def update_chip_from_data(chip: Chip, data: dict) -> None:
    chip.category = data["category"]
    chip.description = data["description"]
    chip.image_path = data.get("image_path", chip.image_path)
    chip.collection = data.get("collection", chip.collection)
    chip.country = data.get("country", chip.country)
    chip.release_year = data.get("release_year", chip.release_year)
    chip.available = data.get("available", chip.available)


def main() -> None:
    args = parse_args()
    seed = load_seed(SEED_FILE)

    print(f"📂 Файл: {SEED_FILE}")
    print(f"📦 В JSON: {len(seed)} чипс(ов)")
    if args.dry_run:
        print("🔍 DRY RUN — в БД ничего не пишем")
    print()

    db = SessionLocal()
    created = 0
    updated = 0
    skipped = 0

    try:
        for data in seed:
            name = data.get("name", "").strip()
            if not name:
                print(f"⚠️  Пропущен: пустое имя — {data}")
                skipped += 1
                continue

            existing = db.query(Chip).filter(Chip.name == name).first()

            if existing is None:
                if args.dry_run:
                    print(f"➕ [DRY] Создать: {name}")
                else:
                    create_chip_from_data(db, data, args.with_news)
                    print(f"➕ Создан: {name}")
                created += 1
            elif args.update:
                if args.dry_run:
                    print(f"✏️  [DRY] Обновить: {name}")
                else:
                    update_chip_from_data(existing, data)
                    print(f"✏️  Обновлён: {name}")
                updated += 1
            else:
                print(f"⏭️  Пропущен (уже есть): {name}")
                skipped += 1

        if args.dry_run:
            print()
            print("🔍 DRY RUN завершён. В БД ничего не записано.")
        else:
            db.commit()
            print()
            print(f"✅ Готово. Создано: {created}, обновлено: {updated}, пропущено: {skipped}")

    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()