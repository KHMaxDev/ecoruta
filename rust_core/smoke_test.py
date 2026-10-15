"""Prueba de humo end-to-end del módulo nativo `ecoruta_core`.

Ejecutar tras instalar el wheel:  python rust_core/smoke_test.py
Verifica: física longitudinal, regularización FIFO y frente de Pareto bi-objetivo.
"""
from __future__ import annotations

import ecoruta_core as ec


def main() -> int:
    vehicle = ec.VehicleParams(
        False, 1350.0, 2.15, 0.30, 0.012, 0.28, 0.0, 1200.0, 500.0, 32.1e6, 1.0
    )

    # Grafo diamante: A (rápido con peaje) vs B (libre y barato) vs C (dominado).
    edges = [
        ec.EdgeData(1, 1, 2, -99.1, 19.4, 15000.0, 0.01, 90.0, 24.0, [100.0] * 24, 0.02, 0.0),
        ec.EdgeData(2, 2, 4, -99.0, 19.4, 15000.0, 0.00, 0.0, 24.0, [100.0] * 24, 0.02, 0.0),
        ec.EdgeData(3, 1, 3, -99.1, 19.3, 16000.0, 0.02, 0.0, 24.0, [65.0] * 24, 0.08, 0.0),
        ec.EdgeData(4, 3, 4, -99.0, 19.4, 16000.0, -0.01, 0.0, 24.0, [65.0] * 24, 0.08, 0.0),
        ec.EdgeData(5, 2, 3, -99.1, 19.3, 8000.0, 0.03, 25.0, 24.0, [40.0] * 24, 0.15, 0.0),
    ]

    times = ec.regularize_fifo(15000.0, [100.0] * 24)
    assert len(times) == 24, "la regularización FIFO debe producir 24 tiempos"

    liters = ec.compute_energy_units(1000.0, 0.05, 60.0, 0.05, 0.0, vehicle, 1.05)
    assert liters > 0.0, "el consumo debe ser positivo"

    pareto = ec.solve_td_mols(edges, vehicle, 1, 4, -99.0, 19.4, 28800.0, 1.05, 50, 0.0)
    assert len(pareto) == 2, f"se esperaban 2 soluciones no dominadas, se obtuvieron {len(pareto)}"
    assert pareto[0].node_ids == [1, 3, 4], f"la más barata debe ser 1-3-4, fue {pareto[0].node_ids}"
    assert pareto[1].node_ids == [1, 2, 4], f"la más rápida debe ser 1-2-4, fue {pareto[1].node_ids}"
    assert pareto[0].total_cost_mxn < pareto[1].total_cost_mxn
    assert pareto[0].total_time_s > pareto[1].total_time_s

    print("OK: frente de Pareto correcto")
    for r in pareto:
        print(
            f"  costo={r.total_cost_mxn:8.2f} MXN | tiempo={r.total_time_s:8.1f} s | "
            f"litros={r.total_fuel_liters:6.3f} | nodos={r.node_ids}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
