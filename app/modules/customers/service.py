from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.customers.models import Customer
from app.modules.customers.schemas import CustomerCreate


async def create_customer(session: AsyncSession, data: CustomerCreate) -> Customer:
    customer = Customer(**data.model_dump())
    session.add(customer)
    await session.commit()
    return customer


async def get_customer(session: AsyncSession, customer_id: int) -> Customer:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    return customer
