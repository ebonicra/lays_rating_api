"""
Создать пользователя-админа.

Запуск:
    python create_admin.py <username> <display_name> <password>

Флаги:
    --super         — назначить super_admin вместо admin
    --dry-run       — только проверить, что username свободен

Примеры:
    python create_admin.py admin "Василий" SuperSecret123
    python create_admin.py admin "Василий" SuperSecret123 --super
    python create_admin.py admin "Василий" SuperSecret123 --dry-run
"""

import argparse
import sys

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import User
from app.models.user_role import UserRole


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Создать админа.")
    parser.add_argument("username", help="Username (уникальный, до 20 символов)")
    parser.add_argument("display_name", help="Отображаемое имя (до 20 символов)")
    parser.add_argument("password", help="Пароль")
    parser.add_argument(
        "--super",
        action="store_true",
        help="Назначить super_admin вместо admin",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Не писать в БД",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Простые проверки длины (как в модели)
    if not (1 <= len(args.username) <= 20):
        print("❌ Username должен быть от 1 до 20 символов.")
        sys.exit(1)
    if not (1 <= len(args.display_name) <= 20):
        print("❌ Display name должен быть от 1 до 20 символов.")
        sys.exit(1)
    if len(args.password) < 6:
        print("❌ Пароль короче 6 символов.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = (
            db.query(User)
            .filter(User.username == args.username)
            .first()
        )
        if existing is not None:
            print(
                f"❌ Пользователь '{args.username}' уже существует "
                f"(id={existing.id}, роль={existing.role})."
            )
            sys.exit(1)

        role = (
            UserRole.SUPER_ADMIN.value
            if args.super
            else UserRole.ADMIN.value
        )

        print(f"👤 Username:     {args.username}")
        print(f"📛 Display name: {args.display_name}")
        print(f"🔑 Роль:         {role}")

        if args.dry_run:
            print("🔍 DRY RUN — в БД ничего не пишем.")
            return

        user = User(
            username=args.username,
            display_name=args.display_name,
            password_hash=hash_password(args.password),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"✅ Готово. id={user.id}, роль={user.role}.")
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()