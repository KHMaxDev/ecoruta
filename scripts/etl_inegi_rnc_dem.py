"""
EcoRuta — Pipeline ETL Geoespacial (INEGI RNC + DEM SRTM/INEGI + PostGIS)

1. Lee la Red Vial y Plazas de Cobro de la Red Nacional de Caminos (RNC - INEGI).
2. Reproyecta geometrías a EPSG:4326 (WGS84).
3. Muestrea un GeoTIFF de elevación (Continuo de Elevaciones Mexicano / SRTM)
   para calcular la pendiente longitudinal real en radianes de cada segmento vial.
4. Genera las aristas dirigidas según el sentido de circulación (`SENTIDO`/`CIRCULACIO`)
   y las inserta en PostGIS, poblando perfiles horarios base en `edge_hourly_speeds`.

Uso:
    python scripts/etl_inegi_rnc_dem.py \
        --roads ./data/raw/rnc_vialidades.gpkg \
        --tolls ./data/raw/rnc_casetas.gpkg \
        --dem ./data/raw/dem_piloto.tif

Variables de entorno (ver .env.example):
    DATABASE_URL_SYNC, PILOT_BBOX_*, RNC_ROADS_PATH, RNC_TOLLS_PATH, DEM_GEOTIFF_PATH
"""

from __future__ import annotations

import argparse
import logging
import math
import os
from typing import Any, Dict, List, Tuple

import geopandas as gpd
import rasterio
from rasterio.crs import CRS
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ecoruta.etl_rnc")

DEFAULT_DB_URL = "postgresql+psycopg2://ecoruta_user:ecoruta_secure_password@localhost:5432/ecoruta_db"
DEFAULT_BBOX: Tuple[float, float, float, float] = (-100.5, 18.8, -98.0, 20.2)  # CDMX-Puebla-Toluca
SLOPE_LIMIT_RAD = 0.25


