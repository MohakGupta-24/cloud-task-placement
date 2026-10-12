"""End-to-End Cloud Task Placement Optimizer.

Integrates:
1. Minimum Spanning Tree (MST) for communication backbone topology.
2. All-Pairs Shortest Paths (APSP) for end-to-end request routing.
3. 0-1 Knapsack Dynamic Programming for capacity-constrained placement selection.
4. Comprehensive policy outputs: Placements, Routing Table, Cost/Benefit Table, and Latency Metrics.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..graph.graph import Graph
from ..mst.kruskal import kruskal_mst
from ..shortest_paths.floyd_warshall import floyd_warshall, reconstruct_apsp_path
from ..placement.models import PlacementOption, PlacementResult
from ..placement.knapsack_dp import knapsack_01_dp
from ..placement.greedy_scheduler import greedy_placement_selection
from .workload import Task


@dataclass
class PlacementDecision:
    """Record of a task placed on a specific server."""
    task_id: str
    server_id: int
    demand_cost: int
    baseline_latency: float
    optimized_latency: float
    latency_benefit: float
    total_benefit: float
    efficiency_ratio: float


@dataclass
class ServerPlacementSummary:
    """Capacity and placement summary for a single physical server."""
    server_id: int
    total_capacity: int
    used_capacity: int
    placed_tasks: List[str]
    total_latency_benefit: float

    @property
    def utilization_percent(self) -> float:
        return (self.used_capacity / self.total_capacity * 100.0) if self.total_capacity > 0 else 0.0


@dataclass
class OptimizerReport:
    """Complete optimization report and policy recommendations."""
    # MST Backbone
    mst_edges: List[Tuple[int, int, float]]
    mst_total_weight: float
    backbone_sync_latency: float

    # Routing Table: (source, destination) -> {"path": [...], "latency": float}
    routing_table: Dict[Tuple[int, int], Dict[str, Any]]

    # Placement Decisions & Tables
    server_summaries: List[ServerPlacementSummary]
    cost_benefit_table: List[PlacementDecision]
    unplaced_tasks: List[str]

    # Aggregate System Metrics
    baseline_average_latency: float
    optimized_average_latency: float
    latency_reduction_percent: float
    total_capacity_utilization: float

    # Greedy Comparison Baseline
    greedy_optimized_latency: float
    greedy_latency_reduction_percent: float


class CloudPlacementOptimizer:
    """Orchestrates MST backbone extraction, APSP routing, and DP placement selection."""

    def __init__(self, graph: Graph, tasks: List[Task]) -> None:
        """Initializes the optimizer with a network topology and workload.

        Args:
            graph: The cloud server network topology.
            tasks: List of tasks with resource demands and client traffic profiles.
        """
        self.graph: Graph = graph
        self.tasks: List[Task] = tasks

    def optimize(self) -> OptimizerReport:
        """Executes the full optimization pipeline and returns a structured report."""
        nodes = self.graph.get_nodes()

        # =========================================================================
        # Stage 1: MST Backbone Extraction (Kruskal's Algorithm)
        # =========================================================================
        mst_edges, mst_total_weight = kruskal_mst(self.graph)

        # Build MST subgraph to calculate average inter-server synchronization latency
        mst_graph = Graph(directed=False)
        for node in nodes:
            mst_graph.add_node(node)
        for u, v, weight in mst_edges:
            mst_graph.add_edge(u, v, latency=weight)

        mst_dist_matrix, _ = floyd_warshall(mst_graph)
        num_pairs = (len(nodes) * (len(nodes) - 1)) // 2
        total_backbone_dist = sum(
            mst_dist_matrix[u][v]
            for i, u in enumerate(nodes)
            for v in nodes[i + 1:]
            if mst_dist_matrix[u][v] != float("inf")
        )
        backbone_sync_latency = (
            round(total_backbone_dist / num_pairs, 2) if num_pairs > 0 else 0.0
        )

        # =========================================================================
        # Stage 2: All-Pairs Shortest Paths & Routing Table (Floyd-Warshall)
        # =========================================================================
        dist_matrix, pred_matrix = floyd_warshall(self.graph)

        routing_table: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for u in nodes:
            for v in nodes:
                path = reconstruct_apsp_path(pred_matrix, u, v)
                routing_table[(u, v)] = {
                    "path": path,
                    "latency": dist_matrix[u][v],
                }

        # =========================================================================
        # Stage 3: Latency-Benefit Formulation
        # =========================================================================
        # Compute access latency for each task on each candidate server
        task_server_latencies: Dict[str, Dict[int, float]] = {}
        task_baseline_latency: Dict[str, float] = {}
        task_preferred_server: Dict[str, int] = {}

        for task in self.tasks:
            latencies_per_server: Dict[int, float] = {}
            total_requests = task.total_requests or 1.0

            for server in nodes:
                weighted_sum = sum(
                    req_volume * dist_matrix[client][server]
                    for client, req_volume in task.client_requests.items()
                )
                latencies_per_server[server] = round(weighted_sum / total_requests, 3)

            task_server_latencies[task.task_id] = latencies_per_server
            # Baseline is worst-case unoptimized access latency (or remote gateway)
            baseline = max(latencies_per_server.values())
            task_baseline_latency[task.task_id] = baseline

            # Preferred server is the one that minimizes client access latency
            preferred = min(latencies_per_server, key=latencies_per_server.get)
            task_preferred_server[task.task_id] = preferred

        # =========================================================================
        # Stage 4: Knapsack DP Selection (and Greedy Baseline)
        # =========================================================================
        # Group tasks by their primary affinity server
        server_candidate_items: Dict[int, List[PlacementOption]] = {s: [] for s in nodes}

        for task in self.tasks:
            pref_server = task_preferred_server[task.task_id]
            best_lat = task_server_latencies[task.task_id][pref_server]
            baseline_lat = task_baseline_latency[task.task_id]
            delta_lat = max(0.0, baseline_lat - best_lat)
            # Weighted benefit represents aggregate network latency saved across all user requests
            total_benefit = delta_lat * task.total_requests

            # Capacity cost is the task demand
            server_candidate_items[pref_server].append(
                PlacementOption(
                    item_id=task.task_id,
                    cost=task.demand,
                    benefit=total_benefit,
                    metadata={
                        "task": task,
                        "best_latency": best_lat,
                        "baseline_latency": baseline_lat,
                        "delta_latency": delta_lat,
                    },
                )
            )

        # Solve Knapsack DP on each server
        dp_results: Dict[int, PlacementResult] = {}
        greedy_results: Dict[int, PlacementResult] = {}

        for server in nodes:
            server_capacity = int(self.graph.get_capacity(server))
            candidates = server_candidate_items[server]

            dp_results[server] = knapsack_01_dp(candidates, server_capacity)
            greedy_results[server] = greedy_placement_selection(candidates, server_capacity)

        # =========================================================================
        # Stage 5: Compile Placement Summaries & Cost/Benefit Table
        # =========================================================================
        server_summaries: List[ServerPlacementSummary] = []
        cost_benefit_table: List[PlacementDecision] = []
        placed_task_ids: set[str] = set()

        for server in nodes:
            res = dp_results[server]
            placed_ids = [str(item.item_id) for item in res.selected_items]
            placed_task_ids.update(placed_ids)

            server_summaries.append(
                ServerPlacementSummary(
                    server_id=server,
                    total_capacity=int(self.graph.get_capacity(server)),
                    used_capacity=res.total_cost,
                    placed_tasks=placed_ids,
                    total_latency_benefit=round(res.total_benefit, 2),
                )
            )

            for item in res.selected_items:
                best_lat = item.metadata["best_latency"]
                base_lat = item.metadata["baseline_latency"]
                delta_lat = item.metadata["delta_latency"]
                ratio = (delta_lat / item.cost) if item.cost > 0 else 0.0

                cost_benefit_table.append(
                    PlacementDecision(
                        task_id=str(item.item_id),
                        server_id=server,
                        demand_cost=item.cost,
                        baseline_latency=base_lat,
                        optimized_latency=best_lat,
                        latency_benefit=delta_lat,
                        total_benefit=round(item.benefit, 2),
                        efficiency_ratio=round(ratio, 4),
                    )
                )

        unplaced_tasks = [t.task_id for t in self.tasks if t.task_id not in placed_task_ids]

        # =========================================================================
        # Stage 6: Calculate System-Wide Average Latencies
        # =========================================================================
        total_traffic = sum(t.total_requests for t in self.tasks) or 1.0

        # 6a. Baseline Average Latency: All tasks served at their worst/unplaced latency
        baseline_total_weighted_lat = sum(
            task_baseline_latency[t.task_id] * t.total_requests for t in self.tasks
        )
        baseline_avg_latency = round(baseline_total_weighted_lat / total_traffic, 2)

        # 6b. DP Optimized Average Latency: Placed tasks served at preferred host
        dp_total_weighted_lat = 0.0
        for task in self.tasks:
            if task.task_id in placed_task_ids:
                server = task_preferred_server[task.task_id]
                lat = task_server_latencies[task.task_id][server]
            else:
                lat = task_baseline_latency[task.task_id]
            dp_total_weighted_lat += lat * task.total_requests

        dp_avg_latency = round(dp_total_weighted_lat / total_traffic, 2)
        reduction_pct = (
            round((baseline_avg_latency - dp_avg_latency) / baseline_avg_latency * 100.0, 2)
            if baseline_avg_latency > 0 else 0.0
        )

        # 6c. Greedy Comparison Average Latency
        greedy_placed_ids = {
            str(item.item_id)
            for res in greedy_results.values()
            for item in res.selected_items
        }
        greedy_total_weighted_lat = 0.0
        for task in self.tasks:
            if task.task_id in greedy_placed_ids:
                server = task_preferred_server[task.task_id]
                lat = task_server_latencies[task.task_id][server]
            else:
                lat = task_baseline_latency[task.task_id]
            greedy_total_weighted_lat += lat * task.total_requests

        greedy_avg_latency = round(greedy_total_weighted_lat / total_traffic, 2)
        greedy_reduction_pct = (
            round((baseline_avg_latency - greedy_avg_latency) / baseline_avg_latency * 100.0, 2)
            if baseline_avg_latency > 0 else 0.0
        )

        # Overall capacity utilization across all servers
        total_used = sum(s.used_capacity for s in server_summaries)
        total_cap = sum(s.total_capacity for s in server_summaries)
        overall_utilization = round((total_used / total_cap * 100.0), 2) if total_cap > 0 else 0.0

        return OptimizerReport(
            mst_edges=mst_edges,
            mst_total_weight=round(mst_total_weight, 2),
            backbone_sync_latency=backbone_sync_latency,
            routing_table=routing_table,
            server_summaries=server_summaries,
            cost_benefit_table=cost_benefit_table,
            unplaced_tasks=unplaced_tasks,
            baseline_average_latency=baseline_avg_latency,
            optimized_average_latency=dp_avg_latency,
            latency_reduction_percent=reduction_pct,
            total_capacity_utilization=overall_utilization,
            greedy_optimized_latency=greedy_avg_latency,
            greedy_latency_reduction_percent=greedy_reduction_pct,
        )
