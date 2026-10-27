from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.geo import geo_point, geo_point_value
from app.modules.couriers.models import Courier, CourierStatus
from app.modules.couriers.schemas import CourierCreate, LocationUpdate

# Скільки найближчих кандидатів розглядати при призначенні кур'єра.
COURIER_CANDIDATES_LIMIT = 20


async def create_courier(session: AsyncSession, data: CourierCreate) -> Courier:
    courier = Courier(**data.model_dump())
    session.add(courier)
    await session.commit()
    return courier


async def get_courier(session: AsyncSession, courier_id: int) -> Courier:
    courier = await session.get(Courier, courier_id)
    if courier is None:
        raise NotFoundError(f"Courier {courier_id} not found")
    return courier


async def update_location(
    session: AsyncSession, courier_id: int, data: LocationUpdate
) -> Courier:
    """Найчастіша операція в системі: один UPDATE ... RETURNING без попереднього SELECT."""
    stmt = (
        update(Courier)
        .where(Courier.id == courier_id)
        .values(lat=data.lat, lng=data.lng, location_updated_at=func.now())
        .returning(Courier)
    )
    courier = (await session.execute(stmt)).scalar_one_or_none()
    if courier is None:
        raise NotFoundError(f"Courier {courier_id} not found")
    await session.commit()
    return courier


async def set_status(
    session: AsyncSession, courier_id: int, new_status: CourierStatus
) -> Courier:
    courier = await get_courier(session, courier_id)
    if courier.status == CourierStatus.BUSY:
        raise ConflictError("Courier is delivering an order; status is managed by the system")
    courier.status = new_status
    await session.commit()
    return courier


# --- Публічний інтерфейс модуля для інших модулів (orders) ---
# Ці функції НЕ комітять: транзакцією керує модуль-викликач.

async def reserve_nearest_available(
    session: AsyncSession, lat: float, lng: float, radius_m: float
) -> Courier | None:
    """Знаходить найближчого вільного кур'єра і блокує його рядок.

    FOR UPDATE SKIP LOCKED: якщо два замовлення одночасно шукають кур'єра,
    друге пропускає вже заблокований рядок і бере наступного, тож один
    кур'єр ніколи не потрапить на два замовлення, а запити не чекають один одного.

    Запит у два кроки, бо PostgreSQL не дозволяє поєднати FOR UPDATE з KNN-сортуванням
    по GiST-індексу ("attempted to lock invisible tuple"):
      1) підзапит без блокування: N найближчих кандидатів через GiST-індекс;
      2) зовнішній запит: блокує першого незаблокованого кандидата за первинним ключем.
    """
    location = geo_point(Courier.lat, Courier.lng)
    target = geo_point_value(lat, lng)
    candidates = (
        select(Courier.id, location.op("<->")(target).label("distance"))
        .where(
            Courier.status == CourierStatus.AVAILABLE,
            Courier.lat.is_not(None),
            func.ST_DWithin(location, target, radius_m),
        )
        .order_by("distance")
        .limit(COURIER_CANDIDATES_LIMIT)
        .subquery()
    )
    stmt = (
        select(Courier)
        .join(candidates, Courier.id == candidates.c.id)
        .where(Courier.status == CourierStatus.AVAILABLE)
        .order_by(candidates.c.distance)
        .limit(1)
        .with_for_update(of=Courier, skip_locked=True)
    )
    courier = (await session.scalars(stmt)).first()
    if courier is not None:
        courier.status = CourierStatus.BUSY
    return courier


async def release(session: AsyncSession, courier_id: int) -> None:
    await session.execute(
        update(Courier)
        .where(Courier.id == courier_id, Courier.status == CourierStatus.BUSY)
        .values(status=CourierStatus.AVAILABLE)
    )
