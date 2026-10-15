/// Parámetros físicos del vehículo (combustión interna o eléctrico).
///
/// Alimenta el modelo longitudinal traccional de consumo energético por arista.
/// Tipo puro de Rust; la cara Python vive en `python.rs` (`PyVehicleParams`).
#[derive(Clone, Debug)]
pub struct VehicleParams {
    pub is_electric: bool,
    pub total_mass_kg: f64,
    pub frontal_area_m2: f64,
    pub drag_coeff_cd: f64,
    pub rolling_coeff_crr: f64,
    pub drivetrain_eff: f64,
    pub regen_efficiency: f64,
    pub idle_power_watts: f64,
    pub aux_power_watts: f64,
    pub energy_density_j_per_unit: f64,
    pub calibration_factor: f64,
}

impl VehicleParams {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        is_electric: bool,
        total_mass_kg: f64,
        frontal_area_m2: f64,
        drag_coeff_cd: f64,
        rolling_coeff_crr: f64,
        drivetrain_eff: f64,
        regen_efficiency: f64,
        idle_power_watts: f64,
        aux_power_watts: f64,
        energy_density_j_per_unit: f64,
        calibration_factor: f64,
    ) -> Self {
        Self {
            is_electric,
            total_mass_kg,
            frontal_area_m2,
            drag_coeff_cd,
            rolling_coeff_crr,
            drivetrain_eff,
            regen_efficiency,
            idle_power_watts,
            aux_power_watts,
            energy_density_j_per_unit,
            calibration_factor,
        }
    }

    /// Consumo mínimo físico por metro a velocidad óptima (70 km/h = 19.44 m/s) en plano.
    /// Base de la cota inferior admisible de la heurística A*.
    pub fn min_energy_units_per_meter(&self, air_density: f64) -> f64 {
        let v_opt = 19.44;
        let g = 9.81;
        let f_aero = 0.5 * air_density * self.drag_coeff_cd * self.frontal_area_m2 * v_opt * v_opt;
        let f_roll = self.total_mass_kg * g * self.rolling_coeff_crr;
        let p_trac = v_opt * (f_aero + f_roll);
        let p_total = (p_trac / self.drivetrain_eff) + self.idle_power_watts + self.aux_power_watts;
        let j_per_meter = p_total / v_opt;
        (j_per_meter / self.energy_density_j_per_unit) * self.calibration_factor
    }
}

/// Calcula las unidades de energía consumidas en una arista.
///
/// Devuelve litros de combustible para vehículos ICE o kWh eléctricos para EVs.
/// Implementa la ecuación longitudinal unificada: aerodinámica + rodadura
/// (ajustada por lluvia) + gravedad por pendiente + inercia por congestión.
#[inline]
pub fn compute_edge_energy_units(
    length_m: f64,
    slope_rad: f64,
    travel_time_s: f64,
    congestion_accel_ms2: f64,
    rain_intensity_mmh: f64,
    veh: &VehicleParams,
    air_density: f64,
) -> f64 {
    let v_ms = (length_m / travel_time_s.max(0.1)).clamp(0.5, 45.0);
    let g = 9.81;

    // Ajuste dinámico del coeficiente de rodadura por película de agua
    let crr_effective = veh.rolling_coeff_crr * (1.0 + 0.02 * rain_intensity_mmh.clamp(0.0, 25.0));

    let f_aero = 0.5 * air_density * veh.drag_coeff_cd * veh.frontal_area_m2 * v_ms * v_ms;
    let f_roll = veh.total_mass_kg * g * crr_effective * slope_rad.cos();
    let f_grav = veh.total_mass_kg * g * slope_rad.sin();
    let f_iner = veh.total_mass_kg * congestion_accel_ms2;

    let f_total = f_aero + f_roll + f_grav + f_iner;
    let wheel_power_w = v_ms * f_total;

    let net_power_w = if veh.is_electric {
        if wheel_power_w >= 0.0 {
            (wheel_power_w / veh.drivetrain_eff) + veh.aux_power_watts
        } else {
            // Frenado regenerativo en pendiente negativa
            (wheel_power_w * veh.regen_efficiency) + veh.aux_power_watts
        }
    } else {
        let p_trac = wheel_power_w.max(0.0);
        (p_trac / veh.drivetrain_eff) + veh.idle_power_watts + veh.aux_power_watts
    };

    let total_energy_j = net_power_w * travel_time_s;
    let units = (total_energy_j / veh.energy_density_j_per_unit) * veh.calibration_factor;

    if veh.is_electric {
        units
    } else {
        units.max(0.0001)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_positive_slope_consumes_more_than_flat() {
        let veh = VehicleParams::new(false, 1350.0, 2.15, 0.30, 0.012, 0.28, 0.0, 1200.0, 500.0, 32.1e6, 1.0);
        let flat = compute_edge_energy_units(1000.0, 0.0, 60.0, 0.05, 0.0, &veh, 1.05);
        let uphill = compute_edge_energy_units(1000.0, 0.05, 60.0, 0.05, 0.0, &veh, 1.05);
        assert!(uphill > flat, "subir pendiente debe consumir más que en plano");
    }

    #[test]
    fn test_rain_increases_consumption() {
        let veh = VehicleParams::new(false, 1350.0, 2.15, 0.30, 0.012, 0.28, 0.0, 1200.0, 500.0, 32.1e6, 1.0);
        let dry = compute_edge_energy_units(1000.0, 0.0, 60.0, 0.05, 0.0, &veh, 1.05);
        let wet = compute_edge_energy_units(1000.0, 0.0, 60.0, 0.05, 25.0, &veh, 1.05);
        assert!(wet > dry, "la lluvia debe incrementar la resistencia a la rodadura");
    }
}
