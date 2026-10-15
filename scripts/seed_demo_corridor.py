"""
EcoRuta — Semilla de corredor demo autocontenido (auditoría 7.4 / Sprint 1).

Puebla un corredor navegable CDMX–Toluca–Puebla directamente en PostGIS usando
el esquema real de `init_db.sql`. No requiere descargar shapefiles del INEGI ni
rasters DEM: la elevación se genera analíticamente y la pendiente se calcula con
el mismo muestreo longitudinal de 50 m que usa el ETL (auditoría 7.2), de modo
que el motor ve tramos con subidas/bajadas intermedias reales.

Contenido generado:
  * ~240 nodos / ~900 aristas bidireccionales con pendientes no triviales.
  * 3 plazas de cobro (`is_toll_booth`) con tarifas marcadas como 'estimado'.
  * 6 estaciones de combustible CNE con precios dispares (para el KNN).
  * 2 polígonos de riesgo/contexto (inundación CONAGUA + contexto SESNSP).

Idempotente: se identifica por el prefijo rnc_id 'ECORUTA_DEMO_' y el rango de
node ids [900000, 999999].

Uso:
    python scripts/seed_demo_corridor.py

Variables de entorno (ver .env.example): DB_HOST, DB_PORT, DB_NAME, DB_USER,
DB_PASSWORD — o bien DATABASE_URL_SYNC.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
from typing import Any, Dict, List, Sequence, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ecoruta.seed_corridor")

NODE_ID_BASE = 900_000
RNC_PREFIX = "ECORUTA_DEMO_"
TOLL_SOURCE_STATUS = "estimado"

DEFAULT_DB_URL = (
    "postgresql+asyncpg://ecoruta_user:ecoruta_secure_password@localhost:5432/ecoruta_db"
)

# Malla del corredor: lat 18.85..19.45 (15 filas), lon -99.55..-99.10 (16 columnas).
GRID_ROWS = 15
GRID_COLS = 16
LAT_MIN, LAT_STEP = 18.85, 0.04
LON_MIN, LON_STEP = -99.55, 0.03

SLOPE_LIMIT_RAD = 0.25


def _env_db_url() -> str:
    """URL de SQLAlchemy forzada al driver asíncrono `asyncpg` (el que trae el backend)."""
    url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
    if url:
        for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+asyncpg://" + url[len(prefix):]
        return url
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "ecoruta_db")
    user = os.getenv("DB_USER", "ecoruta_user")
    pwd = os.getenv("DB_PASSWORD", "ecoruta_secure_password")
    return f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{name}"


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6_371_000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2.0 * r * math.asin(math.sqrt(a))


def _elevation_m(lon: float, lat: float) -> float:
    """Campo de elevación analítico: valles/crestas del corredor transvolcánico."""
    return 2260.0 + 90.0 * math.sin(math.radians((lat - 18.85) * 1200.0)) + 60.0 * math.cos(math.radians((lon + 99.55) * 1600.0))


def _effective_slope_rad(lon1: float, lat1: float, lon2: float, lat2: float, length_m: float) -> Tuple[float, float]:
    """Pendiente efectiva muestreando cada 50 m (idéntico al ETL: auditoría 7.2)."""
    num_samples = max(2, min(40, int(length_m // 50.0) + 1))
    elevs = [
        _elevation_m(lon1 + (lon2 - lon1) * (i / (num_samples - 1)), lat1 + (lat2 - lat1) * (i / (num_samples - 1)))
        for i in range(num_samples)
    ]
    pos = sum(max(0.0, elevs[i + 1] - elevs[i]) for i in range(len(elevs) - 1))
    neg = sum(max(0.0, elevs[i] - elevs[i + 1]) for i in range(len(elevs) - 1))
    fwd = max(-SLOPE_LIMIT_RAD, min(SLOPE_LIMIT_RAD, math.atan2(pos - 0.35 * neg, length_m)))
    rev = max(-SLOPE_LIMIT_RAD, min(SLOPE_LIMIT_RAD, math.atan2(neg - 0.35 * pos, length_m)))
    return fwd, rev


async def _insert_batch(conn: Any, sql: str, rows: Sequence[Dict[str, Any]], label: str) -> None:
    batch = 10_000
    total = 0
    for start in range(0, len(rows), batch):
        chunk = list(rows[start:start + batch])
        await conn.execute(text(sql), chunk)
        total += len(chunk)
    logger.info("Insertados %d registros en %s", total, label)


async def seed_corridor(db_url: str) -> Dict[str, int]:
    engine = create_async_engine(db_url, future=True)

    nodes: List[Tuple[int, float, float]] = []
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            nid = NODE_ID_BASE + r * GRID_COLS + c
            lat = LAT_MIN + r * LAT_STEP
            lon = LON_MIN + c * LON_STEP
            nodes.append((nid, lon, lat))

    # --- Selección de 3 plazas de cobro (distribuidas en el corredor) --------
    toll_node_ids = {
        NODE_ID_BASE + 4 * GRID_COLS + 4,
        NODE_ID_BASE + 8 * GRID_COLS + 9,
        NODE_ID_BASE + 12 * GRID_COLS + 13,
    }

    def is_toll_segment(s: int, t: int) -> bool:
        return (s in toll_node_ids) or (t in toll_node_ids)

    node_rows = [
        {"id": nid, "elevation_m": _elevation_m(lon, lat), "lon": lon, "lat": lat,
         "is_toll": nid in toll_node_ids}
        for nid, lon, lat in nodes
    ]

    def node_at(r: int, c: int) -> Tuple[int, float, float]:
        return nodes[r * GRID_COLS + c]

    undirected: List[Tuple[Tuple[int, float, float], Tuple[int, float, float]]] = []
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS - 1):
            undirected.append((node_at(r, c), node_at(r, c + 1)))
    for r in range(GRID_ROWS - 1):
        for c in range(GRID_COLS):
            undirected.append((node_at(r, c), node_at(r + 1, c)))

    edge_rows: List[Dict[str, Any]] = []
    for (s_id, s_lon, s_lat), (t_id, t_lon, t_lat) in undirected:
        length_m = max(10.0, _haversine_m(s_lon, s_lat, t_lon, t_lat))
        slope_fwd, slope_rev = _effective_slope_rad(s_lon, s_lat, t_lon, t_lat, length_m)
        toll_autos = 42.0 if is_toll_segment(s_id, t_id) else 0.0
        toll_bus = 68.0 if is_toll_segment(s_id, t_id) else 0.0
        toll_truck = 126.0 if is_toll_segment(s_id, t_id) else 0.0
        status = TOLL_SOURCE_STATUS if is_toll_segment(s_id, t_id) else "desconocido"

        base = {
            "road_name": "Corredor EcoRuta (demo)",
            "road_class": "autopista" if toll_autos > 0 else "carretera",
            "length_m": length_m,
            "free_flow_speed_kmh": 110.0 if toll_autos > 0 else 72.0,
            "toll_autos": toll_autos,
            "toll_bus": toll_bus,
            "toll_truck": toll_truck,
            "status": status,
        }
        edge_rows.append({**base, "source": s_id, "target": t_id, "slope": slope_fwd,
                          "lon1": s_lon, "lat1": s_lat, "lon2": t_lon, "lat2": t_lat,
                          "rnc_id": f"{RNC_PREFIX}{s_id}_{t_id}"})
        edge_rows.append({**base, "source": t_id, "target": s_id, "slope": slope_rev,
                          "lon1": t_lon, "lat1": t_lat, "lon2": s_lon, "lat2": s_lat,
                          "rnc_id": f"{RNC_PREFIX}{t_id}_{s_id}"})

    station_rows = [
        {"permiso_cre": "ECORUTA-DEMO-01", "name": "Pemex CDMX Norte (demo)", "reg": 23.80, "prem": 25.40, "dies": 25.10,
         "lon": LON_MIN + 2 * LON_STEP, "lat": LAT_MIN + 2 * LAT_STEP},
        {"permiso_cre": "ECORUTA-DEMO-02", "name": "BP Toluca Oriente (demo)", "reg": 24.15, "prem": 25.75, "dies": 24.55,
         "lon": LON_MIN + 6 * LON_STEP, "lat": LAT_MIN + 6 * LAT_STEP},
        {"permiso_cre": "ECORUTA-DEMO-03", "name": "Shell Amecameca (demo)", "reg": 23.35, "prem": 25.05, "dies": 25.90,
         "lon": LON_MIN + 9 * LON_STEP, "lat": LAT_MIN + 4 * LAT_STEP},
        {"permiso_cre": "ECORUTA-DEMO-04", "name": "Mobil Chalco (demo)", "reg": 24.60, "prem": 26.10, "dies": 24.80,
         "lon": LON_MIN + 11 * LON_STEP, "lat": LAT_MIN + 9 * LAT_STEP},
        {"permiso_cre": "ECORUTA-DEMO-05", "name": "Pemex Puebla Sur (demo)", "reg": 23.20, "prem": 24.90, "dies": 24.40,
         "lon": LON_MIN + 14 * LON_STEP, "lat": LAT_MIN + 12 * LAT_STEP},
        {"permiso_cre": "ECORUTA-DEMO-06", "name": "Axxion Ocoyoacac (demo)", "reg": 24.95, "prem": 26.30, "dies": 25.60,
         "lon": LON_MIN + 1 * LON_STEP, "lat": LAT_MIN + 8 * LAT_STEP},
    ]

    async with engine.begin() as conn:
        logger.info("Limpiando semilla demo anterior (prefijo %s)...", RNC_PREFIX)
        await conn.execute(text("DELETE FROM edge_hourly_speeds WHERE edge_id IN "
                                "(SELECT id FROM road_edges WHERE rnc_id LIKE :p)"), {"p": f"{RNC_PREFIX}%"})
        await conn.execute(text("DELETE FROM road_edges WHERE rnc_id LIKE :p"), {"p": f"{RNC_PREFIX}%"})
        await conn.execute(text("DELETE FROM road_nodes WHERE id BETWEEN :a AND :b"),
                           {"a": NODE_ID_BASE, "b": NODE_ID_BASE + 9999})
        await conn.execute(text("DELETE FROM fuel_stations_cne WHERE permiso_cre LIKE 'ECORUTA-DEMO-%'"))
        await conn.execute(text("DELETE FROM hazard_zones WHERE source_name = 'EcoRuta demo seed'"))

        await _insert_batch(
            conn,
            """
            INSERT INTO road_nodes (id, elevation_m, is_toll_booth, geom)
            VALUES (:id, :elevation_m, :is_toll,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            """,
            node_rows,
            "road_nodes",
        )

        await _insert_batch(
            conn,
            """
            INSERT INTO road_edges (
                source, target, rnc_id, road_name, road_class, length_m, slope_rad,
                free_flow_speed_kmh, toll_cost_autos_mxn, toll_cost_bus_2axles_mxn,
                toll_cost_truck_5axles_mxn, toll_source_status, geom
            ) VALUES (
                :source, :target, :rnc_id, :road_name, :road_class, :length_m, :slope,
                :free_flow_speed_kmh, :toll_autos, :toll_bus, :toll_truck, :status,
                ST_MakeLine(ST_SetSRID(ST_MakePoint(:lon1, :lat1), 4326),
                            ST_SetSRID(ST_MakePoint(:lon2, :lat2), 4326))
            )
            """,
            edge_rows,
            "road_edges",
        )
        await conn.execute(text("SELECT setval('road_edges_id_seq', COALESCE((SELECT MAX(id) FROM road_edges), 1))"))

        logger.info("Generando perfiles horarios (weekday + weekend, 24 h)...")
        await conn.execute(
            text("""
                INSERT INTO edge_hourly_speeds
                    (edge_id, day_type, hour_of_day, speed_p50_kmh, speed_p10_kmh, congestion_stop_index)
                SELECT
                    e.id, dt.day_type, h.hour,
                    GREATEST(e.free_flow_speed_kmh * CASE
                        WHEN h.hour BETWEEN 7 AND 9 OR h.hour BETWEEN 17 AND 19 THEN 0.55
                        ELSE 0.98 END, 15.0),
                    GREATEST(e.free_flow_speed_kmh * CASE
                        WHEN h.hour BETWEEN 7 AND 9 OR h.hour BETWEEN 17 AND 19 THEN 0.35
                        ELSE 0.82 END, 10.0),
                    CASE WHEN h.hour BETWEEN 7 AND 9 OR h.hour BETWEEN 17 AND 19 THEN 0.28 ELSE 0.05 END
                FROM road_edges e
                CROSS JOIN (VALUES ('weekday'), ('weekend')) AS dt(day_type)
                CROSS JOIN generate_series(0, 23) AS h(hour)
                WHERE e.rnc_id LIKE :p
            """),
            {"p": f"{RNC_PREFIX}%"},
        )

        await _insert_batch(
            conn,
            """
            INSERT INTO fuel_stations_cne
                (permiso_cre, station_name, regular_price_mxn, premium_price_mxn,
                 diesel_price_mxn, reported_at, geom)
            VALUES (:permiso_cre, :name, :reg, :prem, :dies, NOW(),
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            """,
            station_rows,
            "fuel_stations_cne",
        )

        logger.info("Insertando zonas de riesgo/contexto...")
        await conn.execute(
            text("""
                INSERT INTO hazard_zones
                    (hazard_type, region_code, description, severity_level, source_name,
                     source_timestamp, spatial_resolution, confidence_level, geom)
                VALUES
                    ('inundacion_historica', 'RH26',
                     'Cuenca Balsas: suelo susceptible a inundación (demo)', 'precaucion',
                     'EcoRuta demo seed', NOW(), 'poligono_cuenca', 'media',
                     ST_Multi(ST_Buffer(ST_SetSRID(ST_MakePoint(:lon_a, :lat_a), 4326), 0.06))),
                    ('contexto_municipal_sesnsp', '21114',
                     'Incidencia delictiva municipal (Puebla) - solo contexto, no por calle',
                     'informativo', 'EcoRuta demo seed', NOW(), 'agregado_municipal', 'media',
                     ST_Multi(ST_Buffer(ST_SetSRID(ST_MakePoint(:lon_b, :lat_b), 4326), 0.08)))
            """),
            {
                "lon_a": LON_MIN + 5 * LON_STEP, "lat_a": LAT_MIN + 5 * LAT_STEP,
                "lon_b": LON_MIN + 13 * LON_STEP, "lat_b": LAT_MIN + 11 * LAT_STEP,
            },
        )

        await conn.execute(
            text("""
                INSERT INTO data_ingest_audit
                    (source_name, dataset, spatial_resolution, records_affected, status, notes)
                VALUES ('EcoRuta demo seed', 'road_nodes/road_edges/edge_hourly_speeds',
                        'tramo_vial', :n, 'fallback_estimate',
                        'Red sintética de demostración; NO es RNC del INEGI.')
            """),
            {"n": len(edge_rows)},
        )

    await engine.dispose()
    return {"nodes": len(node_rows), "edges": len(edge_rows), "stations": len(station_rows)}


def main() -> None:
    db_url = _env_db_url()
    stats = asyncio.run(seed_corridor(db_url))
    logger.info("Semilla de corredor demo completada: %s", stats)


if __name__ == "__main__":
    main()
