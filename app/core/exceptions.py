from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class AppError(Exception):
    """Базова бізнес-помилка. Кожен підклас задає свій HTTP-статус."""

    status_code = 400
    code = "bad_request"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    """Операція суперечить поточному стану ресурсу (напр., недопустимий перехід статусу)."""

    status_code = 409
    code = "conflict"


class BusinessRuleError(AppError):
    """Дані синтаксично коректні, але порушують бізнес-правило."""

    status_code = 422
    code = "business_rule_violation"


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message))

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        # Напр., дублікат унікального телефону.
        return JSONResponse(
            status_code=409,
            content=_error_body("integrity_error", "Resource violates a uniqueness or reference constraint"),
        )
