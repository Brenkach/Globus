import socket

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Налаштування застосунку. Значення беруться зі змінних оточення або .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Globus"
    # Ідентифікатор вузла для заголовка X-Instance-ID. Якщо не задано, береться hostname контейнера.
    instance_id: str = Field(default_factory=socket.gethostname)
    database_url: str = "postgresql+asyncpg://globus:globus@localhost:5432/globus"
    db_pool_size: int = 10
    db_max_overflow: int = 5
    courier_search_radius_m: float = 5000.0

    # ЛР3: штучна затримка відповіді (мс) для симуляції деградованого вузла.
    # Задається лише на одному екземплярі під час експерименту; за замовчуванням 0 (вимкнено).
    artificial_delay_ms: int = 0

    # ЛР4: розподілений кеш (Redis), спільний для всіх екземплярів.
    redis_url: str = "redis://localhost:6379/0"
    cache_enabled: bool = True
    # Таймаут операцій з Redis: кеш має бути швидким, інакше він лише заважає.
    cache_timeout_s: float = 0.3
    # Після помилки Redis цей екземпляр не звертається до кешу N секунд (circuit breaker).
    cache_retry_after_s: float = 5.0


settings = Settings()
