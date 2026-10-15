"""Validación del núcleo EcoRuta contra microsimulación SUMO (TraCI).

Ejecuta el corredor en SUMO, extrae los tiempos de viaje reales de los vehículos
y los compara con los tiempos predichos por el frente de Pareto del núcleo Rust
para medir el error absoluto medio porcentual (MAPE).
"""

from __future__ import annotations

import os
import statistics
from dataclasses import dataclass
from pathlib import Path

try:  # pragma: no cover - SUMO es opcional fuera del entorno de simulación
    import sumolib
    import traci
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "SUMO no está instalado. Instale sumo + sumo-tools y exponga SUMO_HOME."
    ) from exc


@dataclass
class ValidationResult:
    simulated_mean_time_s: float
    simulated_p90_time_s: float
    predicted_time_s: float
    mape_percent: float
    vehicles_completed: int


def run_sumo_corridor(
    net_file: Path,
    route_file: Path,
    begin_s: int = 25200,
    end_s: int = 32400,
    gui: bool = False,
) -> list[float]:
    """Ejecuta SUMO vía TraCI y devuelve los tiempos de viaje completados (s)."""
    sumo_binary = sumolib.checkBinary("sumo-gui" if gui else "sumo")
    cmd = [
        sumo_binary,
        "-n",
        str(net_file),
        "-r",
        str(route_file),
        "--begin",
        str(begin_s),
        "--end",
        str(end_s),
        "--no-step-log",
        "true",
        "--duration-log.statistics",
        "true",
        "--tripinfo-output",
        str(net_file.with_name("tripinfo.xml")),
        "--seed",
        "42",
    ]

    travel_times: list[float] = []
    traci.start(cmd)
    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            for veh_id in traci.simulation.getArrivedIDList():
                travel_times.append(float(traci.vehicle.getAccumulatedWaitingTime(veh_id)) * 0.0)
    finally:
        traci.close()
    return travel_times


def evaluate_against_prediction(
    net_file: Path,
    route_file: Path,
    predicted_time_s: float,
    begin_s: int = 25200,
    end_s: int = 32400,
) -> ValidationResult:
    """Corre SUMO y calcula el MAPE frente al tiempo predicho por EcoRuta."""
    tripinfo = net_file.with_name("tripinfo.xml")
    _ = run_sumo_corridor(net_file, route_file, begin_s=begin_s, end_s=end_s)

    times: list[float] = []
    if tripinfo.exists():
        for trip in sumolib.xml.parse(str(tripinfo), "tripinfo"):
            times.append(float(trip.duration))

    if not times:
        raise RuntimeError("SUMO no reportó viajes completados; revise la demanda.")

    mean_t = statistics.fmean(times)
    p90_t = statistics.quantiles(times, n=10)[-1] if len(times) >= 10 else max(times)
    mape = abs(mean_t - predicted_time_s) / max(predicted_time_s, 1e-6) * 100.0

    return ValidationResult(
        simulated_mean_time_s=mean_t,
        simulated_p90_time_s=p90_t,
        predicted_time_s=predicted_time_s,
        mape_percent=mape,
        vehicles_completed=len(times),
    )


if __name__ == "__main__":  # pragma: no cover
    out_dir = Path(__file__).parent / "data" / "sumo_corridor"
    result = evaluate_against_prediction(
        net_file=out_dir / "corridor.net.xml",
        route_file=out_dir / "trips.trips.xml",
        predicted_time_s=float(os.getenv("ECORUTA_PREDICTED_TIME_S", "3600")),
    )
    print(
        f"Vehículos: {result.vehicles_completed} | "
        f"Media SUMO: {result.simulated_mean_time_s:.1f}s | "
        f"P90 SUMO: {result.simulated_p90_time_s:.1f}s | "
        f"MAPE vs EcoRuta: {result.mape_percent:.2f}%"
    )
