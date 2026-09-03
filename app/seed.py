from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.chip import Chip
from app.models.user import User
from app.models.rating import Rating


def seed_database():
    db: Session = SessionLocal()

    if db.query(Chip).count() > 0:
        print("Database already seeded")
        db.close()
        return

    chips = [
        Chip(
            id=1001,
            name="Lay's Соус 1000 островов",
            category="stix",
            description="Фигня.",
            image_path="1000_islands.png",
            available=True,
        ),

        Chip(
            id=1002,
            name="Lay's Сырный соус",
            category="stix",
            description="Фигня.",
            image_path="cheese_soys.png",
            available=True,
        ),

        Chip(
            id=2001,
            name="Lay's Краб",
            category="classic",
            description="Вкус краба",
            image_path="crab.png",
            available=True,
        ),

        Chip(
            id=2002,
            name="Lay's Бекон",
            category="classic",
            description="Вкус бекона",
            image_path="bacon.png",
            available=True,
        ),

    ]

    db.add_all(chips)

    # user = User(
    #     username="test_user"
    # )
    # db.add(user)

    db.commit()
    print("Database seeded!")
    db.close()



if __name__ == "__main__":
    seed_database()