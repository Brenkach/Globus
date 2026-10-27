from fastapi import APIRouter, Query, status

from app.core.database import SessionDep
from app.modules.orders import service
from app.modules.orders.models import OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderRead, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(data: OrderCreate, session: SessionDep):
    """Створення замовлення: перевірка клієнта, ресторану, страв і розрахунок суми на сервері."""
    return await service.create_order(session, data)


@router.get("", response_model=list[OrderRead])
async def list_orders(
    session: SessionDep,
    customer_id: int | None = Query(default=None, gt=0),
    status: OrderStatus | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return await service.list_orders(session, customer_id, status, limit, offset)


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, session: SessionDep):
    return await service.get_order(session, order_id)


@router.patch("/{order_id}/status", response_model=OrderRead)
async def change_status(order_id: int, data: OrderStatusUpdate, session: SessionDep):
    """Перехід статусу за статусною машиною. Недопустимий перехід повертає 409."""
    return await service.change_status(session, order_id, data.status)


@router.post("/{order_id}/assign-courier", response_model=OrderRead)
async def assign_courier(order_id: int, session: SessionDep):
    """Призначає найближчого вільного кур'єра до ресторану."""
    return await service.assign_courier(session, order_id)
