from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.geo import geo_point, geo_point_value
from app.modules.restaurants.models import MenuItem, Restaurant
from app.modules.restaurants.schemas import (
    MenuItemCreate,
    MenuItemUpdate,
    RestaurantCreate,
    RestaurantUpdate,
)


async def create_restaurant(session: AsyncSession, data: RestaurantCreate) -> Restaurant:
    restaurant = Restaurant(**data.model_dump())
    session.add(restaurant)
    await session.commit()
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
    return restaurant


async def add_menu_item(
    session: AsyncSession, restaurant_id: int, data: MenuItemCreate
) -> MenuItem:
    await get_restaurant(session, restaurant_id)
    item = MenuItem(restaurant_id=restaurant_id, **data.model_dump())
    session.add(item)
    await session.commit()
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
