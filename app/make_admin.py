"""
Скрипт для назначения роли пользователю.

Запуск:
    python -m app.make_admin
"""

from app.database import SessionLocal

# ⚠️ Импортируем ВСЕ модели, чтобы SQLAlchemy знал о связях
from app.models import (
    user,
    user_role,
    user_filter,
    user_follow,
    user_photo,
    photo_reaction,
    chip,
    chip_preference,
    chip_comment,
    comment_reaction,
    news,
    news_type,
    poll_vote,
)

from app.models.user import User
from app.models.user_role import UserRole


def print_user_info(user: User) -> None:
    """Показать текущую инфу о пользователе"""
    print(f"  ID:          {user.id}")
    print(f"  Username:    {user.username}")
    print(f"  Display:     {user.display_name}")
    print(f"  Role:        {user.role}")


def main() -> None:
    db = SessionLocal()

    try:
        username = input("Введите username: ").strip()

        if not username:
            print("❌ Username не может быть пустым")
            return

        user = db.query(User).filter(User.username == username).first()

        if user is None:
            print(f"❌ Пользователь '{username}' не найден")
            return

        print(f"\n✅ Найден пользователь:")
        print_user_info(user)

        print("\nВыберите новую роль:")
        print("  1 — user (обычный пользователь)")
        print("  2 — admin (админ)")
        print("  3 — super_admin (супер-админ)")
        print("  0 — отмена")

        choice = input("\nВведите номер: ").strip()

        role_map = {
            "1": UserRole.USER.value,
            "2": UserRole.ADMIN.value,
            "3": UserRole.SUPER_ADMIN.value,
        }

        if choice == "0":
            print("Отменено")
            return

        new_role = role_map.get(choice)

        if new_role is None:
            print("❌ Неверный выбор")
            return

        if user.role == new_role:
            print(f"ℹ️ Пользователь уже имеет роль '{new_role}'")
            return

        old_role = user.role
        user.role = new_role
        db.commit()

        print(f"\n✅ Роль изменена: {old_role} → {new_role}")

    finally:
        db.close()


if __name__ == "__main__":
    main()