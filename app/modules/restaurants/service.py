from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache
from app.core.exceptions import NotFoundError
from app.core.geo import geo_point, geo_point_value
from app.modules.restaurants import cache as keys
from app.modules.restaurants.models import MenuItem, Restaurant
from app.modules.restaurants.schemas import (
    MenuItemCreate,
    MenuItemRead,
    MenuItemUpdate,
    RestaurantCreate,
    RestaurantListItem,
    RestaurantRead,
    RestaurantUpdate,
)


async def create_restaurant(session: AsyncSession, data: RestaurantCreate) -> Restaurant:
    restaurant = Restaurant(**data.model_dump())
    session.add(restaurant)
    await session.commit()
    # Новий ресторан може з'явитися в будь-якому результаті геопошуку.
    await cache.bump_generation(keys.NEARBY_GENERATION)
    return restaurant


async def get_restaurant(session: AsyncSession, restaurant_id: int) -> Restaurant:
    restaurant = await session.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise NotFoundError(f"Restaurant {restaurant_id} not found")
    return restaurant


async def list_restaurants(session: AsyncSession, limit: int, offset: int) -> list[Restaurant]:
    stmt = select(Restaurant).order_by(Restaurant.id).limit(limit).offset(offset)
    return list((await session.scalars(stmt)).all())


async def find_nearby(
    session: AsyncSession, lat: float, lng: float, radius_m: float, limit: int
) -> list[tuple[Restaurant, float]]:
    """Активні ресторани в радіусі radius_m, від найближчого. Використовує GiST-індекс."""
    location = geo_point(Restaurant.lat, Restaurant.lng)
    target = geo_point_value(lat, lng)
    stmt = (
        select(Restaurant, func.ST_Distance(location, target).label("distance_m"))
        .where(Restaurant.is_active.is_(True), func.ST_DWithin(location, target, radius_m))
        .order_by(location.op("<->")(target))
        .limit(limit)
    )
    rows = await session.execute(stmt)
    return [(row.Restaurant, row.distance_m) for row in rows]


async def update_restaurant(
    session: AsyncSession, restaurant_id: int, data: RestaurantUpdate
) -> Restaurant:
    restaurant = await get_restaurant(session, restaurant_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(restaurant, field, value)
    await session.commit()
    # Інвалідація ПІСЛЯ коміту: якщо скинути раніше, паралельний запит міг би
    # встигнути закешувати старі дані з БД до завершення транзакції.
    await cache.invalidate(keys.restaurant_key(restaurant_id))
    await cache.bump_generation(keys.NEARBY_GENERATION)
    return restaurant


async def add_menu_item(
    session: AsyncSession, restaurant_id: int, data: MenuItemCreate
) -> MenuItem:
    await get_restaurant(session, restaurant_id)
    item = MenuItem(restaurant_id=restaurant_id, **data.model_dump())
    session.add(item)
    await session.commit()
    await cache.invalidate(*keys.menu_keys(restaurant_id))
    return item


async def get_menu(
    session: AsyncSession, restaurant_id: int, only_available: bool
) -> list[MenuItem]:
    await get_restaurant(session, restaurant_id)
    stmt = select(MenuItem).where(MenuItem.restaurant_id == restaurant_id).order_by(MenuItem.id)
    if only_available:
        stmt = stmt.where(MenuItem.is_available.is_(True))
    return list((await session.scalars(stmt)).all())


async def update_menu_item(session: AsyncSession, item_id: int, data: MenuItemUpdate) -> MenuItem:
    item = await session.get(MenuItem, item_id)
    if item is None:
        raise NotFoundError(f"Menu item {item_id} not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await session.commit()
    await cache.invalidate(*keys.menu_keys(item.restaurant_id))
    return item


# --- Публічний інтерфейс модуля для інших модулів (orders) ---

async def get_items_for_order(
    session: AsyncSession, restaurant_id: int, item_ids: list[int]
) -> dict[int, MenuItem]:
    """Повертає страви ресторану за id одним запитом (без N+1)."""
    stmt = select(MenuItem).where(
        MenuItem.restaurant_id == restaurant_id, MenuItem.id.in_(item_ids)
    )
    return {item.id: item for item in (await session.scalars(stmt)).all()}


# --- ЛР4: кешовані версії read-intensive сценаріїв (Cache-Aside) ---
# Повертають (дані у вигляді JSON-сумісних dict, статус кешу HIT / MISS / BYPASS).

async def get_restaurant_cached(session: AsyncSession, restaurant_id: int) -> tuple[dict, str]:
    async def load() -> dict:
        r = await get_restaurant(session, restaurant_id)
        return RestaurantRead.model_validate(r).model_dump(mode="json")

    return await cache.cache_aside(keys.restaurant_key(restaurant_id), keys.TTL_RESTAURANT, load)


async def get_menu_cached(
    session: AsyncSession, restaurant_id: int, only_available: bool
) -> tuple[list[dict], str]:
    async def load() -> list[dict]:
        items = await get_menu(session, restaurant_id, only_available)
        return [MenuItemRead.model_validate(i).model_dump(mode="json") for i in items]

    return await cache.cache_aside(keys.menu_key(restaurant_id, only_available), keys.TTL_MENU, load)


async def find_nearby_cached(
    session: AsyncSession, lat: float, lng: float, radius_m: float, limit: int
) -> tuple[list[dict], str]:
    # Відстань рахується від округленої точки, тому відповідь однакова для всього «квадрата» ~110 м.
    lat, lng = keys.normalize_point(lat, lng)

    async def load() -> list[dict]:
        found = await find_nearby(session, lat, lng, radius_m, limit)
        return [
            RestaurantListItem.model_validate(r)
            .model_copy(update={"distance_m": round(d, 1)})
            .model_dump(mode="json")
            for r, d in found
        ]

    gen = await cache.generation(keys.NEARBY_GENERATION)
    if gen is None:   # Redis недоступний: напряму з БД
        return await load(), cache.BYPASS
    return await cache.cache_aside(keys.nearby_key(gen, lat, lng, radius_m, limit), keys.TTL_NEARBY, load)
