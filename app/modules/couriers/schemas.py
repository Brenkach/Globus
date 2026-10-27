from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.couriers.models import CourierStatus
from app.modules.customers.schemas import PHONE_PATTERN


class CourierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=PHONE_PATTERN, examples=["+380671234567"])


class CourierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    status: CourierStatus
    lat: float | None
    lng: float | None
    location_updated_at: datetime | None


class LocationUpdate(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class CourierStatusUpdate(BaseModel):
    # BUSY виставляє лише система при призначенні на замовлення.
    status: Literal[CourierStatus.AVAILABLE, CourierStatus.OFFLINE]
