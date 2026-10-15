//! Enlaces PyO3 (feature `python`). Todo el cómputo vive en módulos Rust puros
//! (`physics`, `fifo`, `td_mols`); aquí se exponen al intérprete CPython bajo el
//! nombre `ecoruta_core` mediante clases envoltorio con nombre público idéntico.
use pyo3::prelude::*;

use crate::fifo::{interpolate_fifo_travel_time, regularize_hourly_times_fifo};
use crate::physics::{compute_edge_energy_units, VehicleParams};
use crate::td_mols::{solve_core, EdgeData, ParetoRoute};

/// Envoltorio Python de [`VehicleParams`].
#[pyclass(name = "VehicleParams")]
#[derive(Clone)]
pub struct PyVehicleParams {
    #[pyo3(get, set)]
    pub is_electric: bool,
    #[pyo3(get, set)]
    pub total_mass_kg: f64,
    #[pyo3(get, set)]
    pub frontal_area_m2: f64,
    #[pyo3(get, set)]
    pub drag_coeff_cd: f64,
    #[pyo3(get, set)]
    pub rolling_coeff_crr: f64,
    #[pyo3(get, set)]
    pub drivetrain_eff: f64,
    #[pyo3(get, set)]
    pub regen_efficiency: f64,
    #[pyo3(get, set)]
    pub idle_power_watts: f64,
    #[pyo3(get, set)]
    pub aux_power_watts: f64,
    #[pyo3(get, set)]
    pub energy_density_j_per_unit: f64,
    #[pyo3(get, set)]
    pub calibration_factor: f64,
}

impl PyVehicleParams {
    fn to_core(&self) -> VehicleParams {
        VehicleParams::new(
            self.is_electric,
            self.total_mass_kg,
            self.frontal_area_m2,
            self.drag_coeff_cd,
            self.rolling_coeff_crr,
            self.drivetrain_eff,
            self.regen_efficiency,
            self.idle_power_watts,
            self.aux_power_watts,
            self.energy_density_j_per_unit,
            self.calibration_factor,
        )
    }
}

#[pymethods]
impl PyVehicleParams {
    #[new]
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

    /// Consumo mínimo por metro a velocidad óptima (cota inferior de A*).
    pub fn min_energy_units_per_meter(&self, air_density: f64) -> f64 {
        self.to_core().min_energy_units_per_meter(air_density)
    }
}

/// Envoltorio Python de [`EdgeData`] (regulariza FIFO al construirse).
#[pyclass(name = "EdgeData")]
#[derive(Clone)]
pub struct PyEdgeData {
    #[pyo3(get, set)]
    pub id: u64,
    #[pyo3(get, set)]
    pub source: u64,
    #[pyo3(get, set)]
    pub target: u64,
    #[pyo3(get, set)]
    pub target_lon: f64,
    #[pyo3(get, set)]
    pub target_lat: f64,
    #[pyo3(get, set)]
    pub length_m: f64,
    #[pyo3(get, set)]
    pub slope_rad: f64,
    #[pyo3(get, set)]
    pub toll_mxn: f64,
    #[pyo3(get, set)]
    pub unit_energy_price_mxn: f64,
    #[pyo3(get, set)]
    pub congestion_accel_ms2: f64,
    #[pyo3(get, set)]
    pub rain_intensity_mmh: f64,
    // Serie horaria regularizada FIFO (uso interno; no expuesta a Python).
    hourly_travel_time_s: [f64; 24],
}

impl PyEdgeData {
    fn to_core(&self) -> EdgeData {
        EdgeData::from_travel_times(
            self.id,
            self.source,
            self.target,
            self.target_lon,
            self.target_lat,
            self.length_m,
            self.slope_rad,
            self.toll_mxn,
            self.unit_energy_price_mxn,
            self.hourly_travel_time_s,
            self.congestion_accel_ms2,
            self.rain_intensity_mmh,
        )
    }
}

