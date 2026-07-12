from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/teamate"
    ML_MODEL_URL: str = "http://localhost:8000"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    DEBUG: bool = True
    DEFAULT_WEATHER_LAT: float = 6.9271
    DEFAULT_WEATHER_LON: float = 80.6005
    SMS_PROVIDER: str = "mock"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> Any:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"dev", "development"}:
                return True
        return value

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
