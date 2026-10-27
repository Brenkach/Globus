from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.modules.couriers import service as couriers
from app.modules.customers import service as customers
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.orders.schemas import OrderCreate
from app.modules.restaurants import service as restaurants

# Статусна машина замовлення: стан -> дозволені наступні стани.
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.COOKING, OrderStatus.CANCELLED},
    OrderStatus.COOKING: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.PICKED_UP},
    OrderStatus.PICKED_UP: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}

ASSIGNABLE_STATUSES = {OrderStatus.ACCEPTED, OrderStatus.COOKING, OrderStatus.READY}
FINAL_STATUSES = {OrderStatus.DELIVERED, OrderStatus.CANCELLED}


def _order_query():
    return select(Order).options(selectinload(Order.items))


async def get_order(session: AsyncSession, order_id: int, *, for_update: bool = False) -> Order:
    stmt = _order_query().where(Order.id == order_id)
    if for_update:
        stmt = stmt.with_for_update()
    order = (await session.scalars(stmt)).first()
    if order is None:
        raise NotFoundError(f"Order {order_id} not found")
    return order


async def list_orders(
    session: AsyncSession,
    customer_id: int | None,
    status: OrderStatus | None,
    limit: int,
    offset: int,
) -> list[Order]:
    stmt = _order_query().order_by(Order.id.desc()).limit(limit).offset(offset)
    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)
    if status is not None:
        stmt = stmt.where(Order.status == status)
    return list((await session.scalars(stmt)).all())


async def create_order(session: AsyncSession, data: OrderCreate) -> Order:
    await customers.get_customer(session, data.customer_id)
    restaurant = await restaurants.get_restaurant(session, data.restaurant_id)
    if not restaurant.is_active:
        raise BusinessRuleError(f"Restaurant {restaurant.id} is not accepting orders")

    requested_ids = [i.menu_item_id for i in data.items]
    menu = await restaurants.get_items_for_order(session, restaurant.id, requested_ids)

    missing = sorted(set(requested_ids) - menu.keys())
    if missing:
        raise BusinessRuleError(f"Menu items {missing} do not belong to restaurant {restaurant.id}")
    unavailable = sorted(i for i in requested_ids if not menu[i].is_available)
    if unavailable:
        raise BusinessRuleError(f"Menu items {unavailable} are currently unavailable")

    # Ціну рахуємо на сервері з БД і ніколи не довіряємо клієнту.
    order_items = [
        OrderItem(
            menu_item_id=i.menu_item_id,
            name=menu[i.menu_item_id].name,
            unit_price=menu[i.menu_item_id].price,
            quantity=i.quantity,
        )
        for i in data.items
    ]
    total = sum((oi.unit_price * oi.quantity for oi in order_items), Decimal("0"))

    order = Order(
        customer_id=data.customer_id,
        restaurant_id=restaurant.id,
        delivery_address=data.delivery_address,
        delivery_lat=data.delivery_lat,
        delivery_lng=data.delivery_lng,
        total_amount=total,
        items=order_items,
    )
    session.add(order)
    await session.commit()
    return await get_order(session, order.id)


async def change_status(session: AsyncSession, order_id: int, new_status: OrderStatus) -> Order:
    order = await get_order(session, order_id, for_update=True)

    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise ConflictError(f"Cannot change order status from {order.status.value} to {new_status.value}")
    if new_status == OrderStatus.PICKED_UP and order.courier_id is None:
        raise ConflictError("Order cannot be picked up: no courier assigned")

    if new_status in FINAL_STATUSES and order.courier_id is not None:
        await couriers.release(session, order.courier_id)

    order.status = new_status
    await session.commit()
    return order


async def assign_courier(session: AsyncSession, order_id: int) -> Order:
    # Блокуємо замовлення, щоб два паралельні запити не призначили двох кур'єрів.
    order = await get_order(session, order_id, for_update=True)

    if order.courier_id is not None:
        raise ConflictError(f"Order {order_id} already has courier {order.courier_id}")
    if order.status not in ASSIGNABLE_STATUSES:
        raise ConflictError(f"Courier cannot be assigned to order in status {order.status.value}")

    restaurant = await restaurants.get_restaurant(session, order.restaurant_id)
    courier = await couriers.reserve_nearest_available(
        session, restaurant.lat, restaurant.lng, settings.courier_search_radius_m
    )
    if courier is None:
        raise ConflictError("No available couriers near the restaurant, try again later")

    order.courier_id = courier.id
    await session.commit()
    return order
