from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.modules.couriers import service
from app.modules.couriers.schemas import (
    CourierCreate,
    CourierRead,
    CourierStatusUpdate,
    LocationUpdate,
)

router = APIRouter(prefix="/couriers", tags=["couriers"])


@router.post("", response_model=CourierRead, status_code=status.HTTP_201_CREATED)
async def create_courier(data: CourierCreate, session: SessionDep):
    return await service.create_courier(session, data)


@router.get("/{courier_id}", response_model=CourierRead)
async def get_courier(courier_id: int, session: SessionDep):
    return await service.get_courier(session, courier_id)


@router.put("/{courier_id}/location", response_model=CourierRead)
async def update_location(courier_id: int, data: LocationUpdate, session: SessionDep):
    """Кур'єрський застосунок надсилає координати кожні кілька секунд."""
    return await service.update_location(session, courier_id, data)


@router.patch("/{courier_id}/status", response_model=CourierRead)
async def set_status(courier_id: int, data: CourierStatusUpdate, session: SessionDep):
    """Вийти на лінію (AVAILABLE) або завершити зміну (OFFLINE)."""
    return await service.set_status(session, courier_id, data.status)