#[pymethods]
impl PyEdgeData {
    #[new]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        id: u64,
        source: u64,
        target: u64,
        target_lon: f64,
        target_lat: f64,
        length_m: f64,
        slope_rad: f64,
        toll_mxn: f64,
        unit_energy_price_mxn: f64,
        hourly_speeds_kmh: Vec<f64>,
        congestion_accel_ms2: f64,
        rain_intensity_mmh: f64,
    ) -> Self {
        let hourly_travel_time_s = regularize_hourly_times_fifo(length_m, &hourly_speeds_kmh);
        Self {
            id,
            source,
            target,
            target_lon,
            target_lat,
            length_m,
            slope_rad,
            toll_mxn,
            unit_energy_price_mxn,
            congestion_accel_ms2,
            rain_intensity_mmh,
            hourly_travel_time_s,
        }
    }
}

/// Envoltorio Python de [`ParetoRoute`].
#[pyclass(name = "ParetoRoute")]
#[derive(Clone)]
pub struct PyParetoRoute {
    #[pyo3(get)]
    pub total_cost_mxn: f64,
    #[pyo3(get)]
    pub total_time_s: f64,
    #[pyo3(get)]
    pub total_fuel_liters: f64,
    #[pyo3(get)]
    pub total_toll_mxn: f64,
    #[pyo3(get)]
    pub edge_ids: Vec<u64>,
    #[pyo3(get)]
    pub node_ids: Vec<u64>,
}

impl PyParetoRoute {
    fn from_core(r: ParetoRoute) -> Self {
        Self {
            total_cost_mxn: r.total_cost_mxn,
            total_time_s: r.total_time_s,
            total_fuel_liters: r.total_fuel_liters,
            total_toll_mxn: r.total_toll_mxn,
            edge_ids: r.edge_ids,
            node_ids: r.node_ids,
        }
    }
}

/// Time-Dependent Multi-Objective Label-Setting (TD-MOLS) expuesto a Python.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn solve_td_mols<'py>(
    edges: Vec<Bound<'py, PyEdgeData>>,
    vehicle: Bound<'py, PyVehicleParams>,
    source_node: u64,
    target_node: u64,
    dest_lon: f64,
    dest_lat: f64,
    departure_time_s: f64,
    air_density: f64,
    max_labels_per_node: usize,
    epsilon_rel: f64,
) -> Vec<PyParetoRoute> {
    let core_edges: Vec<EdgeData> = edges.iter().map(|e| e.borrow().to_core()).collect();
    solve_core(
        core_edges,
        vehicle.borrow().to_core(),
        source_node,
        target_node,
        dest_lon,
        dest_lat,
        departure_time_s,
        air_density,
        max_labels_per_node,
        epsilon_rel,
    )
    .into_iter()
    .map(PyParetoRoute::from_core)
    .collect()
}

/// Regulariza 24 velocidades horarias reduciéndolas a 24 tiempos de viaje FIFO.
#[pyfunction]
pub fn regularize_fifo(length_m: f64, hourly_speeds_kmh: Vec<f64>) -> Vec<f64> {
    regularize_hourly_times_fifo(length_m, &hourly_speeds_kmh).to_vec()
}

/// Interpola el tiempo de viaje FIFO en un instante del día (segundos).
#[pyfunction]
pub fn interpolate_fifo(hourly_times_s: Vec<f64>, arrival_time_s: f64) -> f64 {
    let mut buf = [0.0_f64; 24];
    for (i, v) in hourly_times_s.iter().take(24).enumerate() {
        buf[i] = *v;
    }
    interpolate_fifo_travel_time(&buf, arrival_time_s)
}

/// Consumo energético (litros ICE o kWh EV) de una arista.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn compute_energy_units(
    length_m: f64,
    slope_rad: f64,
    travel_time_s: f64,
    congestion_accel_ms2: f64,
    rain_intensity_mmh: f64,
    vehicle: Bound<'_, PyVehicleParams>,
    air_density: f64,
) -> f64 {
    compute_edge_energy_units(
        length_m,
        slope_rad,
        travel_time_s,
        congestion_accel_ms2,
        rain_intensity_mmh,
        &vehicle.borrow().to_core(),
        air_density,
    )
}

#[pymodule]
fn ecoruta_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyVehicleParams>()?;
    m.add_class::<PyEdgeData>()?;
    m.add_class::<PyParetoRoute>()?;
    m.add_function(wrap_pyfunction!(solve_td_mols, m)?)?;
    m.add_function(wrap_pyfunction!(regularize_fifo, m)?)?;
    m.add_function(wrap_pyfunction!(interpolate_fifo, m)?)?;
    m.add_function(wrap_pyfunction!(compute_energy_units, m)?)?;
    Ok(())
}
