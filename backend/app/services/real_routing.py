"""Enrutamiento sobre la red vial REAL mediante OSRM y Valhalla (OpenStreetMap).

Reemplaza la malla sintética de demostración: obtiene geometrías reales que siguen
las calles, con distancia y duración base. El motor EcoRuta aplica después su modelo
físico de consumo, la componente de peaje y el ajuste temporal por congestión.

Diseño:
- **OSRM** aporta su mejor ruta y alternativas (perfiles de mínima duración).
- **Valhalla** aporta variantes por preferencia de costos (evitar peajes, evitar
  autopistas, ruta más corta) que introducen los compromisos reales costo↔tiempo.
- Si un proveedor falla, se degrada al otro sin romper la petición.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger("ecoruta.services.real_routing")

OSRM_PUBLIC_BASE = "https://router.project-osrm.org"
VALHALLA_PUBLIC_BASE = "https://valhalla1.openstreetmap.de"
OSRM_TRAVEL_MODE = "driving"

# Perfiles de Valhalla: (etiqueta, opciones de costing, más corto).
_VALHALLA_PROFILES: list[tuple[str, dict, bool]] = [
    ("valhalla_rapida", {}, False),
    ("valhalla_evitar_peajes", {"auto": {"use_tolls": 0.0}}, False),
    ("valhalla_evitar_autopistas", {"auto": {"use_highways": 0.0}}, False),
    ("valhalla_mas_corta", {}, True),
]

_HTTP_TIMEOUT = 45.0


@dataclass
class RealRoute:
    """Una ruta real devuelta por un proveedor de enrutamiento externo."""

    distance_m: float
    duration_s: float
    coordinates: list[list[float]]  # [ [lon, lat], ... ]
    source: str  # "osrm" | "valhalla"
    profile: str
    has_toll: bool | None  # None si el proveedor no lo indica
    highway_distance_m: float | None = None  # tramo a velocidad de autopista (proxy de peaje)


def decode_polyline6(encoded: str) -> list[list[float]]:
    """Decodifica una polilínea con precisión 1e-6 (formato de Valhalla)."""
    coordinates: list[list[float]] = []
    index = 0
    lat = 0
    lon = 0
    length = len(encoded)
    while index < length:
        for is_lon in (False, True):
            shift = 0
            result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lon:
                lon += delta
            else:
                lat += delta
        coordinates.append([lon / 1e6, lat / 1e6])
    return coordinates


class RealRoutingService:
    """Cliente de OSRM/Valhalla que devuelve rutas reales que siguen las calles."""

    def __init__(
        self,
        osrm_base: str = OSRM_PUBLIC_BASE,
        valhalla_base: str = VALHALLA_PUBLIC_BASE,
    ) -> None:
        self.osrm_base = osrm_base.rstrip("/")
        self.valhalla_base = valhalla_base.rstrip("/")

    async def fetch_routes(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> list[RealRoute]:
        """Devuelve todas las rutas reales candidatas (OSRM + Valhalla)."""
        routes: list[RealRoute] = []
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            routes.extend(
                await self._fetch_osrm(client, origin_lat, origin_lon, dest_lat, dest_lon)
            )
            routes.extend(
                await self._fetch_valhalla(client, origin_lat, origin_lon, dest_lat, dest_lon)
            )
        return self._dedupe(routes)

    async def _fetch_osrm(
        self,
        client: httpx.AsyncClient,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> list[RealRoute]:
        url = (
            f"{self.osrm_base}/route/v1/{OSRM_TRAVEL_MODE}/"
            f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
        )
        params = {
            "overview": "full",
            "geometries": "geojson",
            "alternatives": "true",
            "annotations": "distance,speed",
        }
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001 - degradación explícita
            logger.warning("OSRM no disponible (%s); se continúa con Valhalla.", exc)
            return []

        if payload.get("code") != "Ok":
            logger.warning("OSRM respondió %s.", payload.get("code"))
            return []

        routes: list[RealRoute] = []
        for i, r in enumerate(payload.get("routes", [])):
            coords = r.get("geometry", {}).get("coordinates", [])
            if len(coords) < 2:
                continue
            routes.append(
                RealRoute(
                    distance_m=float(r["distance"]),
                    duration_s=float(r["duration"]),
                    coordinates=[[float(c[0]), float(c[1])] for c in coords],
                    source="osrm",
                    profile=f"osrm_alternativa_{i}",
                    has_toll=None,
                    highway_distance_m=self._highway_distance(r),
                )
            )
        logger.info("OSRM devolvió %d ruta(s) reales.", len(routes))
        return routes

    @staticmethod
    def _highway_distance(route_payload: dict) -> float:
        """Suma la distancia recorrida a velocidad de autopista (>80 km/h)."""
        threshold_ms = 80.0 / 3.6
        total = 0.0
        for leg in route_payload.get("legs", []):
            annotation = leg.get("annotation") or {}
            distances = annotation.get("distance") or []
            speeds = annotation.get("speed") or []
            for dist, speed in zip(distances, speeds):
                if speed >= threshold_ms:
                    total += float(dist)
        return total

    async def _fetch_valhalla(
        self,
        client: httpx.AsyncClient,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> list[RealRoute]:
        routes: list[RealRoute] = []
        for label, costing_options, shortest in _VALHALLA_PROFILES:
            body: dict = {
                "locations": [
                    {"lat": origin_lat, "lon": origin_lon},
                    {"lat": dest_lat, "lon": dest_lon},
                ],
                "costing": "auto",
                "directions_options": {"units": "kilometers"},
            }
            if costing_options:
                body["costing_options"] = costing_options
            if shortest:
                body["shortest"] = True
            try:
                resp = await client.post(f"{self.valhalla_base}/route", json=body)
                resp.raise_for_status()
                payload = resp.json()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Valhalla perfil %s falló (%s).", label, exc)
                continue

            trip = payload.get("trip") or {}
            summary = trip.get("summary") or {}
            shape = "".join(leg.get("shape", "") for leg in trip.get("legs", []))
            if not shape:
                continue
            routes.append(
                RealRoute(
                    distance_m=float(summary.get("length", 0.0)) * 1000.0,
                    duration_s=float(summary.get("time", 0.0)),
                    coordinates=decode_polyline6(shape),
                    source="valhalla",
                    profile=label,
                    has_toll=bool(summary.get("has_toll", False)),
                )
            )
        logger.info("Valhalla devolvió %d ruta(s) reales.", len(routes))
        return routes

    @staticmethod
    def _dedupe(routes: list[RealRoute]) -> list[RealRoute]:
        seen: set[tuple[int, int]] = set()
        unique: list[RealRoute] = []
        for r in routes:
            key = (int(round(r.distance_m / 100.0)), int(round(r.duration_s / 10.0)))
            if key in seen:
                continue
            seen.add(key)
            unique.append(r)
        return unique
