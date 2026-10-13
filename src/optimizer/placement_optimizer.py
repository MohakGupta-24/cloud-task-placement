"""End-to-End Cloud Task Placement Optimizer with Iterative Knapsack Rounds and MST Sync.

Incorporates:
1. Multi-server feasibility: Tasks can be placed on ANY server with sufficient capacity.
2. Iterative Knapsack Rounds with Regret:
   - In each round, unplaced tasks propose to their best feasible server.
   - Proposal benefit = regret = Cost(next-best feasible server) - Cost(best server).
   - Servers run 0-1 Knapsack DP (or greedy ratio) to admit highest-regret proposals.
   - Rejected tasks re-propose to remaining feasible servers in subsequent rounds.
3. Multi-Strategy Benchmarking:
   - Iterative Knapsack DP
   - Iterative Greedy Heuristic
   - Spill-over Greedy (highest traffic first, best available server)
   - Random Feasible Placement
   - Unconstrained Lower Bound (ignoring server capacities)
   - Exact Brute-Force Assignment Solver (for small instances)
4. MST Backbone Integration:
   - Weighted median node of the MST acts as the synchronization hub.
   - Sync cost = replication_traffic * MST_path_distance(host, sync_hub).
   - Objective = weighted_access_latency + lambda_sync * sync_cost.
"""

from __future__ import annotations
import itertools
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from ..graph.graph import Graph
from ..mst.kruskal import kruskal_mst
from ..shortest_paths.floyd_warshall import floyd_warshall, reconstruct_apsp_path
from ..placement.models import PlacementOption, PlacementResult
from ..placement.knapsack_dp import knapsack_01_dp
from ..placement.greedy_scheduler import greedy_placement_selection
from .workload import Task


@dataclass
class PlacementDecision:
    """Record of an accepted task placement on a server."""
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
class StrategyMetrics:
    """Comprehensive performance metrics for a specific placement strategy."""
    strategy_name: str
    placed_tasks_count: int
    unplaced_tasks_count: int
    unplaced_task_ids: List[str]
    average_access_latency: float  # ms across placed requests
    average_sync_cost: float       # mean sync cost across placed tasks
    total_objective: float         # sum of composite costs across placed tasks
    fleet_utilization_pct: float
    assignments: Dict[str, int]    # task_id -> server_id


@dataclass
class OptimizerReport:
    """Full optimization report comparing all placement strategies and MST backbone."""
    mst_edges: List[Tuple[int, int, float]]
    mst_total_weight: float
    sync_hub_node: int
    backbone_sync_latency: float
    routing_table: Dict[Tuple[int, int], Dict[str, Any]]
    
    # Strategy-specific metrics
    strategy_metrics: Dict[str, StrategyMetrics]

    # Primary DP Strategy Details (for backward compatibility and detailed views)
    server_summaries: List[ServerPlacementSummary]
    cost_benefit_table: List[PlacementDecision]
    unplaced_tasks: List[str]
    baseline_average_latency: float
    optimized_average_latency: float
    latency_reduction_percent: float
    total_capacity_utilization: float
    greedy_optimized_latency: float
    greedy_latency_reduction_percent: float


