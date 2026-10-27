from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Налаштування застосунку. Значення беруться зі змінних оточення або .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Globus"
    database_url: str = "postgresql+asyncpg://globus:globus@localhost:5432/globus"
    db_pool_size: int = 10
    db_max_overflow: int = 5
    courier_search_radius_m: float = 5000.0


settings = Settings()
