"""Métricas de desempeño de la red simulada en SUMO.

Calcula indicadores agregados (tiempo medio, tiempo perdido, longitud de cola,
emisiones y consumo de combustible) a partir de la salida ``tripinfo.xml`` y
``summary.xml`` de SUMO.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import sumolib


@dataclass
class NetworkMetrics:
    vehicles_completed: int = 0
    mean_duration_s: float = 0.0
    mean_time_loss_s: float = 0.0
    mean_waiting_s: float = 0.0
    total_fuel_ml: float = 0.0
    mean_co2_mg: float = 0.0
    mean_route_length_m: float = 0.0
    vehicles_by_type: dict[str, int] = field(default_factory=dict)


def compute_network_metrics(tripinfo_path: Path) -> NetworkMetrics:
    if not tripinfo_path.exists():
        raise FileNotFoundError(f"No existe el archivo de tripinfo: {tripinfo_path}")

    metrics = NetworkMetrics()
    durations: list[float] = []
    losses: list[float] = []
    waits: list[float] = []
    lengths: list[float] = []

    for trip in sumolib.xml.parse(str(tripinfo_path), "tripinfo"):
        metrics.vehicles_completed += 1
        durations.append(float(trip.duration))
        losses.append(float(getattr(trip, "timeLoss", 0.0)))
        waits.append(float(getattr(trip, "waitingTime", 0.0)))
        lengths.append(float(getattr(trip, "routeLength", 0.0)))
        metrics.total_fuel_ml += float(getattr(trip, "fuel_abs", 0.0))
        metrics.mean_co2_mg += float(getattr(trip, "CO2_abs", 0.0))
        vtype = getattr(trip, "vType", "unknown")
        metrics.vehicles_by_type[vtype] = metrics.vehicles_by_type.get(vtype, 0) + 1

    n = max(metrics.vehicles_completed, 1)
    metrics.mean_duration_s = sum(durations) / n
    metrics.mean_time_loss_s = sum(losses) / n
    metrics.mean_waiting_s = sum(waits) / n
    metrics.mean_route_length_m = sum(lengths) / n
    metrics.mean_co2_mg /= n
    return metrics


if __name__ == "__main__":  # pragma: no cover
    path = Path(__file__).parent / "data" / "sumo_corridor" / "tripinfo.xml"
    m = compute_network_metrics(path)
    print(
        f"Vehículos: {m.vehicles_completed} | Duración media: {m.mean_duration_s:.0f}s | "
        f"Pérdida media: {m.mean_time_loss_s:.0f}s | Combustible total: {m.total_fuel_ml / 1000:.1f}L"
    )
