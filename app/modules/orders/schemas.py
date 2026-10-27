from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.orders.models import OrderStatus


class OrderItemIn(BaseModel):
    menu_item_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    customer_id: int = Field(gt=0)
    restaurant_id: int = Field(gt=0)
    delivery_address: str = Field(min_length=1, max_length=255)
    delivery_lat: float = Field(ge=-90, le=90)
    delivery_lng: float = Field(ge=-180, le=180)
    items: list[OrderItemIn] = Field(min_length=1, max_length=50)

    @field_validator("items")
    @classmethod
    def unique_menu_items(cls, items: list[OrderItemIn]) -> list[OrderItemIn]:
        ids = [i.menu_item_id for i in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate menu_item_id; use quantity instead")
        return items


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    menu_item_id: int
    name: str
    unit_price: Decimal
    quantity: int


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    restaurant_id: int
    courier_id: int | None
    status: OrderStatus
    delivery_address: str
    delivery_lat: float
    delivery_lng: float
    total_amount: Decimal
    items: list[OrderItemRead]
    created_at: datetime
    updated_at: datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
