"""Conector de contexto territorial municipal del SESNSP.

Cruza las rutas del frente de Pareto con las zonas estadísticas municipales del
SESNSP y las de susceptibilidad de inundación de CONAGUA para adjuntar avisos
transparentes, sin alterar los pesos monetarios con falsas probabilidades por calle.

Regla arquitectónica inquebrantable: los datos del SESNSP tienen resolución
municipal y NUNCA deben convertirse en puntuaciones por segmento vial.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("ecoruta.connectors.sesnsp")

EPISTEMOLOGICAL_DISCLAIMER = (
    "Indicador estadístico agregado a nivel municipal/cuenca. "
    "No representa una probabilidad exacta en el segmento vial individual."
)


class SESNSPTerritorialContextService:
    """Adjunta avisos contextuales municipales sin micro-puntuaciones por calle."""

    @staticmethod
    async def audit_route_context(
        db: AsyncSession,
        edge_ids: list[int],
    ) -> list[dict[str, Any]]:
        if not edge_ids:
            return []

        query = text(
            """
            SELECT DISTINCT
                hz.hazard_type,
                hz.region_code,
                hz.description,
                hz.severity_level,
                hz.source_name,
                hz.source_timestamp,
                hz.spatial_resolution
            FROM road_edges e
            JOIN hazard_zones hz ON ST_Intersects(e.geom, hz.geom)
            WHERE e.id = ANY(:edge_ids)
              AND hz.severity_level IN ('informativo', 'precaucion');
            """
        )

        res = await db.execute(query, {"edge_ids": edge_ids})
        notices: list[dict[str, Any]] = []
        for row in res.fetchall():
            notices.append(
                {
                    "type": row.hazard_type,
                    "region_code": row.region_code,
                    "message": row.description,
                    "severity": row.severity_level,
                    "source": row.source_name,
                    "source_timestamp": (
                        row.source_timestamp.isoformat() if row.source_timestamp else None
                    ),
                    "spatial_resolution": row.spatial_resolution,
                    "epistemological_disclaimer": EPISTEMOLOGICAL_DISCLAIMER,
                }
            )
        return notices

    @staticmethod
    async def audit_route_geometry_context(
        db: AsyncSession,
        coordinates: list[list[float]],
    ) -> list[dict[str, Any]]:
        """Avisos contextuales cruzando la geometría real de la ruta con las zonas.

        Se usa en el motor de red real (OSRM/Valhalla), donde no existen ``edge_ids``.
        """
        if len(coordinates) < 2:
            return []

        wkt = "LINESTRING(" + ",".join(f"{float(lon)} {float(lat)}" for lon, lat in coordinates) + ")"
        query = text(
            """
            SELECT DISTINCT
                hz.hazard_type,
                hz.region_code,
                hz.description,
                hz.severity_level,
                hz.source_name,
                hz.source_timestamp,
                hz.spatial_resolution
            FROM hazard_zones hz
            WHERE ST_Intersects(hz.geom, ST_GeomFromText(:wkt, 4326))
              AND hz.severity_level IN ('informativo', 'precaucion');
            """
        )
        res = await db.execute(query, {"wkt": wkt})
        notices: list[dict[str, Any]] = []
        for row in res.fetchall():
            notices.append(
                {
                    "type": row.hazard_type,
                    "region_code": row.region_code,
                    "message": row.description,
                    "severity": row.severity_level,
                    "source": row.source_name,
                    "source_timestamp": (
                        row.source_timestamp.isoformat() if row.source_timestamp else None
                    ),
                    "spatial_resolution": row.spatial_resolution,
                    "epistemological_disclaimer": EPISTEMOLOGICAL_DISCLAIMER,
                }
            )
        return notices
