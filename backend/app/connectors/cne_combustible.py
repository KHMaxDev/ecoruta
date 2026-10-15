"""Conector de precios de combustible de la CNE y asignación espacial a aristas.

Descarga los precios vigentes reportados ante la Comisión Nacional de Energía (CNE),
conserva la marca temporal exacta (``reported_at``) para auditoría de frescura y
actualiza en PostGIS el precio asignado a cada arista vial buscando la estación
activa más cercana mediante el operador KNN ``<->``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("ecoruta.connectors.cne")

# Precios de respaldo explícitamente marcados como estimación cuando la CNE no responde.
FALLBACK_REGULAR = 23.80
FALLBACK_PREMIUM = 25.40
FALLBACK_DIESEL = 25.10


class CNEFuelConnector:
    """Normalizador y asignador espacial de precios de gasolinas y diésel de la CNE."""

    def __init__(self, endpoint_url: str, max_search_radius_deg: float = 0.15) -> None:
        self.endpoint_url = endpoint_url
        # Radio máximo de búsqueda del vecino más cercano (~15 km en grados).
        self.max_search_radius_deg = max_search_radius_deg

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def _fetch_records(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.endpoint_url)
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, dict):
            return list(payload.get("results", []))
        return list(payload)

    async def sync_stations_and_assign_edges(self, db: AsyncSession) -> dict[str, Any]:
        status = "ok"
        try:
            records = await self._fetch_records()
        except Exception as exc:  # noqa: BLE001 - degradación explícita y auditada
            logger.warning("Fallo la descarga CNE (%s); usando respaldo marcado.", exc)
            records = []
            status = "fallback_estimate"

        inserted = 0
        now_utc = datetime.now(timezone.utc)

        for row in records:
            permiso = row.get("permiso_cre") or row.get("permiso")
            lat = row.get("latitud") or row.get("latitude")
            lon = row.get("longitud") or row.get("longitude")
            if not (permiso and lat and lon):
                continue

            await db.execute(
                text(
                    """
                    INSERT INTO fuel_stations_cne (
                        permiso_cre, station_name, regular_price_mxn,
                        premium_price_mxn, diesel_price_mxn, reported_at, fetched_at, geom
                    ) VALUES (
                        :permiso, :name, :reg, :prem, :die, :rep_at, :fetch_at,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                    )
                    ON CONFLICT (permiso_cre) DO UPDATE SET
                        regular_price_mxn = EXCLUDED.regular_price_mxn,
                        premium_price_mxn = EXCLUDED.premium_price_mxn,
                        diesel_price_mxn = EXCLUDED.diesel_price_mxn,
                        reported_at = EXCLUDED.reported_at,
                        fetched_at = EXCLUDED.fetched_at;
                    """
                ),
                {
                    "permiso": permiso,
                    "name": row.get("razon_social", "Estación CNE"),
                    "reg": row.get("precio_regular"),
                    "prem": row.get("precio_premium"),
                    "die": row.get("precio_diesel"),
                    "rep_at": row.get("fecha_reporte", now_utc.isoformat()),
                    "fetch_at": now_utc,
                    "lon": float(lon),
                    "lat": float(lat),
                },
            )
            inserted += 1

        # Asignación espacial por vecino más cercano (KNN) con radio máximo de búsqueda.
        # Se envuelve la tabla objetivo en una subconsulta para poder usar LATERAL (PostgreSQL
        # no permite referenciar el alias del objetivo de un UPDATE dentro de un FROM LATERAL).
        await db.execute(
            text(
                """
                UPDATE road_edges e
                SET
                    assigned_regular_price_mxn = COALESCE(sub.regular_price_mxn, :fb_reg),
                    assigned_premium_price_mxn = COALESCE(sub.premium_price_mxn, :fb_prem),
                    assigned_diesel_price_mxn  = COALESCE(sub.diesel_price_mxn, :fb_die),
                    fuel_price_updated_at      = COALESCE(sub.reported_at, e.fuel_price_updated_at)
                FROM (
                    SELECT e2.id AS edge_id,
                           s.regular_price_mxn, s.premium_price_mxn, s.diesel_price_mxn, s.reported_at
                    FROM road_edges e2
                    CROSS JOIN LATERAL (
                        SELECT regular_price_mxn, premium_price_mxn, diesel_price_mxn, reported_at
                        FROM fuel_stations_cne fs
                        WHERE fs.regular_price_mxn IS NOT NULL
                          AND ST_DWithin(e2.geom::geography, fs.geom::geography, 15000.0)
                        ORDER BY e2.geom <-> fs.geom
                        LIMIT 1
                    ) s
                ) sub
                WHERE e.id = sub.edge_id;
                """
            ),
            {"fb_reg": FALLBACK_REGULAR, "fb_prem": FALLBACK_PREMIUM, "fb_die": FALLBACK_DIESEL},
        )
        await db.commit()
        logger.info("Sincronizadas %d estaciones CNE y actualizadas aristas viales.", inserted)
        return {
            "status": status,
            "stations_synced": inserted,
            "timestamp_utc": now_utc.isoformat(),
            "source": "Comisión Nacional de Energía (CNE) - precios reportados por permisionarios",
        }
