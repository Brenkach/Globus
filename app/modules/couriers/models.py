import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class CourierStatus(str, enum.Enum):
    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"


class Courier(TimestampMixin, Base):
    __tablename__ = "couriers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    status: Mapped[CourierStatus] = mapped_column(
        Enum(CourierStatus, name="courier_status"),
        default=CourierStatus.OFFLINE,
        server_default=CourierStatus.OFFLINE.value,
        index=True,
    )
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
