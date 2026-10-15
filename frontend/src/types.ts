export interface RouteRequest {
  origin_lat: number;
  origin_lon: number;
  dest_lat: number;
  dest_lon: number;
  departure_hour: number;
  day_type: "weekday" | "weekend";
  vehicle_code: string;
  cargo_mass_kg: number;
  ac_enabled: boolean;
  willingness_to_pay_mxn_per_min: number;
  max_budget_mxn?: number | null;
  max_duration_min?: number | null;
  use_robust_p90: boolean;
}

export interface ContextNotice {
  type: string;
  region_code: string;
  message: string;
  severity: string;
  source: string;
  source_timestamp: string | null;
  spatial_resolution: string;
  epistemological_disclaimer: string;
}

export interface RoutePoint {
  recommendation_tag: string;
  total_cost_mxn: number;
  fuel_cost_mxn: number;
  toll_cost_mxn: number;
  total_fuel_liters: number;
  duration_minutes: number;
  savings_vs_fastest_mxn: number;
  extra_time_vs_fastest_min: number | null;
  edge_ids: number[];
  node_ids: number[];
  coordinates: [number, number][];
  context_notices: ContextNotice[];
  distance_km: number;
  baseline_duration_minutes: number;
  network_source: string;
  route_profile: string;
  toll_is_estimate: boolean;
  is_real_network: boolean;
}

export interface Comparison {
  ecoruta_distance_km: number;
  ecoruta_time_min: number;
  ecoruta_cost_mxn: number;
  osrm_distance_km: number | null;
  osrm_time_min: number | null;
  valhalla_time_min: number | null;
  savings_cost_vs_osrm_mxn: number | null;
  savings_time_vs_osrm_min: number | null;
  google_maps_url: string;
  notes: string;
}

export interface OptimizationResult {
  status: string;
  pareto_count: number;
  recommended_user: RoutePoint;
  recommended_knee: RoutePoint;
  cheapest: RoutePoint;
  fastest: RoutePoint;
  pareto_frontier: RoutePoint[];
}

export interface DataProvenanceAudit {
  road_network_source: string;
  fuel_price_source: string;
  toll_source: string;
  safety_context_notice: string;
  uncertainty_mode: string;
  computed_at_utc: string;
}

export interface OptimizeResponse {
  optimization_result: OptimizationResult;
  comparison: Comparison | null;
  data_provenance_audit: DataProvenanceAudit;
}

export interface WeatherOut {
  latitude: number;
  longitude: number;
  temperature_c: number;
  precipitation_mmh: number;
  wind_speed_kmh: number;
  condition: string;
  observed_at: string;
  source: string;
  status: string;
}

export interface VehicleProfile {
  code: string;
  name: string;
  fuel_type: string;
  empty_mass_kg: number;
  frontal_area_m2: number;
  drag_coeff_cd: number;
  rolling_coeff_crr: number;
  drivetrain_efficiency: number;
  idle_power_watts: number;
  nominal_kml: number | null;
  num_axles: number;
  height_m: number;
  max_weight_tons: number;
}
