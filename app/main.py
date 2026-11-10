import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

import app.models  # noqa: F401  (реєстрація моделей)
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import register_exception_handlers
from app.modules.couriers.router import router as couriers_router
from app.modules.customers.router import router as customers_router
from app.modules.orders.router import router as orders_router
from app.modules.restaurants.router import menu_router, router as restaurants_router

app = FastAPI(
    title=settings.app_name,
    version="0.3.0",
    description="Globus — високонавантажений сервіс доставки їжі з відстеженням кур'єрів у реальному часі.",
)
register_exception_handlers(app)

HEALTH_PATH = "/health"
HEALTH_DB_TIMEOUT_S = 2.0


@app.middleware("http")
async def add_instance_id(request: Request, call_next):
    """Позначає, який саме вузол обробив запит. Стану між запитами не зберігає.

    ЛР3: якщо задано ARTIFICIAL_DELAY_MS, вузол навмисно відповідає повільніше
    (симуляція деградованого сервера). /health затримку не отримує: вузол живий,
    але повільний, і саме тут видно різницю між Round Robin та Least Connections.
    """
    if settings.artificial_delay_ms > 0 and request.url.path != HEALTH_PATH:
        await asyncio.sleep(settings.artificial_delay_ms / 1000)
    response = await call_next(request)
    response.headers["X-Instance-ID"] = settings.instance_id
    return response


for r in (customers_router, restaurants_router, menu_router, couriers_router, orders_router):
    app.include_router(r)


@app.get(HEALTH_PATH, tags=["system"])
async def health():
    """Readiness-перевірка для балансувальника.

    200: вузол готовий обробляти запити (БД відповідає).
    503: вузол живий, але деградований (немає зв'язку з БД), тож балансувальник
    має тимчасово виключити його з пулу.
    """
    try:
        async with SessionLocal() as session:
            await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=HEALTH_DB_TIMEOUT_S)
    except Exception as exc:  # будь-яка проблема з БД означає «не готовий»
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "instance": settings.instance_id, "database": "unavailable",
                     "detail": type(exc).__name__},
        )
    return {"status": "ok", "instance": settings.instance_id, "database": "ok"}
