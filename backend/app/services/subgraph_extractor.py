"""Extracción del subgrafo factible mediante corredor elíptico amortiguado en PostGIS.

Evita la explosión combinatoria extrayendo únicamente el corredor relevante que
envuelve las rutas candidatas extremas, excluyendo automáticamente las aristas con
cierre confirmado o incompatibles con el gálibo/peso del vehículo.

Si el corredor inicial es demasiado estrecho (p. ej. en una red de malla amplia),
se reintenta con amortiguaciones progresivamente mayores antes de declarar
infactibilidad.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import ecoruta_core
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:  # pragma: no cover
    from ecoruta_core import EdgeData

logger = logging.getLogger("ecoruta.services.subgraph_extractor")

_PRICE_COLUMN_BY_FUEL = {
    "regular": "assigned_regular_price_mxn",
    "premium": "assigned_premium_price_mxn",
    "diesel": "assigned_diesel_price_mxn",
    "electric": "assigned_regular_price_mxn",  # el precio por kWh se resuelve aparte
}


class SubgraphExtractorService:
    """Extrae el subgrafo factible aplicando filtros duros y un corredor elíptico."""

    async def _nearest_nodes(
        self,
        db: AsyncSession,
        origin_lon: float,
        origin_lat: float,
        dest_lon: float,
        dest_lat: float,
    ) -> tuple[int, int] | None:
        nodes_res = await db.execute(
            text(
                """
                SELECT
                    (SELECT id FROM road_nodes
                     ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:olon, :olat), 4326) LIMIT 1) AS source_id,
                    (SELECT id FROM road_nodes
                     ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:dlon, :dlat), 4326) LIMIT 1) AS target_id;
                """
            ),
            {"olon": origin_lon, "olat": origin_lat, "dlon": dest_lon, "dlat": dest_lat},
        )
        row = nodes_res.fetchone()
        if row is None or row.source_id is None or row.target_id is None:
            return None
        return int(row.source_id), int(row.target_id)

    async def _query_edges(
        self,
        db: AsyncSession,
        origin_lon: float,
        origin_lat: float,
        dest_lon: float,
        dest_lat: float,
        day_type: str,
        speed_col: str,
        price_col: str,
        toll_col: str,
        vehicle_height_m: float,
        vehicle_weight_tons: float,
        buffer_degrees: float,
    ) -> list["EdgeData"]:
        query = text(
            f"""
            WITH corridor AS (
                SELECT ST_Buffer(
                    ST_MakeLine(
                        ST_SetSRID(ST_MakePoint(:olon, :olat), 4326),
                        ST_SetSRID(ST_MakePoint(:dlon, :dlat), 4326)
                    ),
                    :buf
                ) AS geom
            )
            SELECT
                e.id,
                e.source,
                e.target,
                ST_X(tn.geom) AS target_lon,
                ST_Y(tn.geom) AS target_lat,
                e.length_m,
                e.slope_rad,
                e.{toll_col} AS toll_mxn,
                e.{price_col} AS fuel_price_mxn,
                COALESCE(
                    ARRAY_AGG(h.{speed_col} ORDER BY h.hour_of_day)
                        FILTER (WHERE h.{speed_col} IS NOT NULL),
                    ARRAY_FILL(e.free_flow_speed_kmh, ARRAY[24])
                ) AS hourly_speeds,
                COALESCE(AVG(h.congestion_stop_index), 0.05) AS congestion_accel
            FROM road_edges e
            JOIN road_nodes tn ON tn.id = e.target
            JOIN corridor c ON ST_Intersects(e.geom, c.geom)
            LEFT JOIN edge_hourly_speeds h
                ON h.edge_id = e.id AND h.day_type = :day_type
            WHERE e.is_closed_confirmed = FALSE
              AND e.max_height_m >= :v_height
              AND e.max_weight_tons >= :v_weight
            GROUP BY e.id, tn.geom;
            """
        )
        edges_res = await db.execute(
            query,
            {
                "olon": origin_lon,
                "olat": origin_lat,
                "dlon": dest_lon,
                "dlat": dest_lat,
                "buf": buffer_degrees,
                "day_type": day_type,
                "v_height": vehicle_height_m,
                "v_weight": vehicle_weight_tons,
            },
        )
        rust_edges: list[EdgeData] = []
        for r in edges_res.fetchall():
            speeds = list(r.hourly_speeds)
            if len(speeds) < 24:
                speeds = [60.0] * 24
            rust_edges.append(
                ecoruta_core.EdgeData(
                    int(r.id),
                    int(r.source),
                    int(r.target),
                    float(r.target_lon),
                    float(r.target_lat),
                    float(r.length_m),
                    float(r.slope_rad),
                    float(r.toll_mxn),
                    float(r.fuel_price_mxn),
                    [float(s) for s in speeds],
                    float(r.congestion_accel),
                    0.0,  # rain_intensity_mmh: inyectada por el conector meteorológico
                )
            )
        return rust_edges

    async def extract_active_subgraph(
        self,
        db: AsyncSession,
        origin_lon: float,
        origin_lat: float,
        dest_lon: float,
        dest_lat: float,
        vehicle_height_m: float,
        vehicle_weight_tons: float,
        fuel_type: str,
        num_axles: int,
        day_type: str = "weekday",
        use_robust_p90: bool = False,
        buffer_degrees: float = 0.35,
    ) -> tuple[int, int, list["EdgeData"]]:
        """Devuelve ``(source_node, target_node, edges)`` listos para ``solve_td_mols``."""
        nodes = await self._nearest_nodes(db, origin_lon, origin_lat, dest_lon, dest_lat)
        if nodes is None:
            return 0, 0, []
        source_node, target_node = nodes

        speed_col = "speed_p10_kmh" if use_robust_p90 else "speed_p50_kmh"
        price_col = _PRICE_COLUMN_BY_FUEL.get(fuel_type, "assigned_regular_price_mxn")
        toll_col = "toll_cost_truck_5axles_mxn" if num_axles >= 5 else "toll_cost_autos_mxn"

        rust_edges: list[EdgeData] = []
        for factor in (1.0, 2.0, 3.5):
            rust_edges = await self._query_edges(
                db,
                origin_lon,
                origin_lat,
                dest_lon,
                dest_lat,
                day_type,
                speed_col,
                price_col,
                toll_col,
                vehicle_height_m,
                vehicle_weight_tons,
                buffer_degrees * factor,
            )
            if rust_edges:
                break

        logger.info(
            "Subgrafo extraído: source=%d target=%d, %d aristas factibles.",
            source_node,
            target_node,
            len(rust_edges),
        )
        return source_node, target_node, rust_edges
