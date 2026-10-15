"""Selector multiobjetivo: suma ponderada, ε-restricciones y Punto de Codo (Knee Point)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from ecoruta_core import ParetoRoute


class ParetoPreferenceSelector:
    """Analiza la frontera de Pareto y selecciona recomendaciones de ruta."""

    @staticmethod
    def evaluate_pareto_front(
        front: list["ParetoRoute"],
        willingness_to_pay_mxn_per_min: float = 2.5,
        max_budget_mxn: float | None = None,
        max_duration_min: float | None = None,
    ) -> dict[str, Any]:
        if not front:
            return {"status": "infeasible", "routes": []}

        # Filtrar por restricciones ε si el usuario las definió.
        feasible_front = [
            r
            for r in front
            if (max_budget_mxn is None or r.total_cost_mxn <= max_budget_mxn)
            and (max_duration_min is None or (r.total_time_s / 60.0) <= max_duration_min)
        ]

        epsilon_violated = len(feasible_front) == 0
        active_front = front if epsilon_violated else feasible_front

        min_cost_route = min(active_front, key=lambda r: r.total_cost_mxn)
        min_time_route = min(active_front, key=lambda r: r.total_time_s)

        # Punto de Codo: máxima distancia perpendicular a la recta extrema normalizada.
        c_min = min_cost_route.total_cost_mxn
        c_max = max(r.total_cost_mxn for r in active_front)
        t_min = min_time_route.total_time_s
        t_max = max(r.total_time_s for r in active_front)

        c_span = max(c_max - c_min, 1e-6)
        t_span = max(t_max - t_min, 1e-6)

        best_knee_route = active_front[0]
        max_knee_dist = -1.0
        for r in active_front:
            c_norm = (r.total_cost_mxn - c_min) / c_span
            t_norm = (r.total_time_s - t_min) / t_span
            dist = abs(1.0 - c_norm - t_norm) / math.sqrt(2.0)
            if dist > max_knee_dist:
                max_knee_dist = dist
                best_knee_route = r

        # Suma ponderada J(P) = C(P) + λ · T(P).
        user_optimal_route = min(
            active_front,
            key=lambda r: r.total_cost_mxn
            + willingness_to_pay_mxn_per_min * (r.total_time_s / 60.0),
        )

        def serialize(r: "ParetoRoute", tag: str) -> dict[str, Any]:
            savings_vs_fastest_mxn = min_time_route.total_cost_mxn - r.total_cost_mxn
            extra_time_vs_fastest_min = (r.total_time_s - min_time_route.total_time_s) / 60.0
            distance_m = float(getattr(r, "distance_m", 0.0))
            baseline_s = float(getattr(r, "baseline_duration_s", r.total_time_s))
            return {
                "recommendation_tag": tag,
                "total_cost_mxn": round(r.total_cost_mxn, 2),
                "fuel_cost_mxn": round(r.total_cost_mxn - r.total_toll_mxn, 2),
                "toll_cost_mxn": round(r.total_toll_mxn, 2),
                "total_fuel_liters": round(r.total_fuel_liters, 3),
                "duration_minutes": round(r.total_time_s / 60.0, 1),
                "savings_vs_fastest_mxn": round(savings_vs_fastest_mxn, 2),
                "extra_time_vs_fastest_min": round(extra_time_vs_fastest_min, 1),
                "edge_ids": list(r.edge_ids),
                "node_ids": list(r.node_ids),
                "coordinates": [
                    [float(c[0]), float(c[1])] for c in getattr(r, "coordinates", [])
                ],
                "distance_km": round(distance_m / 1000.0, 3),
                "baseline_duration_minutes": round(baseline_s / 60.0, 1),
                "network_source": getattr(r, "source", "real"),
                "route_profile": getattr(r, "profile", "desconocido"),
                "toll_is_estimate": True,
                "is_real_network": True,
            }

        return {
            "status": "epsilon_relaxed" if epsilon_violated else "optimal",
            "pareto_count": len(active_front),
            "recommended_user": serialize(user_optimal_route, "preferencia_usuario"),
            "recommended_knee": serialize(best_knee_route, "punto_de_codo_equilibrado"),
            "cheapest": serialize(min_cost_route, "minimo_costo"),
            "fastest": serialize(min_time_route, "minimo_tiempo"),
            "pareto_frontier": [serialize(r, f"pareto_{i}") for i, r in enumerate(active_front)],
        }
