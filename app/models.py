"""Реєструє всі ORM-моделі в Base.metadata (для Alembic і маперів)."""

from app.modules.couriers.models import Courier, CourierStatus  # noqa: F401
from app.modules.customers.models import Customer  # noqa: F401
from app.modules.orders.models import Order, OrderItem, OrderStatus  # noqa: F401
from app.modules.restaurants.models import MenuItem, Restaurant  # noqa: F401
