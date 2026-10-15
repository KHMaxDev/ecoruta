"""Contratos Pydantic v2 para los endpoints de optimización de rutas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    """Petición bi-objetivo origen-destino."""

    origin_lat: float = Field(..., ge=-90.0, le=90.0, examples=[19.4326])
    origin_lon: float = Field(..., ge=-180.0, le=180.0, examples=[-99.1332])
    dest_lat: float = Field(..., ge=-90.0, le=90.0, examples=[19.0414])
    dest_lon: float = Field(..., ge=-180.0, le=180.0, examples=[-98.2063])
    departure_hour: int = Field(8, ge=0, le=23)
    day_type: str = Field("weekday", pattern="^(weekday|weekend)$")
    vehicle_code: str = Field("sedan_compacto")
    cargo_mass_kg: float = Field(150.0, ge=0.0)
    ac_enabled: bool = Field(True)
    willingness_to_pay_mxn_per_min: float = Field(2.5, ge=0.0)
    max_budget_mxn: float | None = Field(default=None, gt=0.0)
    max_duration_min: float | None = Field(default=None, gt=0.0)
    use_robust_p90: bool = Field(
        False, description="Si es True, evalúa tiempos en el percentil P90 de congestión."
    )


class WaypointIn(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    window_start_min: int = Field(0, ge=0, le=1440)
    window_end_min: int = Field(1440, ge=0, le=1440)


class MultistopRequest(BaseModel):
    """Petición de múltiples paradas con ventanas de tiempo (GTDVRPTW)."""

    depot: WaypointIn
    stops: list[WaypointIn] = Field(..., min_length=1, max_length=10)
    departure_hour: int = Field(8, ge=0, le=23)
    day_type: str = Field("weekday", pattern="^(weekday|weekend)$")
    vehicle_code: str = Field("sedan_compacto")
    cargo_mass_kg: float = Field(150.0, ge=0.0)
    willingness_to_pay_mxn_per_min: float = Field(2.0, ge=0.0)
    use_robust_p90: bool = False


class DataProvenanceAudit(BaseModel):
    """Bloque de auditoría obligatorio en toda respuesta (regla arquitectónica 6)."""

    road_network_source: str
    fuel_price_source: str
    toll_source: str
    safety_context_notice: str
    uncertainty_mode: str
    computed_at_utc: str


class RoutePointOut(BaseModel):
    recommendation_tag: str
    total_cost_mxn: float
    fuel_cost_mxn: float
    toll_cost_mxn: float
    total_fuel_liters: float
    duration_minutes: float
    savings_vs_fastest_mxn: float
    extra_time_vs_fastest_min: float | None = None
    edge_ids: list[int]
    node_ids: list[int]
    coordinates: list[list[float]] = Field(default_factory=list)
    context_notices: list[dict] = Field(default_factory=list)
    distance_km: float = 0.0
    baseline_duration_minutes: float = 0.0
    network_source: str = "real"
    route_profile: str = "desconocido"
    toll_is_estimate: bool = True
    is_real_network: bool = True


class ComparisonOut(BaseModel):
    """Comparativa de EcoRuta frente a otros motores y Google Maps."""

    ecoruta_distance_km: float
    ecoruta_time_min: float
    ecoruta_cost_mxn: float
    osrm_distance_km: float | None = None
    osrm_time_min: float | None = None
    valhalla_time_min: float | None = None
    savings_cost_vs_osrm_mxn: float | None = None
    savings_time_vs_osrm_min: float | None = None
    google_maps_url: str
    notes: str


class OptimizationResult(BaseModel):
    status: str
    pareto_count: int
    recommended_user: RoutePointOut
    recommended_knee: RoutePointOut
    cheapest: RoutePointOut
    fastest: RoutePointOut
    pareto_frontier: list[RoutePointOut]


class OptimizeResponse(BaseModel):
    optimization_result: OptimizationResult
    comparison: ComparisonOut | None = None
    data_provenance_audit: DataProvenanceAudit


class MultistopResponse(BaseModel):
    multistop_result: dict
    data_provenance_audit: DataProvenanceAudit


class WeatherOut(BaseModel):
    """Clima observado en tiempo real para un punto (Open-Meteo / SMN)."""

    latitude: float
    longitude: float
    temperature_c: float
    precipitation_mmh: float
    wind_speed_kmh: float
    condition: str
    observed_at: str
    source: str
    status: str = "ok"


class VehicleProfileOut(BaseModel):
    code: str
    name: str
    fuel_type: str
    empty_mass_kg: float
    frontal_area_m2: float
    drag_coeff_cd: float
    rolling_coeff_crr: float
    drivetrain_efficiency: float
    idle_power_watts: float
    nominal_kml: float | None = None
    num_axles: int
    height_m: float
    max_weight_tons: float
