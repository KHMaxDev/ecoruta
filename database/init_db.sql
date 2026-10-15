-- =============================================================================
-- EcoRuta — Esquema DDL geoespacial y topológico
-- PostgreSQL 16 + PostGIS 3.4 + pgRouting 3.6
-- Ejecutado automáticamente por el contenedor `postgis` en el primer arranque.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 0. Extensiones requeridas
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgrouting;
CREATE EXTENSION IF NOT EXISTS hstore;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ---------------------------------------------------------------------------
-- 1. Perfiles de vehículos (combustión interna y eléctricos)
--    Parámetros físicos del modelo longitudinal traccional.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicle_profiles (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_electric BOOLEAN NOT NULL DEFAULT FALSE,
    fuel_type VARCHAR(20) NOT NULL CHECK (fuel_type IN ('regular', 'premium', 'diesel', 'electric')),
    empty_mass_kg DOUBLE PRECISION NOT NULL,
    frontal_area_m2 DOUBLE PRECISION NOT NULL,
    drag_coeff_cd DOUBLE PRECISION NOT NULL,
    rolling_coeff_crr DOUBLE PRECISION NOT NULL DEFAULT 0.012,
    drivetrain_efficiency DOUBLE PRECISION NOT NULL DEFAULT 0.28,
    regen_efficiency DOUBLE PRECISION NOT NULL DEFAULT 0.62,
    idle_power_watts DOUBLE PRECISION NOT NULL DEFAULT 1200.0,
    aux_power_watts DOUBLE PRECISION NOT NULL DEFAULT 1500.0,
    -- Densidad energética volumétrica: gasolina ~32.1e6 J/L, diésel ~35.5e6 J/L, EV ~3.6e6 J/kWh
    energy_density_j_per_unit DOUBLE PRECISION NOT NULL,
    nominal_kml DOUBLE PRECISION,
    calibration_factor DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    num_axles INT NOT NULL DEFAULT 2,
    height_m DOUBLE PRECISION NOT NULL DEFAULT 1.6,
    max_weight_tons DOUBLE PRECISION NOT NULL DEFAULT 3.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 2. Nodos de la red vial
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS road_nodes (
    id BIGINT PRIMARY KEY,
    elevation_m DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    is_toll_booth BOOLEAN NOT NULL DEFAULT FALSE,
    geom GEOMETRY(Point, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_road_nodes_geom ON road_nodes USING GIST (geom);

-- ---------------------------------------------------------------------------
-- 3. Aristas dirigidas (Grafo vial unificado INEGI RNC + OSM)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS road_edges (
    id BIGSERIAL PRIMARY KEY,
    source BIGINT NOT NULL REFERENCES road_nodes(id),
    target BIGINT NOT NULL REFERENCES road_nodes(id),
    rnc_id VARCHAR(64),
    road_name VARCHAR(255),
    road_class VARCHAR(50) NOT NULL DEFAULT 'carretera',
    length_m DOUBLE PRECISION NOT NULL CHECK (length_m > 0),
    slope_rad DOUBLE PRECISION NOT NULL DEFAULT 0.0,   -- Pendiente media en radianes, acotada [-0.25, 0.25]
    free_flow_speed_kmh DOUBLE PRECISION NOT NULL DEFAULT 60.0,
    surface_factor DOUBLE PRECISION NOT NULL DEFAULT 1.0, -- 1.0 asfalto, 1.4 empedrado, 2.0 terracería

    -- Tarifas de peaje por categoría (Datos INEGI RNC)
    toll_cost_autos_mxn DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    toll_cost_bus_2axles_mxn DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    toll_cost_truck_5axles_mxn DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    toll_source_status VARCHAR(20) NOT NULL DEFAULT 'confirmado'
        CHECK (toll_source_status IN ('confirmado', 'estimado', 'desconocido')),

    -- Restricciones físicas duras
    max_height_m DOUBLE PRECISION NOT NULL DEFAULT 99.0,
    max_weight_tons DOUBLE PRECISION NOT NULL DEFAULT 999.0,
    is_closed_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    closure_reason TEXT,

    -- Precios de energía asignados espacialmente por la CNE
    assigned_regular_price_mxn DOUBLE PRECISION NOT NULL DEFAULT 23.80,
    assigned_premium_price_mxn DOUBLE PRECISION NOT NULL DEFAULT 25.40,
    assigned_diesel_price_mxn  DOUBLE PRECISION NOT NULL DEFAULT 25.10,
    assigned_electric_price_mxn DOUBLE PRECISION NOT NULL DEFAULT 6.20,  -- MXN/kWh
    fuel_price_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    geom GEOMETRY(LineString, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_road_edges_geom ON road_edges USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_road_edges_source_target ON road_edges (source, target);
CREATE INDEX IF NOT EXISTS idx_road_edges_target ON road_edges (target);

-- ---------------------------------------------------------------------------
-- 4. Perfiles de velocidad horaria (24 h) FIFO-regularizados
--    speed_p50 -> tiempo esperado (beta = 0.50)
--    speed_p10 -> tiempo robusto (beta = 0.90)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS edge_hourly_speeds (
    edge_id BIGINT NOT NULL REFERENCES road_edges(id) ON DELETE CASCADE,
    day_type VARCHAR(15) NOT NULL CHECK (day_type IN ('weekday', 'weekend')),
    hour_of_day SMALLINT NOT NULL CHECK (hour_of_day BETWEEN 0 AND 23),
    speed_p50_kmh DOUBLE PRECISION NOT NULL,
    speed_p10_kmh DOUBLE PRECISION NOT NULL,
    congestion_stop_index DOUBLE PRECISION NOT NULL DEFAULT 0.05, -- Aceleración equivalente media m/s^2
    PRIMARY KEY (edge_id, day_type, hour_of_day)
);

-- ---------------------------------------------------------------------------
-- 5. Estaciones de servicio (CNE)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fuel_stations_cne (
    permiso_cre VARCHAR(64) PRIMARY KEY,
    station_name VARCHAR(255),
    regular_price_mxn DOUBLE PRECISION,
    premium_price_mxn DOUBLE PRECISION,
    diesel_price_mxn DOUBLE PRECISION,
    reported_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    geom GEOMETRY(Point, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fuel_stations_geom ON fuel_stations_cne USING GIST (geom);

-- ---------------------------------------------------------------------------
-- 6. Capas contextuales de peligro hídrico (CONAGUA) y seguridad (SESNSP)
--    `spatial_resolution` es OBLIGATORIO para transparentar el alcance espacial.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hazard_zones (
    id SERIAL PRIMARY KEY,
    hazard_type VARCHAR(30) NOT NULL
        CHECK (hazard_type IN ('inundacion_historica', 'cierre_vial_activo', 'contexto_municipal_sesnsp', 'clima_severo')),
    region_code VARCHAR(50),
    description TEXT NOT NULL,
    severity_level VARCHAR(20) NOT NULL
        CHECK (severity_level IN ('informativo', 'precaucion', 'cierre_duro')),
    source_name VARCHAR(100) NOT NULL,
    source_timestamp TIMESTAMPTZ NOT NULL,
    spatial_resolution VARCHAR(50) NOT NULL
        CHECK (spatial_resolution IN ('tramo_vial', 'poligono_cuenca', 'agregado_municipal')),
    confidence_level VARCHAR(20) NOT NULL DEFAULT 'media'
        CHECK (confidence_level IN ('alta', 'media', 'baja', 'fallback_estimate')),
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hazard_zones_geom ON hazard_zones USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_hazard_zones_type ON hazard_zones (hazard_type, severity_level);

-- ---------------------------------------------------------------------------
-- 7. Auditoría de ingesta de datos (frescura y procedencia)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_ingest_audit (
    id BIGSERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    dataset VARCHAR(100) NOT NULL,
    spatial_resolution VARCHAR(50),
    records_affected BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'ok'
        CHECK (status IN ('ok', 'partial', 'failed', 'fallback_estimate')),
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT
);

-- ---------------------------------------------------------------------------
-- 8. Función de conveniencia: consulta del estado de frescura de datos
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ecoruta_fuel_price_age_hours()
RETURNS TABLE (edge_id BIGINT, age_hours DOUBLE PRECISION) AS $$
BEGIN
    RETURN QUERY
    SELECT e.id, EXTRACT(EPOCH FROM (NOW() - e.fuel_price_updated_at)) / 3600.0
    FROM road_edges e;
END;
$$ LANGUAGE plpgsql STABLE;

-- ---------------------------------------------------------------------------
-- 9. Vista de aristas factibles (excluye cierres confirmados)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_road_edges_open AS
SELECT *
FROM road_edges
WHERE is_closed_confirmed = FALSE;
