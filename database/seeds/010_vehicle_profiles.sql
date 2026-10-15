-- =============================================================================
-- EcoRuta — Semillas: perfiles de vehículos de referencia
-- Cargado automáticamente tras init_db.sql
-- =============================================================================
-- Densidades energéticas volumétricas:
--   Gasolina: ~32.1e6 J/L   Diésel: ~35.5e6 J/L   EV: 3.6e6 J/kWh
-- =============================================================================

INSERT INTO vehicle_profiles (
    code, name, is_electric, fuel_type, empty_mass_kg, frontal_area_m2,
    drag_coeff_cd, rolling_coeff_crr, drivetrain_efficiency, regen_efficiency,
    idle_power_watts, aux_power_watts, energy_density_j_per_unit,
    nominal_kml, calibration_factor, num_axles, height_m, max_weight_tons
) VALUES
    ('sedan_compacto', 'Sedán Compacto (1.6L)', FALSE, 'regular',
     1250.0, 2.15, 0.30, 0.012, 0.28, 0.62,
     1200.0, 1500.0, 32.1e6, 15.5, 1.0, 2, 1.48, 3.5),

    ('suv_mediana', 'SUV Mediana (2.5L)', FALSE, 'premium',
     1750.0, 2.65, 0.36, 0.013, 0.29, 0.62,
     1400.0, 1600.0, 32.1e6, 11.2, 1.0, 2, 1.72, 3.5),

    ('camion_ligero_3_5t', 'Camión de Reparto 3.5T Diésel', FALSE, 'diesel',
     2800.0, 4.80, 0.55, 0.010, 0.38, 0.00,
     2200.0, 1200.0, 35.5e6, 7.5, 1.0, 2, 2.85, 3.5),

    ('tractocamion_t3s2', 'Tractocamión T3-S2 (5 Ejes)', FALSE, 'diesel',
     14500.0, 8.50, 0.68, 0.008, 0.42, 0.00,
     6000.0, 2000.0, 35.5e6, 2.8, 1.0, 5, 4.15, 48.0),

    ('ev_compacto', 'Vehículo Eléctrico Compacto (60 kWh)', TRUE, 'electric',
     1600.0, 2.30, 0.29, 0.011, 0.90, 0.62,
     300.0, 900.0, 3.6e6, NULL, 1.0, 2, 1.55, 3.0)
ON CONFLICT (code) DO NOTHING;
