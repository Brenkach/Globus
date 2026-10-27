from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.modules.customers import service
from app.modules.customers.schemas import CustomerCreate, CustomerRead

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(data: CustomerCreate, session: SessionDep):
    return await service.create_customer(session, data)


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(customer_id: int, session: SessionDep):
    return await service.get_customer(session, customer_id)
