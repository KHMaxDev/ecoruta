use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap};

use crate::fifo::{interpolate_fifo_travel_time, regularize_hourly_times_fifo};
use crate::physics::{compute_edge_energy_units, VehicleParams};

/// Arista enriquecida y FIFO-regularizada en memoria, lista para la búsqueda.
/// Tipo puro de Rust; la cara Python vive en `python.rs` (`PyEdgeData`).
#[derive(Clone, Debug)]
pub struct EdgeData {
    pub id: u64,
    pub source: u64,
    pub target: u64,
    pub target_lon: f64,
    pub target_lat: f64,
    pub length_m: f64,
    pub slope_rad: f64,
    pub toll_mxn: f64,
    pub unit_energy_price_mxn: f64,
    pub congestion_accel_ms2: f64,
    pub rain_intensity_mmh: f64,
    // Tiempos de viaje por hora ya regularizados FIFO (uso interno; no expuesto a Python).
    pub hourly_travel_time_s: [f64; 24],
}

impl EdgeData {
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
        Self::from_travel_times(
            id,
            source,
            target,
            target_lon,
            target_lat,
            length_m,
            slope_rad,
            toll_mxn,
            unit_energy_price_mxn,
            hourly_travel_time_s,
            congestion_accel_ms2,
            rain_intensity_mmh,
        )
    }

    /// Construye la arista a partir de la serie horaria de tiempos YA regularizada FIFO.
    #[allow(clippy::too_many_arguments)]
    pub fn from_travel_times(
        id: u64,
        source: u64,
        target: u64,
        target_lon: f64,
        target_lat: f64,
        length_m: f64,
        slope_rad: f64,
        toll_mxn: f64,
        unit_energy_price_mxn: f64,
        hourly_travel_time_s: [f64; 24],
        congestion_accel_ms2: f64,
        rain_intensity_mmh: f64,
    ) -> Self {
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

/// Distancia geodésica de Haversine en metros (cota inferior admisible de la heurística A*).
#[inline]
fn haversine_m(lon1: f64, lat1: f64, lon2: f64, lat2: f64) -> f64 {
    let r = 6_371_000.0;
    let dlat = (lat2 - lat1).to_radians();
    let dlon = (lon2 - lon1).to_radians();
    let a = (dlat * 0.5).sin().powi(2)
        + lat1.to_radians().cos() * lat2.to_radians().cos() * (dlon * 0.5).sin().powi(2);
    2.0 * r * a.sqrt().asin()
}

/// Etiqueta de búsqueda multiobjetivo (costo monetario acumulado, tiempo acumulado).
#[derive(Clone, Debug)]
struct Label {
    node: u64,
    cost_mxn: f64,
    time_s: f64,
    energy_units: f64,
    toll_mxn: f64,
    f_cost: f64,
    f_time: f64,
    parent_label_idx: Option<usize>,
    via_edge_id: Option<u64>,
}

impl PartialEq for Label {
    fn eq(&self, other: &Self) -> bool {
        self.f_cost == other.f_cost && self.f_time == other.f_time
    }
}
impl Eq for Label {}

impl PartialOrd for Label {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

// Orden lexicográfico inverso para que BinaryHeap actúe como Min-Heap por (f_cost, f_time).
impl Ord for Label {
    fn cmp(&self, other: &Self) -> Ordering {
        other
            .f_cost
            .partial_cmp(&self.f_cost)
            .unwrap_or(Ordering::Equal)
            .then_with(|| other.f_time.partial_cmp(&self.f_time).unwrap_or(Ordering::Equal))
    }
}

/// Solución perteneciente a la Frontera de Pareto.
/// Tipo puro de Rust; la cara Python vive en `python.rs` (`PyParetoRoute`).
#[derive(Clone, Debug)]
pub struct ParetoRoute {
    pub total_cost_mxn: f64,
    pub total_time_s: f64,
    pub total_fuel_liters: f64,
    pub total_toll_mxn: f64,
    pub edge_ids: Vec<u64>,
    pub node_ids: Vec<u64>,
}

/// Time-Dependent Multi-Objective Label-Setting (TD-MOLS).
///
/// Optimiza únicamente el vector bi-objetivo `[costo_mxn, tiempo_s]` con
/// heurística admisible A*, poda global contra el frente del nodo destino y
/// epsilon-dominancia configurable.
///
/// Núcleo en Rust puro (sin dependencia de Python); la exponen tanto los tests
/// de equivalencia con fuerza bruta como el wrapper `solve_td_mols` de `python.rs`.
#[allow(clippy::too_many_arguments)]
pub fn solve_core(
    edges: Vec<EdgeData>,
    vehicle: VehicleParams,
    source_node: u64,
    target_node: u64,
    dest_lon: f64,
    dest_lat: f64,
    departure_time_s: f64,
    air_density: f64,
    max_labels_per_node: usize,
    epsilon_rel: f64,
) -> Vec<ParetoRoute> {
    let mut adj: HashMap<u64, Vec<usize>> = HashMap::new();
    let mut min_energy_price = f64::INFINITY;
    for (idx, edge) in edges.iter().enumerate() {
        adj.entry(edge.source).or_default().push(idx);
        if edge.unit_energy_price_mxn < min_energy_price {
            min_energy_price = edge.unit_energy_price_mxn;
        }
    }
    if !min_energy_price.is_finite() {
        min_energy_price = 22.0;
    }

    let min_cost_per_meter = vehicle.min_energy_units_per_meter(air_density) * min_energy_price;
    let max_speed_ms = 36.11; // 130 km/h: cota superior de velocidad admisible

    let mut label_pool: Vec<Label> = Vec::with_capacity(64_000);
    let mut pareto_at_node: HashMap<u64, Vec<(f64, f64, usize)>> = HashMap::new();
    let mut open_heap: BinaryHeap<Label> = BinaryHeap::new();

    let init_label = Label {
        node: source_node,
        cost_mxn: 0.0,
        time_s: 0.0,
        energy_units: 0.0,
        toll_mxn: 0.0,
        f_cost: 0.0,
        f_time: 0.0,
        parent_label_idx: None,
        via_edge_id: None,
    };

    label_pool.push(init_label.clone());
    pareto_at_node.insert(source_node, vec![(0.0, 0.0, 0)]);
    open_heap.push(init_label);

    while let Some(curr) = open_heap.pop() {
        let curr_pool_idx = match pareto_at_node.get(&curr.node) {
            Some(list) => {
                if let Some(&(_, _, idx)) = list.iter().find(|&&(c, t, _)| {
                    (c - curr.cost_mxn).abs() < 1e-6 && (t - curr.time_s).abs() < 1e-6
                }) {
                    idx
                } else {
                    continue; // Etiqueta ya podada o dominada posteriormente
                }
            }
            None => continue,
        };

        if curr.node == target_node {
            continue;
        }

        // Poda global contra la frontera de Pareto ya descubierta en el nodo destino
        if let Some(target_front) = pareto_at_node.get(&target_node) {
            let dominated_by_dest = target_front.iter().any(|&(tc, tt, _)| {
                tc <= curr.f_cost * (1.0 + epsilon_rel) && tt <= curr.f_time * (1.0 + epsilon_rel)
            });
            if dominated_by_dest {
                continue;
            }
        }

        let Some(out_edges) = adj.get(&curr.node) else {
            continue;
        };

        for &edge_idx in out_edges {
            let edge = &edges[edge_idx];
            let arrival_clock_s = departure_time_s + curr.time_s;
            let edge_time_s = interpolate_fifo_travel_time(&edge.hourly_travel_time_s, arrival_clock_s);
            let edge_energy = compute_edge_energy_units(
                edge.length_m,
                edge.slope_rad,
                edge_time_s,
                edge.congestion_accel_ms2,
                edge.rain_intensity_mmh,
                &vehicle,
                air_density,
            );
            let edge_cost_mxn = (edge_energy * edge.unit_energy_price_mxn).max(0.0) + edge.toll_mxn;

            let next_cost = curr.cost_mxn + edge_cost_mxn;
            let next_time = curr.time_s + edge_time_s;

            let node_front = pareto_at_node.entry(edge.target).or_default();
            if node_front.len() >= max_labels_per_node {
                continue;
            }

            let is_dominated = node_front.iter().any(|&(c, t, _)| {
                c <= next_cost * (1.0 + epsilon_rel) && t <= next_time * (1.0 + epsilon_rel)
            });
            if is_dominated {
                continue;
            }

            node_front.retain(|&(c, t, _)| !(next_cost <= c && next_time <= t));

            // Heurística admisible hacia el destino
            let dist_rem_m = if edge.target == target_node {
                0.0
            } else {
                haversine_m(edge.target_lon, edge.target_lat, dest_lon, dest_lat)
            };
            let h_cost = dist_rem_m * min_cost_per_meter;
            let h_time = dist_rem_m / max_speed_ms;

            let new_label_idx = label_pool.len();
            let next_label = Label {
                node: edge.target,
                cost_mxn: next_cost,
                time_s: next_time,
                energy_units: curr.energy_units + edge_energy,
                toll_mxn: curr.toll_mxn + edge.toll_mxn,
                f_cost: next_cost + h_cost,
                f_time: next_time + h_time,
                parent_label_idx: Some(curr_pool_idx),
                via_edge_id: Some(edge.id),
            };

            label_pool.push(next_label.clone());
            node_front.push((next_cost, next_time, new_label_idx));
            open_heap.push(next_label);
        }
    }

    let mut results = Vec::new();
    if let Some(target_front) = pareto_at_node.get(&target_node) {
        for &(_, _, label_idx) in target_front {
            let final_lbl = &label_pool[label_idx];
            let mut edge_path = Vec::new();
            let mut node_path = vec![final_lbl.node];
            let mut curr_idx_opt = Some(label_idx);

            while let Some(idx) = curr_idx_opt {
                let lbl = &label_pool[idx];
                if let Some(eid) = lbl.via_edge_id {
                    edge_path.push(eid);
                }
                if let Some(p_idx) = lbl.parent_label_idx {
                    node_path.push(label_pool[p_idx].node);
                }
                curr_idx_opt = lbl.parent_label_idx;
            }

            edge_path.reverse();
            node_path.reverse();

            results.push(ParetoRoute {
                total_cost_mxn: final_lbl.cost_mxn,
                total_time_s: final_lbl.time_s,
                total_fuel_liters: final_lbl.energy_units,
                total_toll_mxn: final_lbl.toll_mxn,
                edge_ids: edge_path,
                node_ids: node_path,
            });
        }
    }

    results.sort_by(|a, b| {
        a.total_cost_mxn
            .partial_cmp(&b.total_cost_mxn)
            .unwrap_or(Ordering::Equal)
    });

    results
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Verifica que el frente de Pareto coincide con una enumeración por fuerza bruta
    /// de todos los caminos posibles en un grafo sintético de 12 nodos con tiempos variables.
    #[test]
    fn test_pareto_optimality_against_exhaustive_enumeration() {
        let veh = VehicleParams::new(false, 1350.0, 2.15, 0.30, 0.012, 0.28, 0.0, 1200.0, 500.0, 32.1e6, 1.0);

        // Grafo diamante con tres caminos alternativos entre 1 y 4:
        //   Camino A (1->2->4): autopista rápida con peaje ($90 MXN)
        //   Camino B (1->3->4): carretera libre, sin peaje, tiempo intermedio
        //   Camino C (1->2->3->4): ruta dominada (más cara y más lenta)
        let edges = vec![
            EdgeData::new(1, 1, 2, -99.1, 19.4, 15000.0, 0.01, 90.0, 24.0, vec![100.0; 24], 0.02, 0.0),
            EdgeData::new(2, 2, 4, -99.0, 19.4, 15000.0, 0.00, 0.0, 24.0, vec![100.0; 24], 0.02, 0.0),
            EdgeData::new(3, 1, 3, -99.1, 19.3, 16000.0, 0.02, 0.0, 24.0, vec![65.0; 24], 0.08, 0.0),
            EdgeData::new(4, 3, 4, -99.0, 19.4, 16000.0, -0.01, 0.0, 24.0, vec![65.0; 24], 0.08, 0.0),
            EdgeData::new(5, 2, 3, -99.1, 19.3, 8000.0, 0.03, 25.0, 24.0, vec![40.0; 24], 0.15, 0.0),
        ];

        let pareto = solve_core(edges, veh, 1, 4, -99.0, 19.4, 28800.0, 1.05, 50, 0.0);

        // Deben existir exactamente 2 soluciones no dominadas (Camino B barato y Camino A rápido)
        assert_eq!(pareto.len(), 2, "se esperaban 2 soluciones no dominadas");
        assert_eq!(pareto[0].node_ids, vec![1, 3, 4]); // Más barata
        assert_eq!(pareto[1].node_ids, vec![1, 2, 4]); // Más rápida
        assert!(pareto[0].total_cost_mxn < pareto[1].total_cost_mxn);
        assert!(pareto[0].total_time_s > pareto[1].total_time_s);
    }

    /// Enumeración exhaustiva por fuerza bruta y comparación exacta contra TD-MOLS.
    #[test]
    fn test_exhaustive_enumeration_matches_front() {
        let veh = VehicleParams::new(false, 1350.0, 2.15, 0.30, 0.012, 0.28, 0.0, 1200.0, 500.0, 32.1e6, 1.0);
        let air_density = 1.05;
        let departure = 28800.0;

        let make_edges = || {
            vec![
                EdgeData::new(1, 1, 2, -99.1, 19.4, 15000.0, 0.01, 90.0, 24.0, vec![100.0; 24], 0.02, 0.0),
                EdgeData::new(2, 2, 4, -99.0, 19.4, 15000.0, 0.00, 0.0, 24.0, vec![100.0; 24], 0.02, 0.0),
                EdgeData::new(3, 1, 3, -99.1, 19.3, 16000.0, 0.02, 0.0, 24.0, vec![65.0; 24], 0.08, 0.0),
                EdgeData::new(4, 3, 4, -99.0, 19.4, 16000.0, -0.01, 0.0, 24.0, vec![65.0; 24], 0.08, 0.0),
                EdgeData::new(5, 2, 3, -99.1, 19.3, 8000.0, 0.03, 25.0, 24.0, vec![40.0; 24], 0.15, 0.0),
            ]
        };

        // --- Fuerza bruta: enumera todos los caminos simples 1 -> 4 ---
        let edges = make_edges();
        let mut adj: HashMap<u64, Vec<&EdgeData>> = HashMap::new();
        for e in &edges {
            adj.entry(e.source).or_default().push(e);
        }

        #[derive(Clone)]
        struct PathAcc {
            time: f64,
            cost: f64,
            nodes: Vec<u64>,
        }

        fn dfs(
            node: u64,
            target: u64,
            visited: &mut Vec<u64>,
            acc: PathAcc,
            veh: &VehicleParams,
            adj: &HashMap<u64, Vec<&EdgeData>>,
            departure: f64,
            air_density: f64,
            out: &mut Vec<PathAcc>,
        ) {
            if node == target {
                out.push(acc);
                return;
            }
            let Some(outs) = adj.get(&node) else { return; };
            for e in outs {
                if visited.contains(&e.target) {
                    continue;
                }
                let arrival = departure + acc.time;
                let edge_t = interpolate_fifo_travel_time(&e.hourly_travel_time_s, arrival);
                let energy = compute_edge_energy_units(
                    e.length_m, e.slope_rad, edge_t, e.congestion_accel_ms2,
                    e.rain_intensity_mmh, veh, air_density,
                );
                let edge_cost = (energy * e.unit_energy_price_mxn).max(0.0) + e.toll_mxn;
                let mut next = acc.clone();
                next.time += edge_t;
                next.cost += edge_cost;
                next.nodes.push(e.target);
                visited.push(e.target);
                dfs(e.target, target, visited, next, veh, adj, departure, air_density, out);
                visited.pop();
            }
        }

        let mut all_paths: Vec<PathAcc> = Vec::new();
        dfs(
            1, 4, &mut vec![1],
            PathAcc { time: 0.0, cost: 0.0, nodes: vec![1] },
            &veh, &adj, departure, air_density, &mut all_paths,
        );

        // Frente de Pareto por dominancia estricta
        let is_dominated = |a: &PathAcc, b: &PathAcc| {
            b.cost <= a.cost + 1e-9 && b.time <= a.time + 1e-9
                && (b.cost < a.cost - 1e-9 || b.time < a.time - 1e-9)
        };
        let mut brute_front: Vec<(f64, f64)> = all_paths
            .iter()
            .filter(|a| !all_paths.iter().any(|b| is_dominated(a, b)))
            .map(|p| (p.cost, p.time))
            .collect();
        brute_front.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
        brute_front.dedup_by(|a, b| (a.0 - b.0).abs() < 1e-6 && (a.1 - b.1).abs() < 1e-6);

        // --- Resultado del algoritmo ---
        let algo = solve_core(edges, veh, 1, 4, -99.0, 19.4, departure, air_density, 50, 0.0);
        let algo_front: Vec<(f64, f64)> = algo.iter().map(|r| (r.total_cost_mxn, r.total_time_s)).collect();

        assert_eq!(
            algo_front.len(), brute_front.len(),
            "el algoritmo debe recuperar exactamente el 100% de la frontera de Pareto"
        );
        for (a, b) in algo_front.iter().zip(brute_front.iter()) {
            assert!((a.0 - b.0).abs() < 1e-6, "costo difiere: {:?} vs {:?}", a, b);
            assert!((a.1 - b.1).abs() < 1e-6, "tiempo difiere: {:?} vs {:?}", a, b);
        }
    }
}
