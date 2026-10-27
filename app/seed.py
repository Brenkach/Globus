"""Демо-дані для захисту. Запуск: docker compose exec app python -m app.seed"""

import asyncio
from decimal import Decimal

from sqlalchemy import func, select

import app.models  # noqa: F401
from app.core.database import SessionLocal
from app.modules.couriers.models import Courier, CourierStatus
from app.modules.customers.models import Customer
from app.modules.restaurants.models import MenuItem, Restaurant

RESTAURANTS = [
    ("Pizza Napoli", "вул. Хрещатик, 10", 50.4470, 30.5220,
     [("Маргарита", "189.00"), ("Пепероні", "229.00"), ("Чотири сири", "249.00")]),
    ("Sushi Time", "вул. Велика Васильківська, 45", 50.4330, 30.5180,
     [("Філадельфія", "319.00"), ("Каліфорнія", "279.00"), ("Місо-суп", "99.00")]),
    ("Burger Lab", "вул. Саксаганського, 12", 50.4390, 30.5100,
     [("Чізбургер", "175.00"), ("Картопля фрі", "75.00"), ("Лимонад", "60.00")]),
]

COURIERS = [
    ("Олег", "+380670000001", 50.4450, 30.5200),
    ("Ірина", "+380670000002", 50.4400, 30.5150),
    ("Максим", "+380670000003", 50.4350, 30.5250),
    ("Анна", "+380670000004", 50.4500, 30.5300),
    ("Дмитро", "+380670000005", 50.4280, 30.5050),
]


async def seed() -> None:
    async with SessionLocal() as session:
        if await session.scalar(select(func.count()).select_from(Restaurant)):
            print("Database already seeded, skipping")
            return

        for name, address, lat, lng, menu in RESTAURANTS:
            restaurant = Restaurant(name=name, address=address, lat=lat, lng=lng)
            session.add(restaurant)
            await session.flush()
            session.add_all(
                MenuItem(restaurant_id=restaurant.id, name=n, price=Decimal(p)) for n, p in menu
            )

        session.add_all(
            Courier(name=n, phone=p, lat=lat, lng=lng, status=CourierStatus.AVAILABLE)
            for n, p, lat, lng in COURIERS
        )
        session.add_all([
            Customer(name="Тестовий клієнт 1", phone="+380501111111"),
            Customer(name="Тестовий клієнт 2", phone="+380502222222"),
        ])
        await session.commit()
        print("Seed data created")


if __name__ == "__main__":
    asyncio.run(seed())
