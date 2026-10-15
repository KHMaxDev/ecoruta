"""Economía de la ruta real: consumo físico, peaje estimado y ajuste temporal.

Toma las geometrías reales de OSRM/Valhalla y les aplica el modelo longitudinal de
fuerzas del núcleo Rust para estimar el consumo (litros ICE o kWh EV), sumando una
componente de peaje y un factor de congestión dependiente de la hora/tipo de día.
El resultado es un conjunto de soluciones reales costo↔tiempo sobre el que se calcula
el frente de Pareto.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import ecoruta_core
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.real_routing import RealRoute

logger = logging.getLogger("ecoruta.services.route_economy")

# Precios de respaldo (MXN por litro o por kWh) marcados como estimación si la CNE
# no está disponible. Fuente declarada en la auditoría de procedencia.
FALLBACK_PRICE_MXN = {
    "regular": 23.80,
    "premium": 25.40,
    "diesel": 25.10,
    "electric": 4.20,
}

# Tarifas indicativas de peaje (MXN por km recorrido en vía de peaje). No sustituyen
# las tarifas oficiales de la RNC; se marcan como estimación.
TOLL_RATE_MXN_PER_KM = {"autos": 1.10, "camion": 2.40}


def congestion_factor(departure_hour: int, day_type: str, robust_p90: bool) -> float:
    """Multiplicador de tiempo por congestión según hora y tipo de día."""
    if day_type == "weekend":
        base = 1.0
    elif departure_hour in (7, 8, 9, 17, 18, 19):
        base = 1.30
    else:
        base = 1.08
    return base * (1.15 if robust_p90 else 1.0)


@dataclass
class RealRouteSolution:
    """Solución de ruta real evaluada por EcoRuta (compatible con el selector Pareto)."""

    total_cost_mxn: float
    total_time_s: float
    total_fuel_liters: float
    total_toll_mxn: float
    edge_ids: list[int]
    node_ids: list[int]
    coordinates: list[list[float]]
    distance_m: float
    baseline_duration_s: float
    source: str
    profile: str


class FuelPriceService:
    """Resuelve el precio unitario de la energía usando el padrón CNE o un respaldo."""

    @staticmethod
    async def get_unit_price(
        db: AsyncSession, fuel_type: str, lat: float, lon: float
    ) -> tuple[float, str]:
        column = {
            "regular": "regular_price_mxn",
            "premium": "premium_price_mxn",
            "diesel": "diesel_price_mxn",
        }.get(fuel_type)

        if column is not None:
            try:
                res = await db.execute(
                    text(
                        f"""
                        SELECT {column} AS price, reported_at
                        FROM fuel_stations_cne
                        WHERE {column} IS NOT NULL
                        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                        LIMIT 1;
                        """
                    ),
                    {"lon": lon, "lat": lat},
                )
                row = res.fetchone()
                if row is not None and row.price is not None:
                    ts = row.reported_at.isoformat() if row.reported_at else "desconocido"
                    return float(row.price), f"CNE ({ts})"
            except Exception as exc:  # noqa: BLE001 - la BD de estaciones es opcional
                logger.warning("Precio CNE no disponible (%s); uso respaldo marcado.", exc)

        return FALLBACK_PRICE_MXN.get(fuel_type, FALLBACK_PRICE_MXN["regular"]), "fallback_estimate"


class RouteEconomyService:
    """Evalúa rutas reales con el modelo físico y conforma el conjunto de soluciones."""

    def __init__(self, air_density: float = 1.05) -> None:
        self.air_density = air_density

    def evaluate(
        self,
        route: RealRoute,
        vehicle: ecoruta_core.VehicleParams,
        unit_price_mxn: float,
        time_multiplier: float,
        num_axles: int,
    ) -> RealRouteSolution:
        fuel_units = ecoruta_core.compute_energy_units(
            route.distance_m,
            0.0,  # pendiente media: sin DEM cargado (se marca como estimación)
            route.duration_s,
            0.0,  # inercia media por congestión
            0.0,  # intensidad de lluvia (se inyecta vía conector meteorológico aparte)
            vehicle,
            self.air_density,
        )
        fuel_cost = fuel_units * unit_price_mxn

        # Distancia sujeta a peaje: preferimos el tramo medido a velocidad de autopista
        # (OSRM); si no, usamos el atributo de peaje del proveedor (Valhalla).
        if route.highway_distance_m is not None:
            toll_distance_m = route.highway_distance_m
        elif route.has_toll:
            toll_distance_m = route.distance_m
        else:
            toll_distance_m = 0.0

        toll_rate = TOLL_RATE_MXN_PER_KM["camion" if num_axles >= 5 else "autos"]
        toll = (toll_distance_m / 1000.0) * toll_rate

        return RealRouteSolution(
            total_cost_mxn=fuel_cost + toll,
            total_time_s=route.duration_s * time_multiplier,
            total_fuel_liters=fuel_units,
            total_toll_mxn=toll,
            edge_ids=[],
            node_ids=[],
            coordinates=route.coordinates,
            distance_m=route.distance_m,
            baseline_duration_s=route.duration_s,
            source=route.source,
            profile=route.profile,
        )


def filter_non_dominated(solutions: list[RealRouteSolution]) -> list[RealRouteSolution]:
    """Descarta soluciones dominadas (mayor costo y mayor tiempo)."""
    front: list[RealRouteSolution] = []
    for a in solutions:
        dominated = False
        for b in solutions:
            if a is b:
                continue
            if (
                b.total_cost_mxn <= a.total_cost_mxn
                and b.total_time_s <= a.total_time_s
                and (b.total_cost_mxn < a.total_cost_mxn or b.total_time_s < a.total_time_s)
            ):
                dominated = True
                break
        if not dominated:
            front.append(a)
    return sorted(front, key=lambda s: s.total_cost_mxn)
