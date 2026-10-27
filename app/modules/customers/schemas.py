from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

PHONE_PATTERN = r"^\+?\d{10,15}$"


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=PHONE_PATTERN, examples=["+380501234567"])


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    created_at: datetime
