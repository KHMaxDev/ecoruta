"""Conector meteorológico e hidrológico (CONAGUA / Open-Meteo / SMN).

1. Consulta precipitación horaria, temperatura y viento en Open-Meteo / SMN.
2. Evalúa alertas de precipitación severa sobre polígonos del Atlas Nacional de
   Riesgo por Inundación (CONAGUA / CENAPRED).
3. Distingue estrictamente entre ``precaucion`` (informativo) y ``cierre_duro``
   (confirmado), aplicando solo los cierres duros como filtros de factibilidad.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("ecoruta.connectors.conagua_weather")


class WeatherAndFloodHazardConnector:
    """Consulta clima horario y aplica cierres viales confirmados por inundación."""

    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def fetch_corridor_weather(self, lat: float, lon: float) -> dict[str, Any]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,precipitation,rain,wind_speed_10m",
            "timezone": "America/Mexico_City",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(self.OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        curr = data.get("current", {})
        return {
            "temperature_c": float(curr.get("temperature_2m", 22.0)),
            "precipitation_mmh": float(curr.get("precipitation", 0.0)),
            "wind_speed_kmh": float(curr.get("wind_speed_10m", 10.0)),
            "observed_at": curr.get("time", datetime.now(timezone.utc).isoformat()),
            "source": "Open-Meteo / SMN CONAGUA",
        }

    async def apply_confirmed_flood_closures(self, db: AsyncSession) -> int:
        """Marca ``is_closed_confirmed = TRUE`` solo en aristas con ``cierre_duro``.

        Las zonas con ``severity_level`` igual a ``informativo`` o ``precaucion``
        NO bloquean aristas; solo se reportan en la auditoría de la ruta.
        """
        res = await db.execute(
            text(
                """
                UPDATE road_edges e
                SET
                    is_closed_confirmed = TRUE,
                    closure_reason = hz.description
                FROM hazard_zones hz
                WHERE hz.severity_level = 'cierre_duro'
                  AND ST_Intersects(e.geom, hz.geom);
                """
            )
        )
        await db.commit()
        return res.rowcount or 0
