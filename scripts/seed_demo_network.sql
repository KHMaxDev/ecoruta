-- =============================================================================
-- EcoRuta — Red sintética de demostración (malla sobre la región piloto)
-- =============================================================================
-- Genera una malla navegable de nodos/aristas sobre el bbox piloto
-- (CDMX–Puebla–Toluca–Querétaro) para que CUALQUIER par de puntos dentro de la
-- región tenga al menos una ruta factible. NO son datos reales de la RNC:
-- es una red de demostración auto-consistente para validar el motor.
--
--   lat: 18.8 .. 20.9 (paso 0.3, 8 filas)   lon: -100.7 .. -97.9 (paso 0.3, 10 col)
--
-- Uso: psql -U ecoruta_user -d ecoruta_db -f seed_demo_network.sql
-- =============================================================================

DELETE FROM edge_hourly_speeds;
DELETE FROM hazard_zones;
DELETE FROM road_edges;
DELETE FROM road_nodes;

-- --- Nodos (malla lat/lon) ---------------------------------------------------
-- id = li*100 + lj + 1
INSERT INTO road_nodes (id, elevation_m, geom)
SELECT
  (li * 100 + lj + 1) AS id,
  CASE WHEN li > 4 THEN 2200.0 ELSE 1800.0 END,
  ST_SetSRID(ST_MakePoint(-100.7 + lj * 0.3, 18.8 + li * 0.3), 4326)
FROM generate_series(0, 7) AS li
CROSS JOIN generate_series(0, 9) AS lj;

-- --- Aristas bidireccionales -------------------------------------------------
-- Clase alterna por celda: "autopista" (con peaje y más rápida) vs "carretera
-- libre" (sin peaje y más lenta), lo que produce un frente de Pareto no trivial.
WITH n AS (
  SELECT id, ((id - 1) / 100) AS li, ((id - 1) % 100) AS lj, geom FROM road_nodes
),
pairs AS (
  SELECT a.id AS s, b.id AS t, ((a.li + a.lj) % 2) AS cls, a.geom AS ga, b.geom AS gb
  FROM n a JOIN n b ON a.li = b.li AND b.lj = a.lj + 1
  UNION ALL
  SELECT a.id AS s, b.id AS t, ((a.li + a.lj) % 2) AS cls, a.geom AS ga, b.geom AS gb
  FROM n a JOIN n b ON a.lj = b.lj AND b.li = a.li + 1
),
dir AS (
  SELECT s, t, cls, ST_MakeLine(ga, gb) AS geom FROM pairs
  UNION ALL
  SELECT t, s, cls, ST_MakeLine(gb, ga) AS geom FROM pairs
)
INSERT INTO road_edges
  (source, target, road_name, road_class, length_m, slope_rad,
   free_flow_speed_kmh, toll_cost_autos_mxn, toll_cost_truck_5axles_mxn,
   max_height_m, max_weight_tons, geom)
SELECT
  s, t,
  CASE WHEN cls = 0 THEN 'Autopista (demo)' ELSE 'Carretera libre (demo)' END,
  CASE WHEN cls = 0 THEN 'autopista' ELSE 'carretera' END,
  ST_Distance(ST_StartPoint(geom)::geography, ST_EndPoint(geom)::geography),
  0.0,
  CASE WHEN cls = 0 THEN 110.0 ELSE 75.0 END,
  CASE WHEN cls = 0 THEN 60.0 ELSE 0.0 END,
  CASE WHEN cls = 0 THEN 210.0 ELSE 0.0 END,
  5.5, 66.0,
  geom
FROM dir;

SELECT setval('road_edges_id_seq', (SELECT MAX(id) FROM road_edges));

-- --- Perfiles horarios -------------------------------------------------------
INSERT INTO edge_hourly_speeds
  (edge_id, day_type, hour_of_day, speed_p50_kmh, speed_p10_kmh, congestion_stop_index)
SELECT
  e.id, dt.day_type, h.hour,
  GREATEST(e.free_flow_speed_kmh * CASE WHEN h.hour BETWEEN 7 AND 9 OR h.hour BETWEEN 17 AND 19
                                        THEN 0.60 ELSE 1.00 END, 15.0),
  GREATEST(e.free_flow_speed_kmh * CASE WHEN h.hour BETWEEN 7 AND 9 OR h.hour BETWEEN 17 AND 19
                                        THEN 0.39 ELSE 0.85 END, 10.0),
  CASE WHEN h.hour BETWEEN 7 AND 9 OR h.hour BETWEEN 17 AND 19 THEN 0.30 ELSE 0.05 END
FROM road_edges e
CROSS JOIN (VALUES ('weekday'), ('weekend')) AS dt(day_type)
CROSS JOIN generate_series(0, 23) AS h(hour);

-- --- Zonas contextuales ------------------------------------------------------
INSERT INTO hazard_zones
  (hazard_type, region_code, description, severity_level, source_name,
   source_timestamp, spatial_resolution, confidence_level, geom)
VALUES
  ('contexto_municipal_sesnsp', '21114', 'Incidencia delictiva municipal (Puebla) - solo contexto',
   'informativo', 'SESNSP', NOW(), 'agregado_municipal', 'media',
   ST_Multi(ST_GeomFromText('POLYGON((-98.50 19.00,-98.00 19.00,-98.00 19.40,-98.50 19.40,-98.50 19.00))', 4326))),
  ('inundacion_historica', 'RH26', 'Suelo susceptible a inundación (cuenca Balsas) - precaución',
   'precaucion', 'CONAGUA Atlas Nacional de Riesgo', NOW(), 'poligono_cuenca', 'media',
   ST_Multi(ST_GeomFromText('POLYGON((-99.35 19.10,-98.95 19.10,-98.95 19.45,-99.35 19.45,-99.35 19.10))', 4326)));
