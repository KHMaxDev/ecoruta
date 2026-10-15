"""Optimizador de múltiples paradas dependiente del tiempo (GTDVRPTW) con OR-Tools.

Construye la matriz de costo generalizado J_ij = C_ij + λ·T_ij (calculada por el
motor multiobjetivo en Rust) y resuelve la secuencia óptima de paradas con ventanas
de tiempo mediante Google OR-Tools.
"""

from __future__ import annotations

from typing import Any

from ortools.constraint_solver import pywrapcp, routing_enums_pb2


class MultiStopVRPOptimizer:
    """Resuelve la secuencia óptima de paradas sobre una matriz de costo generalizado."""

    @staticmethod
    def solve_sequence(
        cost_matrix_mxn: list[list[float]],
        time_matrix_min: list[list[int]],
        time_windows_min: list[tuple[int, int]],
        willingness_to_pay_mxn_per_min: float = 2.0,
        depot_index: int = 0,
    ) -> dict[str, Any]:
        num_locations = len(cost_matrix_mxn)
        if num_locations == 0:
            return {"status": "infeasible", "ordered_waypoints": []}
        if len(cost_matrix_mxn) != num_locations or len(time_matrix_min) != num_locations:
            raise ValueError("Matrices de costo y tiempo con dimensiones inconsistentes.")
        if len(time_windows_min) != num_locations:
            raise ValueError("Las ventanas de tiempo deben cubrir todas las ubicaciones.")

        manager = pywrapcp.RoutingIndexManager(num_locations, 1, depot_index)
        routing = pywrapcp.RoutingModel(manager)

        # 1. Callback de costo generalizado (escalado x100 para aritmética entera).
        def generalized_cost_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            c_mxn = cost_matrix_mxn[from_node][to_node]
            t_min = time_matrix_min[from_node][to_node]
            j_val = c_mxn + willingness_to_pay_mxn_per_min * t_min
            return int(round(j_val * 100))

        transit_callback_index = routing.RegisterTransitCallback(generalized_cost_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # 2. Dimensión temporal para las ventanas de llegada.
        def time_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(time_matrix_min[from_node][to_node])

        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            60,  # Espera máxima permitida en un nodo (min).
            1440,  # Horizonte máximo diario (24 h).
            False,
            "Time",
        )
        time_dimension = routing.GetDimensionOrDie("Time")

        for loc_idx, (tw_start, tw_end) in enumerate(time_windows_min):
            index = manager.NodeToIndex(loc_idx)
            time_dimension.CumulVar(index).SetRange(tw_start, tw_end)

        # 3. Metaheurística Guided Local Search.
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 3

        solution = routing.SolveWithParameters(search_parameters)
        if not solution:
            return {"status": "infeasible", "ordered_waypoints": []}

        ordered_nodes: list[int] = []
        total_cost_mxn = 0.0
        total_time_min = 0
        index = routing.Start(0)

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            ordered_nodes.append(node)
            next_index = solution.Value(routing.NextVar(index))
            if not routing.IsEnd(next_index):
                next_node = manager.IndexToNode(next_index)
                total_cost_mxn += cost_matrix_mxn[node][next_node]
                total_time_min += time_matrix_min[node][next_node]
            index = next_index

        return {
            "status": "optimal_sequence",
            "ordered_waypoints": ordered_nodes,
            "estimated_total_cost_mxn": round(total_cost_mxn, 2),
            "estimated_total_time_min": total_time_min,
        }
