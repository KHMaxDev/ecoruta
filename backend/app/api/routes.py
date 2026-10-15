"""Endpoints REST de cálculo, auditoría y administración de EcoRuta.

El motor opera sobre la **red vial real** (OSRM + Valhalla / OpenStreetMap): obtiene
geometrías que siguen las calles y les aplica el modelo físico de consumo, la
componente de peaje y el ajuste temporal por congestión.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

import ecoruta_core
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.connectors.cne_combustible import CNEFuelConnector
from app.connectors.conagua_riesgos import WeatherAndFloodHazardConnector
from app.connectors.sesnsp_seguridad import SESNSPTerritorialContextService
from app.db import get_db
from app.schemas.routes import (
    ComparisonOut,
    DataProvenanceAudit,
    MultistopRequest,
    MultistopResponse,
    OptimizeResponse,
    RouteRequest,
    VehicleProfileOut,
    WeatherOut,
)
from app.services.multi_stop_vrp import MultiStopVRPOptimizer
from app.services.pareto_selector import ParetoPreferenceSelector
from app.services.real_routing import RealRoute, RealRoutingService
from app.services.route_economy import (
    FuelPriceService,
    RouteEconomyService,
    congestion_factor,
    filter_non_dominated,
)

logger = logging.getLogger("ecoruta.api")

router = APIRouter(prefix=settings.api_v1_prefix)

_redis: aioredis.Redis | None = None

_ENERGY_DENSITY_J_PER_UNIT = {
    "regular": 32.1e6,
    "premium": 32.1e6,
    "diesel": 35.5e6,
    "electric": 3.6e6,
}

_PROVENANCE = {
    "road_network_source": (
        "OpenStreetMap vía OSRM (perfiles de mínima duración) y Valhalla "
        "(variantes por preferencia de costos) — red vial real."
    ),
    "fuel_price_source": (
        "Comisión Nacional de Energía (CNE); sustituto explícito cuando no responde."
    ),
    "toll_source": (
        "Estimación por perfil de peaje del motor (Valhalla 'has_toll'); "
        "no se ha cargado la tarifa oficial de la RNC."
    ),
    "safety_context_notice": (
        "Los indicadores de incidencia delictiva provienen del SESNSP a escala municipal. "
        "Son informativos y NO representan probabilidades de delito por calle."
    ),
}


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _redis


def _cache_key(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "ecoruta:optimize:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _audit(mode: str) -> DataProvenanceAudit:
    return DataProvenanceAudit(
        **_PROVENANCE,
        uncertainty_mode=mode,
        computed_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def _google_maps_url(o_lat: float, o_lon: float, d_lat: float, d_lon: float) -> str:
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={o_lat},{o_lon}&destination={d_lat},{d_lon}&travelmode=driving"
    )


async def _load_vehicle_profile(db: AsyncSession, code: str) -> VehicleProfileOut:
    res = await db.execute(
        text(
            """
            SELECT code, name, fuel_type, empty_mass_kg, frontal_area_m2, drag_coeff_cd,
                   rolling_coeff_crr, drivetrain_efficiency, idle_power_watts, nominal_kml,
                   num_axles, height_m, max_weight_tons
            FROM vehicle_profiles WHERE code = :code;
            """
        ),
        {"code": code},
    )
    row = res.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Perfil vehicular desconocido: {code}")
    return VehicleProfileOut(**dict(row._mapping))


def _build_vehicle(
    profile: VehicleProfileOut, cargo_mass_kg: float, ac_enabled: bool
):
    is_electric = profile.fuel_type == "electric"
    return ecoruta_core.VehicleParams(
        is_electric,
        profile.empty_mass_kg + cargo_mass_kg,
        profile.frontal_area_m2,
        profile.drag_coeff_cd,
        profile.rolling_coeff_crr,
        profile.drivetrain_efficiency,
        0.62 if is_electric else 0.0,
        profile.idle_power_watts,
        1500.0 if ac_enabled else 200.0,
        _ENERGY_DENSITY_J_PER_UNIT.get(profile.fuel_type, 32.1e6),
        1.0,
    )


async def _enrich(db: AsyncSession, selection: dict) -> dict:
    selection["context_notices"] = await SESNSPTerritorialContextService.audit_route_geometry_context(
        db, selection.get("coordinates", [])
    )
    return selection


async def _evaluate_real_front(
    db: AsyncSession,
    req: RouteRequest,
    profile: VehicleProfileOut,
    vehicle,
) -> tuple[list, list[RealRoute]]:
    routes = await RealRoutingService().fetch_routes(
        req.origin_lat, req.origin_lon, req.dest_lat, req.dest_lon
    )
    if not routes:
        raise HTTPException(
            status_code=502,
            detail="No fue posible obtener una ruta real (OSRM/Valhalla no disponibles).",
        )

    unit_price, _price_source = await FuelPriceService.get_unit_price(
        db, profile.fuel_type, req.origin_lat, req.origin_lon
    )
    multiplier = congestion_factor(req.departure_hour, req.day_type, req.use_robust_p90)
    economy = RouteEconomyService(settings.air_density_default)
    solutions = [
        economy.evaluate(r, vehicle, unit_price, multiplier, profile.num_axles) for r in routes
    ]
    return solutions, routes


@router.post("/routes/optimize", response_model=OptimizeResponse)
async def optimize_ecoruta(
    req: RouteRequest, db: AsyncSession = Depends(get_db)
) -> OptimizeResponse:
    cache_payload = {
        "o": [req.origin_lat, req.origin_lon],
        "d": [req.dest_lat, req.dest_lon],
        "h": req.departure_hour,
        "dt": req.day_type,
        "v": req.vehicle_code,
        "cargo": req.cargo_mass_kg,
        "ac": req.ac_enabled,
        "lambda": req.willingness_to_pay_mxn_per_min,
        "p90": req.use_robust_p90,
    }
    key = _cache_key(cache_payload)
    try:
        cached = await get_redis().get(key)
        if cached:
            return OptimizeResponse.model_validate_json(cached)
    except Exception as exc:  # noqa: BLE001 - la caché es opcional
        logger.warning("Caché Redis no disponible: %s", exc)

    profile = await _load_vehicle_profile(db, req.vehicle_code)
    vehicle = _build_vehicle(profile, req.cargo_mass_kg, req.ac_enabled)

    solutions, real_routes = await _evaluate_real_front(db, req, profile, vehicle)
    front = filter_non_dominated(solutions)
    if not front:
        raise HTTPException(status_code=404, detail="Frontera de Pareto vacía para el corredor.")

    selection = ParetoPreferenceSelector.evaluate_pareto_front(
        front=front,
        willingness_to_pay_mxn_per_min=req.willingness_to_pay_mxn_per_min,
        max_budget_mxn=req.max_budget_mxn,
        max_duration_min=req.max_duration_min,
    )

    for tag in ("recommended_user", "recommended_knee", "cheapest", "fastest"):
        selection[tag] = await _enrich(db, selection[tag])
    selection["pareto_frontier"] = [
        await _enrich(db, route) for route in selection["pareto_frontier"]
    ]

    comparison = _build_comparison(selection["recommended_knee"], real_routes, req)

    mode = "Robusto (P90)" if req.use_robust_p90 else "Esperado (P50)"
    response = OptimizeResponse(
        optimization_result=selection,
        comparison=comparison,
        data_provenance_audit=_audit(mode),
    )

    try:
        await get_redis().set(key, response.model_dump_json(), ex=settings.cache_ttl_seconds)
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo escribir en caché Redis: %s", exc)

    return response


def _build_comparison(
    ecoruta_route: dict, real_routes: list[RealRoute], req: RouteRequest
) -> ComparisonOut:
    osrm = [r for r in real_routes if r.source == "osrm"]
    valhalla = [r for r in real_routes if r.source == "valhalla"]
    osrm_best = min(osrm, key=lambda r: r.duration_s) if osrm else None
    valhalla_best = min(valhalla, key=lambda r: r.duration_s) if valhalla else None

    osrm_time = round(osrm_best.duration_s / 60.0, 1) if osrm_best else None
    return ComparisonOut(
        ecoruta_distance_km=float(ecoruta_route.get("distance_km", 0.0)),
        ecoruta_time_min=float(ecoruta_route.get("duration_minutes", 0.0)),
        ecoruta_cost_mxn=float(ecoruta_route.get("total_cost_mxn", 0.0)),
        osrm_distance_km=round(osrm_best.distance_m / 1000.0, 1) if osrm_best else None,
        osrm_time_min=osrm_time,
        valhalla_time_min=round(valhalla_best.duration_s / 60.0, 1) if valhalla_best else None,
        savings_cost_vs_osrm_mxn=None,
        savings_time_vs_osrm_min=(
            round(osrm_time - float(ecoruta_route.get("duration_minutes", 0.0)), 1)
            if osrm_time is not None
            else None
        ),
        google_maps_url=_google_maps_url(
            req.origin_lat, req.origin_lon, req.dest_lat, req.dest_lon
        ),
        notes=(
            "OSRM/Valhalla estiman la geometría y la duración base (red vial real). "
            "EcoRuta añade el costo físico de combustible, el peaje estimado y el ajuste "
            "temporal por congestión según la hora de salida."
        ),
    )


async def _solve_pair(
    db: AsyncSession,
    a: tuple[float, float],
    b: tuple[float, float],
    profile: VehicleProfileOut,
    vehicle,
    req: MultistopRequest,
) -> tuple[float, float, RealRoute | None]:
    routes = await RealRoutingService().fetch_routes(a[0], a[1], b[0], b[1])
    if not routes:
        raise HTTPException(status_code=502, detail="Tramo sin ruta real disponible.")
    best = min(routes, key=lambda r: r.duration_s)

    unit_price, _ = await FuelPriceService.get_unit_price(db, profile.fuel_type, a[0], a[1])
    multiplier = congestion_factor(req.departure_hour, req.day_type, req.use_robust_p90)
    economy = RouteEconomyService(settings.air_density_default)
    sol = economy.evaluate(best, vehicle, unit_price, multiplier, profile.num_axles)
    return sol.total_cost_mxn, sol.total_time_s / 60.0, best


@router.post("/routes/optimize-multistop", response_model=MultistopResponse)
async def optimize_multistop(
    req: MultistopRequest, db: AsyncSession = Depends(get_db)
) -> MultistopResponse:
    profile = await _load_vehicle_profile(db, req.vehicle_code)
    vehicle = _build_vehicle(profile, req.cargo_mass_kg, ac_enabled=True)

    nodes = [req.depot, *req.stops]
    n = len(nodes)
    cost_matrix = [[0.0] * n for _ in range(n)]
    time_matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            cost, minutes, _ = await _solve_pair(
                db, (nodes[i].lat, nodes[i].lon), (nodes[j].lat, nodes[j].lon), profile, vehicle, req
            )
            cost_matrix[i][j] = cost
            time_matrix[i][j] = int(round(minutes))

    windows = [(w.window_start_min, w.window_end_min) for w in nodes]
    result = MultiStopVRPOptimizer.solve_sequence(
        cost_matrix_mxn=cost_matrix,
        time_matrix_min=time_matrix,
        time_windows_min=windows,
        willingness_to_pay_mxn_per_min=req.willingness_to_pay_mxn_per_min,
        depot_index=0,
    )

    mode = "Robusto (P90)" if req.use_robust_p90 else "Esperado (P50)"
    return MultistopResponse(multistop_result=result, data_provenance_audit=_audit(mode))


@router.get("/weather", response_model=WeatherOut)
async def get_current_weather(lat: float, lon: float) -> WeatherOut:
    """Clima actual (temperatura, lluvia, viento) para un punto, vía Open-Meteo/SMN."""
    connector = WeatherAndFloodHazardConnector()
    try:
        data = await connector.fetch_corridor_weather(lat, lon)
        status = "ok"
    except Exception as exc:  # noqa: BLE001 - degradación explícita y auditada
        logger.warning("Clima no disponible (%s); usando estimación marcada.", exc)
        data = {
            "temperature_c": 22.0,
            "precipitation_mmh": 0.0,
            "wind_speed_kmh": 10.0,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "source": "fallback_estimate",
        }
        status = "fallback_estimate"

    precip = float(data["precipitation_mmh"])
    wind = float(data["wind_speed_kmh"])
    temp = float(data["temperature_c"])
    if precip >= 7.5:
        condition = "Lluvia intensa"
    elif precip >= 2.5:
        condition = "Lluvia moderada"
    elif precip > 0.0:
        condition = "Lluvia ligera"
    elif wind >= 40.0:
        condition = "Ventoso"
    elif temp >= 32.0:
        condition = "Caluroso"
    else:
        condition = "Despejado / nublado"

    return WeatherOut(
        latitude=lat,
        longitude=lon,
        condition=condition,
        status=status,
        **data,
    )


@router.get("/vehicles/profiles", response_model=list[VehicleProfileOut])
async def list_vehicle_profiles(db: AsyncSession = Depends(get_db)) -> list[VehicleProfileOut]:
    res = await db.execute(
        text(
            """
            SELECT code, name, fuel_type, empty_mass_kg, frontal_area_m2, drag_coeff_cd,
                   rolling_coeff_crr, drivetrain_efficiency, idle_power_watts, nominal_kml,
                   num_axles, height_m, max_weight_tons
            FROM vehicle_profiles ORDER BY id;
            """
        )
    )
    return [VehicleProfileOut(**dict(row._mapping)) for row in res.fetchall()]


@router.post("/admin/sync-data")
async def sync_data(db: AsyncSession = Depends(get_db)) -> dict:
    """Dispara la sincronización de conectores oficiales (CNE y cierres CONAGUA)."""
    cne = CNEFuelConnector(settings.cne_endpoint_url)
    cne_result = await cne.sync_stations_and_assign_edges(db)
    closures = await WeatherAndFloodHazardConnector().apply_confirmed_flood_closures(db)
    return {
        "cne_sync": cne_result,
        "confirmed_closures_applied": closures,
        "data_provenance_audit": _audit("no_aplica").model_dump(),
    }