class InegiRNCGeospatialETL:
    """Extrae, enriquece con elevación y carga la RNC en PostGIS."""

    def __init__(self, db_url: str, dem_geotiff_path: str) -> None:
        self.engine: Engine = create_engine(db_url, future=True)
        self.dem_path: str = dem_geotiff_path
        self.dem_dataset = rasterio.open(dem_geotiff_path)
        if self.dem_dataset.crs is None:
            logger.warning("El DEM no declara CRS; asumiendo EPSG:4326.")
        elif self.dem_dataset.crs.to_epsg() != 4326:
            logger.info("DEM en CRS %s; se muestreará usando coordenadas geográficas WGS84.", self.dem_dataset.crs)
        self._dem_band = self.dem_dataset.read(1)

    def sample_elevation_m(self, lon: float, lat: float) -> float:
        """Altitud (m.s.n.m.) muestreada del raster DEM en (lon, lat)."""
        try:
            row, col = self.dem_dataset.index(lon, lat)
            if row < 0 or col < 0 or row >= self.dem_dataset.height or col >= self.dem_dataset.width:
                return 0.0
            val = float(self._dem_band[row, col])
            if math.isnan(val) or val < -500.0 or val > 6000.0:
                return 0.0
            return val
        except Exception:  # noqa: BLE001 - nodo fuera de la ventana del raster
            return 0.0

    @staticmethod
    def extract_endpoints(geom: Any) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Coordenadas (lon, lat) inicial y final de un LineString/MultiLineString."""
        from shapely.geometry import LineString, MultiLineString

        if isinstance(geom, MultiLineString):
            coords = list(geom.geoms[0].coords) + list(geom.geoms[-1].coords)
        elif isinstance(geom, LineString):
            coords = list(geom.coords)
        else:
            raise ValueError(f"Geometría no soportada: {type(geom)}")
        return (float(coords[0][0]), float(coords[0][1])), (float(coords[-1][0]), float(coords[-1][1]))

    @staticmethod
    def _is_two_way(circulation: str) -> bool:
        value = (circulation or "").lower()
        return ("dos" in value) or ("ambos" in value) or ("bidirec" in value)

    def process_and_load_rnc(
        self,
        rnc_roads_path: str,
        rnc_tolls_path: str | None = None,
        bbox_filter: Tuple[float, float, float, float] = DEFAULT_BBOX,
    ) -> Dict[str, int]:
        """Procesa un recorte regional o nacional de la RNC del INEGI."""
        logger.info("Cargando capa de vialidades RNC desde %s...", rnc_roads_path)
        gdf_roads = gpd.read_file(rnc_roads_path)

        if gdf_roads.crs is not None and gdf_roads.crs.to_epsg() != 4326:
            logger.info("Reproyectando vialidades de %s a EPSG:4326...", gdf_roads.crs)
            gdf_roads = gdf_roads.to_crs(epsg=4326)

        gdf_roads = gdf_roads.cx[bbox_filter[0]:bbox_filter[2], bbox_filter[1]:bbox_filter[3]]
        logger.info("Segmentos viales dentro del corredor: %d", len(gdf_roads))

        if rnc_tolls_path:
            try:
                gdf_tolls = gpd.read_file(rnc_tolls_path)
                if gdf_tolls.crs is not None and gdf_tolls.crs.to_epsg() != 4326:
                    gdf_tolls = gdf_tolls.to_crs(epsg=4326)
                logger.info("Plazas de cobro cargadas: %d", len(gdf_tolls))
            except Exception as exc:  # noqa: BLE001
                logger.warning("No se pudo cargar el shapefile de casetas '%s': %s", rnc_tolls_path, exc)

        node_registry: Dict[Tuple[int, int], int] = {}
        nodes_to_insert: List[Dict[str, Any]] = []
        edges_to_insert: List[Dict[str, Any]] = []
        next_node_id = 1

        def get_or_create_node(lon: float, lat: float) -> Tuple[int, float]:
            nonlocal next_node_id
            key = (int(round(lon * 100000)), int(round(lat * 100000)))  # ~1 m de precisión
            if key in node_registry:
                nid = node_registry[key]
                return nid, nodes_to_insert[nid - 1]["elevation_m"]
            elev = self.sample_elevation_m(lon, lat)
            nid = next_node_id
            next_node_id += 1
            node_registry[key] = nid
            nodes_to_insert.append({"id": nid, "lon": lon, "lat": lat, "elevation_m": elev})
            return nid, elev

        for idx, row in gdf_roads.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue

            (lon1, lat1), (lon2, lat2) = self.extract_endpoints(geom)
            u_id, elev_u = get_or_create_node(lon1, lat1)
            v_id, elev_v = get_or_create_node(lon2, lat2)
            if u_id == v_id:
                continue

            length_m = float(row.get("LONGITUD", 0.0) or 0.0)
            if length_m <= 1.0:
                length_m = max(10.0, float(geom.length) * 111320.0)

            delta_h = elev_v - elev_u
            slope_uv = max(-SLOPE_LIMIT_RAD, min(SLOPE_LIMIT_RAD, math.atan2(delta_h, length_m)))
            slope_vu = -slope_uv

            speed_kmh = float(row.get("VELOCIDAD", 60.0) or 60.0)
            road_name = str(row.get("NOMBRE", "Vialidad s/n") or "Vialidad s/n")
            road_class = str(row.get("TIPO_VIAL", "Carretera") or "Carretera").lower()
            circulacion = str(row.get("CIRCULACIO", row.get("SENTIDO", "Dos sentidos")) or "Dos sentidos")
            peaje_flag = str(row.get("PEAJE", "No") or "No").upper()

            toll_auto = float(row.get("TARIFA_A", 0.0) or 0.0) if peaje_flag == "SI" else 0.0
            toll_truck = float(row.get("TARIFA_C5", toll_auto * 4.2) or 0.0) if peaje_flag == "SI" else 0.0

            from shapely.geometry import LineString, MultiLineString

            base_line = geom if isinstance(geom, LineString) else geom.geoms[0]
            rnc_id = str(row.get("ID_RED", idx))

            edges_to_insert.append({
                "source": u_id, "target": v_id, "rnc_id": rnc_id,
                "road_name": road_name, "road_class": road_class,
                "length_m": length_m, "slope_rad": slope_uv,
                "free_flow_speed_kmh": speed_kmh,
                "toll_cost_autos_mxn": toll_auto, "toll_cost_truck_5axles_mxn": toll_truck,
                "wkt": base_line.wkt,
            })

            if self._is_two_way(circulacion):
                reverse = LineString(list(base_line.coords)[::-1])
                edges_to_insert.append({
                    "source": v_id, "target": u_id, "rnc_id": f"{rnc_id}_REV",
                    "road_name": road_name, "road_class": road_class,
                    "length_m": length_m, "slope_rad": slope_vu,
                    "free_flow_speed_kmh": speed_kmh,
                    "toll_cost_autos_mxn": toll_auto, "toll_cost_truck_5axles_mxn": toll_truck,
                    "wkt": reverse.wkt,
                })

        with self.engine.begin() as conn:
            logger.info("Insertando %d nodos topológicos con elevación DEM...", len(nodes_to_insert))
            for n in nodes_to_insert:
                conn.execute(
                    text("""
                        INSERT INTO road_nodes (id, elevation_m, geom)
                        VALUES (:id, :elevation_m, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                        ON CONFLICT (id) DO NOTHING;
                    """),
                    n,
                )

            logger.info("Insertando %d aristas dirigidas enriquecidas...", len(edges_to_insert))
            for e in edges_to_insert:
                conn.execute(
                    text("""
                        INSERT INTO road_edges (
                            source, target, rnc_id, road_name, road_class,
                            length_m, slope_rad, free_flow_speed_kmh,
                            toll_cost_autos_mxn, toll_cost_truck_5axles_mxn, geom
                        ) VALUES (
                            :source, :target, :rnc_id, :road_name, :road_class,
                            :length_m, :slope_rad, :free_flow_speed_kmh,
                            :toll_cost_autos_mxn, :toll_cost_truck_5axles_mxn,
                            ST_GeomFromText(:wkt, 4326)
                        );
                    """),
                    e,
                )

            logger.info("Generando series horarias de velocidad inicial (24h)...")
            conn.execute(
                text("""
                    INSERT INTO edge_hourly_speeds (
                        edge_id, day_type, hour_of_day, speed_p50_kmh, speed_p10_kmh, congestion_stop_index
                    )
                    SELECT
                        e.id, 'weekday', h.hr,
                        CASE
                            WHEN h.hr IN (7, 8, 9, 18, 19, 20) THEN GREATEST(8.0, e.free_flow_speed_kmh * 0.48)
                            WHEN h.hr IN (13, 14, 15, 16, 17) THEN GREATEST(12.0, e.free_flow_speed_kmh * 0.72)
                            ELSE e.free_flow_speed_kmh * 0.95
                        END,
                        CASE
                            WHEN h.hr IN (7, 8, 9, 18, 19, 20) THEN GREATEST(5.0, e.free_flow_speed_kmh * 0.30)
                            WHEN h.hr IN (13, 14, 15, 16, 17) THEN GREATEST(8.0, e.free_flow_speed_kmh * 0.52)
                            ELSE e.free_flow_speed_kmh * 0.85
                        END,
                        CASE WHEN h.hr IN (7, 8, 9, 18, 19, 20) THEN 0.24 ELSE 0.05 END
                    FROM road_edges e
                    CROSS JOIN generate_series(0, 23) AS h(hr)
                    ON CONFLICT DO NOTHING;
                """)
            )

            conn.execute(
                text("""
                    INSERT INTO data_ingest_audit (source_name, dataset, spatial_resolution, records_affected, status, notes)
                    VALUES ('INEGI RNC', 'road_nodes/road_edges/edge_hourly_speeds', 'tramo_vial', :n,
                            'ok', 'ETL ETL INEGI RNC + DEM SRTM');
                """),
                {"n": len(edges_to_insert)},
            )

        logger.info("Pipeline ETL Geoespacial completado con éxito.")
        return {"nodes": len(nodes_to_insert), "edges": len(edges_to_insert)}


def _env_bbox() -> Tuple[float, float, float, float]:
    try:
        return (
            float(os.getenv("PILOT_BBOX_MIN_LON", DEFAULT_BBOX[0])),
            float(os.getenv("PILOT_BBOX_MIN_LAT", DEFAULT_BBOX[1])),
            float(os.getenv("PILOT_BBOX_MAX_LON", DEFAULT_BBOX[2])),
            float(os.getenv("PILOT_BBOX_MAX_LAT", DEFAULT_BBOX[3])),
        )
    except (TypeError, ValueError):
        return DEFAULT_BBOX


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL geoespacial INEGI RNC + DEM para EcoRuta.")
    parser.add_argument("--roads", default=os.getenv("RNC_ROADS_PATH", "./data/raw/rnc_vialidades.gpkg"))
    parser.add_argument("--tolls", default=os.getenv("RNC_TOLLS_PATH", "./data/raw/rnc_casetas.gpkg"))
    parser.add_argument("--dem", default=os.getenv("DEM_GEOTIFF_PATH", "./data/raw/dem_piloto.tif"))
    parser.add_argument("--db", default=os.getenv("DATABASE_URL_SYNC", DEFAULT_DB_URL))
    args = parser.parse_args()

    if not os.path.exists(args.roads):
        raise SystemExit(f"No existe el archivo de vialidades RNC: {args.roads}")
    if not os.path.exists(args.dem):
        raise SystemExit(f"No existe el GeoTIFF DEM: {args.dem}")

    etl = InegiRNCGeospatialETL(db_url=args.db, dem_geotiff_path=args.dem)
    stats = etl.process_and_load_rnc(
        rnc_roads_path=args.roads,
        rnc_tolls_path=args.tolls if os.path.exists(args.tolls) else None,
        bbox_filter=_env_bbox(),
    )
    logger.info("Resultado ETL: %s", stats)


if __name__ == "__main__":
    main()
