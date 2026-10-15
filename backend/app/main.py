"""Punto de entrada de la API EcoRuta (FastAPI + ASGI)."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_router
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ecoruta.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Iniciando %s", settings.app_name)
    yield
    from app.api.routes import get_redis

    try:
        await get_redis().aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo cerrar la conexión Redis: %s", exc)
    logger.info("Deteniendo %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Motor de optimización multiobjetivo (costo vs. tiempo) de rutas viales en México "
        "con modelo físico de consumo, regularización FIFO y auditoría de datos."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
