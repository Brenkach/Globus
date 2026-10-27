from fastapi import FastAPI
from sqlalchemy import text

import app.models  # noqa: F401  (реєстрація моделей)
from app.core.config import settings
from app.core.database import SessionDep
from app.core.exceptions import register_exception_handlers
from app.modules.couriers.router import router as couriers_router
from app.modules.customers.router import router as customers_router
from app.modules.orders.router import router as orders_router
from app.modules.restaurants.router import menu_router, router as restaurants_router

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Globus — високонавантажений сервіс доставки їжі з відстеженням кур'єрів у реальному часі.",
)
register_exception_handlers(app)

for r in (customers_router, restaurants_router, menu_router, couriers_router, orders_router):
    app.include_router(r)


@app.get("/health", tags=["system"])
async def health(session: SessionDep):
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