class CloudPlacementOptimizer:
    """Orchestrates MST hub extraction, APSP routing, and iterative knapsack placement."""

    def __init__(
        self,
        graph: Graph,
        tasks: List[Task],
        lambda_sync: float = 0.0,
    ) -> None:
        """Initializes the optimizer.

        Args:
            graph: The cloud server network topology.
            tasks: List of tasks with resource demands, traffic, and replication rates.
            lambda_sync: Weighting parameter for MST replication synchronization cost.
                When lambda_sync == 0.0, reproduces pure access latency optimization.
        """
        self.graph: Graph = graph
        self.tasks: List[Task] = tasks
        self.lambda_sync: float = float(lambda_sync)
        self.task_map: Dict[str, Task] = {t.task_id: t for t in tasks}

    def _compute_mst_and_hub(
        self,
    ) -> Tuple[List[Tuple[int, int, float]], float, int, Dict[int, Dict[int, float]], float]:
        """Extracts MST backbone and identifies the weighted median sync hub."""
        nodes = self.graph.get_nodes()
        mst_edges, mst_weight = kruskal_mst(self.graph)

        mst_g = Graph(directed=False)
        for n in nodes:
            mst_g.add_node(n)
        for u, v, w in mst_edges:
            mst_g.add_edge(u, v, latency=w)

        mst_dist, _ = floyd_warshall(mst_g)

        # Weighted median node: minimizes sum of w_v * D_MST(v, hub)
        # Node weight w_v represents total traffic originating at client node v
        node_weights: Dict[int, float] = {n: 1.0 for n in nodes}
        for task in sorted(self.tasks, key=lambda t: t.task_id):
            for client in sorted(task.client_requests.keys()):
                req = task.client_requests[client]
                node_weights[client] = node_weights.get(client, 1.0) + req

        best_hub = nodes[0]
        min_hub_weighted_dist = float("inf")
        for candidate_hub in nodes:
            weighted_sum = sum(
                node_weights[v] * mst_dist[v][candidate_hub] for v in nodes
            )
            if weighted_sum < min_hub_weighted_dist:
                min_hub_weighted_dist = weighted_sum
                best_hub = candidate_hub

        # Average inter-server synchronization delay across backbone
        num_pairs = (len(nodes) * (len(nodes) - 1)) // 2
        total_backbone_dist = sum(
            mst_dist[u][v]
            for i, u in enumerate(nodes)
            for v in nodes[i + 1:]
            if mst_dist[u][v] != float("inf")
        )
        avg_sync_latency = round(total_backbone_dist / num_pairs, 2) if num_pairs > 0 else 0.0

        return mst_edges, mst_weight, best_hub, mst_dist, avg_sync_latency

    def _task_server_cost(
        self,
        task: Task,
        server: int,
        dist_matrix: Dict[int, Dict[int, float]],
        mst_dist_matrix: Dict[int, Dict[int, float]],
        sync_hub: int,
    ) -> Tuple[float, float, float]:
        """Calculates access delay, sync cost, and composite cost of placing task on server.

        Returns:
            Tuple of (per_request_access_latency, sync_cost, composite_cost).
        """
        total_traffic = task.total_requests or 1.0
        weighted_access_delay = sum(
            task.client_requests[client] * dist_matrix[client][server]
            for client in sorted(task.client_requests.keys())
        )
        per_req_lat = weighted_access_delay / total_traffic

        # Sync cost along MST to hub: replication_traffic * D_MST(server, hub)
        sync_cost = task.replication_traffic * mst_dist_matrix[server][sync_hub]

        # Composite cost: total access delay + lambda * sync_cost
        composite = weighted_access_delay + (self.lambda_sync * sync_cost)
        return per_req_lat, sync_cost, composite

    def _evaluate_assignments(
        self,
        strategy_name: str,
        assignments: Dict[str, int],
        unplaced_ids: List[str],
        dist_matrix: Dict[int, Dict[int, float]],
        mst_dist_matrix: Dict[int, Dict[int, float]],
        sync_hub: int,
    ) -> StrategyMetrics:
        """Computes standardized metrics for any given placement assignment."""
        nodes = self.graph.get_nodes()
        total_placed_traffic = 0.0
        total_weighted_access_delay = 0.0
        total_sync_cost = 0.0
        total_composite_cost = 0.0

        server_used_cap: Dict[int, int] = {n: 0 for n in nodes}

        for task_id in sorted(assignments.keys()):
            server = assignments[task_id]
            task = self.task_map[task_id]
            server_used_cap[server] += task.demand
            per_lat, sync, comp = self._task_server_cost(
                task, server, dist_matrix, mst_dist_matrix, sync_hub
            )
            total_placed_traffic += task.total_requests
            total_weighted_access_delay += per_lat * task.total_requests
            total_sync_cost += sync
            total_composite_cost += comp

        avg_access_lat = (
            round(total_weighted_access_delay / total_placed_traffic, 3)
            if total_placed_traffic > 0 else 0.0
        )
        avg_sync = (
            round(total_sync_cost / len(assignments), 3)
            if assignments else 0.0
        )
        tot_cap = sum(self.graph.get_capacity(n) for n in nodes)
        used_cap = sum(server_used_cap.values())
        fleet_util = round((used_cap / tot_cap * 100.0), 2) if tot_cap > 0 else 0.0

        return StrategyMetrics(
            strategy_name=strategy_name,
            placed_tasks_count=len(assignments),
            unplaced_tasks_count=len(unplaced_ids),
            unplaced_task_ids=sorted(unplaced_ids),
            average_access_latency=avg_access_lat,
            average_sync_cost=avg_sync,
            total_objective=round(total_composite_cost, 2),
            fleet_utilization_pct=fleet_util,
            assignments=assignments,
        )

    def _run_iterative_knapsack(
        self,
        use_dp: bool,
        dist_matrix: Dict[int, Dict[int, float]],
        mst_dist_matrix: Dict[int, Dict[int, float]],
        sync_hub: int,
    ) -> Tuple[Dict[str, int], List[str]]:
        """Executes iterative knapsack rounds with regret-based proposals."""
        nodes = self.graph.get_nodes()
        rem_cap: Dict[int, int] = {n: int(self.graph.get_capacity(n)) for n in nodes}
        unplaced: Set[str] = {t.task_id for t in self.tasks}
        assignments: Dict[str, int] = {}

        # Precompute costs for all (task, server)
        cost_cache: Dict[str, Dict[int, float]] = {}
        for task in sorted(self.tasks, key=lambda t: t.task_id):
            cost_cache[task.task_id] = {
                s: self._task_server_cost(task, s, dist_matrix, mst_dist_matrix, sync_hub)[2]
                for s in nodes
            }

        max_rounds = len(self.tasks) * 2
        for _ in range(max_rounds):
            if not unplaced:
                break

            # 1. Proposal Generation
            server_proposals: Dict[int, List[PlacementOption]] = {s: [] for s in nodes}
            proposals_count = 0

            for t_id in sorted(unplaced):
                task = self.task_map[t_id]
                # Feasible servers with room for task demand
                feasible = [s for s in nodes if rem_cap[s] >= task.demand]
                if not feasible:
                    continue

                # Sort feasible servers by cost ascending, tie-break by server id
                feasible.sort(key=lambda s: (cost_cache[t_id][s], s))
                best_server = feasible[0]
                best_cost = cost_cache[t_id][best_server]

                if len(feasible) >= 2:
                    next_best_server = feasible[1]
                    next_best_cost = cost_cache[t_id][next_best_server]
                    regret = next_best_cost - best_cost
                else:
                    # Sole feasible server remaining: high regret of losing final placement option
                    worst_cost = max(cost_cache[t_id].values())
                    regret = (worst_cost - best_cost) + 10.0

                benefit = max(0.01, round(regret, 4))
                server_proposals[best_server].append(
                    PlacementOption(
                        item_id=t_id,
                        cost=task.demand,
                        benefit=benefit,
                        metadata={"task": task, "best_server": best_server},
                    )
                )
                proposals_count += 1

            if proposals_count == 0:
                # No unplaced task can fit on any server
                break

            # 2. Server Selection via Knapsack
            round_accepted = 0
            for server in nodes:
                proposals = server_proposals[server]
                if not proposals:
                    continue

                cap = rem_cap[server]
                if use_dp:
                    result = knapsack_01_dp(proposals, cap)
                else:
                    result = greedy_placement_selection(proposals, cap)

                for item in result.selected_items:
                    t_id = str(item.item_id)
                    assignments[t_id] = server
                    rem_cap[server] -= item.cost
                    unplaced.remove(t_id)
                    round_accepted += 1

            if round_accepted == 0:
                # Deadlock: proposals made but none could be accepted
                break

        return assignments, sorted(unplaced)

    def _run_spillover_greedy(
        self,
        dist_matrix: Dict[int, Dict[int, float]],
        mst_dist_matrix: Dict[int, Dict[int, float]],
        sync_hub: int,
    ) -> Tuple[Dict[str, int], List[str]]:
        """Simple spill-over greedy: highest traffic first, best server with capacity."""
        nodes = self.graph.get_nodes()
        rem_cap: Dict[int, int] = {n: int(self.graph.get_capacity(n)) for n in nodes}
        assignments: Dict[str, int] = {}
        unplaced: List[str] = []

        # Sort tasks descending by client traffic, tie-break by task_id ascending
        sorted_tasks = sorted(self.tasks, key=lambda t: (-t.total_requests, t.task_id))

        for task in sorted_tasks:
            feasible = [s for s in nodes if rem_cap[s] >= task.demand]
            if not feasible:
                unplaced.append(task.task_id)
                continue

            # Pick feasible server with minimum composite cost, tie-break by server id
            best_server = min(
                feasible,
                key=lambda s: (self._task_server_cost(task, s, dist_matrix, mst_dist_matrix, sync_hub)[2], s),
            )
            assignments[task.task_id] = best_server
            rem_cap[best_server] -= task.demand

        return assignments, sorted(unplaced)

    def _run_random_placement(
        self,
        dist_matrix: Dict[int, Dict[int, float]],
        mst_dist_matrix: Dict[int, Dict[int, float]],
        sync_hub: int,
        seed: int = 42,
    ) -> Tuple[Dict[str, int], List[str]]:
        """Random placement: assigns each task to a randomly chosen feasible server."""
        rng = random.Random(seed)
        nodes = self.graph.get_nodes()
        rem_cap: Dict[int, int] = {n: int(self.graph.get_capacity(n)) for n in nodes}
        assignments: Dict[str, int] = {}
        unplaced: List[str] = []

        tasks_shuffled = sorted(self.tasks, key=lambda t: t.task_id)
        rng.shuffle(tasks_shuffled)

        for task in tasks_shuffled:
            feasible = [s for s in nodes if rem_cap[s] >= task.demand]
            if not feasible:
                unplaced.append(task.task_id)
                continue

            chosen_server = rng.choice(feasible)
            assignments[task.task_id] = chosen_server
            rem_cap[chosen_server] -= task.demand

        return assignments, sorted(unplaced)

    def _run_unconstrained_lower_bound(
        self,
        dist_matrix: Dict[int, Dict[int, float]],
        mst_dist_matrix: Dict[int, Dict[int, float]],
        sync_hub: int,
    ) -> Tuple[Dict[str, int], List[str]]:
        """Unconstrained lower bound: places every task on its globally optimal server, ignoring capacity."""
        nodes = self.graph.get_nodes()
        assignments: Dict[str, int] = {}

        for task in sorted(self.tasks, key=lambda t: t.task_id):
            best_server = min(
                nodes,
                key=lambda s: (self._task_server_cost(task, s, dist_matrix, mst_dist_matrix, sync_hub)[2], s),
            )
            assignments[task.task_id] = best_server

        return assignments, []

    def solve_brute_force_assignment(
        self,
        dist_matrix: Dict[int, Dict[int, float]],
        mst_dist_matrix: Dict[int, Dict[int, float]],
        sync_hub: int,
    ) -> Optional[StrategyMetrics]:
        """Exhaustive brute-force assignment solver for tiny benchmark instances (<= 7 tasks, <= 6 servers)."""
        nodes = self.graph.get_nodes()
        sorted_tasks = sorted(self.tasks, key=lambda t: t.task_id)
        k = len(sorted_tasks)
        m = len(nodes)

        # Guard against combinatorial explosion
        options = nodes + [None]
        if (len(options) ** k) > 300_000:
            return None

        capacities = {s: int(self.graph.get_capacity(s)) for s in nodes}
        cost_lookup = [
            {s: self._task_server_cost(sorted_tasks[i], s, dist_matrix, mst_dist_matrix, sync_hub)[2] for s in nodes}
            for i in range(k)
        ]
        demands = [sorted_tasks[i].demand for i in range(k)]

        best_assignment: Dict[str, int] = {}
        best_placed_count = -1
        best_objective = float("inf")

        # Iterate over all (m+1)^k candidate assignment mappings
        for combo in itertools.product(options, repeat=k):
            used_cap: Dict[int, int] = {s: 0 for s in nodes}
            placed_count = 0
            total_comp = 0.0
            feasible = True

            for i, server in enumerate(combo):
                if server is not None:
                    used_cap[server] += demands[i]
                    if used_cap[server] > capacities[server]:
                        feasible = False
                        break
                    placed_count += 1
                    total_comp += cost_lookup[i][server]

            if not feasible:
                continue

            if placed_count > best_placed_count or (placed_count == best_placed_count and total_comp < best_objective):
                best_placed_count = placed_count
                best_objective = total_comp
                best_assignment = {sorted_tasks[i].task_id: combo[i] for i in range(k) if combo[i] is not None}

        unplaced = [t.task_id for t in sorted_tasks if t.task_id not in best_assignment]
        return self._evaluate_assignments(
            strategy_name="brute_force_optimal",
            assignments=best_assignment,
            unplaced_ids=unplaced,
            dist_matrix=dist_matrix,
            mst_dist_matrix=mst_dist_matrix,
            sync_hub=sync_hub,
        )

    def optimize(self) -> OptimizerReport:
        """Runs all placement strategies, evaluations, and metrics reporting."""
        nodes = self.graph.get_nodes()

        # 1. MST Backbone & Weighted Median Hub
        mst_edges, mst_weight, sync_hub, mst_dist, avg_sync_latency = self._compute_mst_and_hub()

        # 2. APSP Shortest Path Routing Table
        dist_matrix, pred_matrix = floyd_warshall(self.graph)
        routing_table: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for u in nodes:
            for v in nodes:
                routing_table[(u, v)] = {
                    "path": reconstruct_apsp_path(pred_matrix, u, v),
                    "latency": dist_matrix[u][v],
                }

        # 3. Execute all Placement Strategies
        strategy_metrics: Dict[str, StrategyMetrics] = {}

        # 3a. Unconstrained Lower Bound
        asgn_lb, unp_lb = self._run_unconstrained_lower_bound(dist_matrix, mst_dist, sync_hub)
        strategy_metrics["unconstrained_lower_bound"] = self._evaluate_assignments(
            "unconstrained_lower_bound", asgn_lb, unp_lb, dist_matrix, mst_dist, sync_hub
        )

        # 3b. Iterative Knapsack DP (Primary)
        asgn_dp, unp_dp = self._run_iterative_knapsack(True, dist_matrix, mst_dist, sync_hub)
        dp_metrics = self._evaluate_assignments(
            "iterative_knapsack_dp", asgn_dp, unp_dp, dist_matrix, mst_dist, sync_hub
        )
        strategy_metrics["iterative_knapsack_dp"] = dp_metrics

        # 3c. Iterative Knapsack Greedy
        asgn_gr, unp_gr = self._run_iterative_knapsack(False, dist_matrix, mst_dist, sync_hub)
        gr_metrics = self._evaluate_assignments(
            "iterative_knapsack_greedy", asgn_gr, unp_gr, dist_matrix, mst_dist, sync_hub
        )
        strategy_metrics["iterative_knapsack_greedy"] = gr_metrics

        # 3d. Simple Spill-over Greedy
        asgn_spill, unp_spill = self._run_spillover_greedy(dist_matrix, mst_dist, sync_hub)
        strategy_metrics["spillover_greedy"] = self._evaluate_assignments(
            "spillover_greedy", asgn_spill, unp_spill, dist_matrix, mst_dist, sync_hub
        )

        # 3e. Random Feasible Placement
        asgn_rand, unp_rand = self._run_random_placement(dist_matrix, mst_dist, sync_hub)
        strategy_metrics["random_placement"] = self._evaluate_assignments(
            "random_placement", asgn_rand, unp_rand, dist_matrix, mst_dist, sync_hub
        )

        # 3f. Brute-Force Assignment (if tiny instance)
        bf_metrics = self.solve_brute_force_assignment(dist_matrix, mst_dist, sync_hub)
        if bf_metrics:
            strategy_metrics["brute_force_optimal"] = bf_metrics

        # 4. Compile Detailed DP Reports & Tables
        server_summaries: List[ServerPlacementSummary] = []
        cost_benefit_table: List[PlacementDecision] = []

        server_alloc: Dict[int, List[str]] = {n: [] for n in nodes}
        for t_id, s in sorted(asgn_dp.items()):
            server_alloc[s].append(t_id)

        for s in nodes:
            placed = server_alloc[s]
            used_c = sum(self.task_map[tid].demand for tid in placed)
            tot_c = int(self.graph.get_capacity(s))

            # Latency benefit relative to unconstrained/baseline
            total_ben = 0.0
            for tid in placed:
                task = self.task_map[tid]
                per_lat, _, _ = self._task_server_cost(task, s, dist_matrix, mst_dist, sync_hub)
                worst_lat = max(
                    self._task_server_cost(task, v, dist_matrix, mst_dist, sync_hub)[0]
                    for v in nodes
                )
                b_lat = round(worst_lat, 2)
                o_lat = round(per_lat, 2)
                d_lat = round(max(0.0, b_lat - o_lat), 2)
                tot_ben_t = d_lat * task.total_requests
                total_ben += tot_ben_t
                ratio = (d_lat / task.demand) if task.demand > 0 else 0.0

                cost_benefit_table.append(
                    PlacementDecision(
                        task_id=tid,
                        server_id=s,
                        demand_cost=task.demand,
                        baseline_latency=b_lat,
                        optimized_latency=o_lat,
                        latency_benefit=d_lat,
                        total_benefit=round(tot_ben_t, 2),
                        efficiency_ratio=round(ratio, 4),
                    )
                )

            server_summaries.append(
                ServerPlacementSummary(
                    server_id=s,
                    total_capacity=tot_c,
                    used_capacity=used_c,
                    placed_tasks=placed,
                    total_latency_benefit=round(total_ben, 2),
                )
            )

        # Baseline average latency across unconstrained placement or random
        rand_metrics = strategy_metrics["random_placement"]
        baseline_avg_lat = rand_metrics.average_access_latency or dp_metrics.average_access_latency
        dp_avg_lat = dp_metrics.average_access_latency
        reduction_pct = (
            round((baseline_avg_lat - dp_avg_lat) / baseline_avg_lat * 100.0, 2)
            if baseline_avg_lat > 0 else 0.0
        )

        greedy_avg_lat = gr_metrics.average_access_latency
        gr_reduction_pct = (
            round((baseline_avg_lat - greedy_avg_lat) / baseline_avg_lat * 100.0, 2)
            if baseline_avg_lat > 0 else 0.0
        )

        return OptimizerReport(
            mst_edges=mst_edges,
            mst_total_weight=round(mst_weight, 2),
            sync_hub_node=sync_hub,
            backbone_sync_latency=avg_sync_latency,
            routing_table=routing_table,
            strategy_metrics=strategy_metrics,
            server_summaries=server_summaries,
            cost_benefit_table=cost_benefit_table,
            unplaced_tasks=unp_dp,
            baseline_average_latency=round(baseline_avg_lat, 2),
            optimized_average_latency=round(dp_avg_lat, 2),
            latency_reduction_percent=reduction_pct,
            total_capacity_utilization=dp_metrics.fleet_utilization_pct,
            greedy_optimized_latency=round(greedy_avg_lat, 2),
            greedy_latency_reduction_percent=gr_reduction_pct,
        )
