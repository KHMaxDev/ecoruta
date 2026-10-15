"""Configuración central de la aplicación EcoRuta (Pydantic Settings v2)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "EcoRuta API"
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+asyncpg://ecoruta_user:ecoruta_secure_password@localhost:5432/ecoruta_db"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    cache_ttl_seconds: int = Field(default=900)

    valhalla_url: str = Field(default="http://localhost:8002")
    inegi_sakbe_token: str = Field(default="")
    cne_endpoint_url: str = Field(
        default="https://datos.gob.mx/apis-cne/precios-gasolinas-diesel.json"
    )

    air_density_default: float = Field(default=1.05)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
