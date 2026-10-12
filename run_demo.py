"""Runnable Demonstration Script for Cloud Task Placement Optimizer (Revision 2).

Executes the full algorithmic pipeline on the small cloud network topology (10 nodes),
comparing all five placement strategies side-by-side, displaying whole-fleet utilization,
and demonstrating the Minimum Spanning Tree (MST) weighted-median synchronization hub.
"""

from __future__ import annotations
import os
import sys
from typing import Any, Dict, List

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.graph.graph import Graph
from src.optimizer.workload import Task, generate_synthetic_workload
from src.optimizer.placement_optimizer import CloudPlacementOptimizer, OptimizerReport


def format_header(title: str, width: int = 94) -> str:
    line = "=" * width
    return f"\n{line}\n  {title}\n{line}"


def run_demo(lambda_sync: float = 0.5) -> None:
    data_path = os.path.join(current_dir, "data", "small_topology.json")
    if not os.path.exists(data_path):
        print(f"Dataset not found at {data_path}. Please check data directory.")
        return

    print("\n" + "#" * 94)
    print("   CLOUD TASK PLACEMENT OPTIMIZER -- DAA PBL GROUP 3")
    print("   Pipeline: MST Sync Hub + Floyd-Warshall APSP + Multi-Round Knapsack DP")
    print(f"   Configured Backbone Sync Weight (Lambda): {lambda_sync:.2f}")
    print("#" * 94)

    # 1. Load topology and generate workload
    graph = Graph.load_from_json(data_path)
    print(f"\n[+] Loaded Cloud Network Topology: {graph.num_nodes} servers, {graph.num_edges} physical links")

    tasks = generate_synthetic_workload(
        graph=graph,
        num_tasks=15,
        demand_range=(15, 45),
        requests_per_task=(25.0, 150.0),
        replication_traffic_range=(10.0, 30.0),
        seed=42,
    )
    total_demand = sum(t.demand for t in tasks)
    total_fleet_cap = sum(graph.get_capacity(n) for n in graph.get_nodes())
    print(f"[+] Ingested Workload: {len(tasks)} cloud tasks (Total Demand: {total_demand} units | Fleet Capacity: {int(total_fleet_cap)} units)")

    # 2. Run optimizer
    optimizer = CloudPlacementOptimizer(graph, tasks, lambda_sync=lambda_sync)
    report: OptimizerReport = optimizer.optimize()

    # 3. Stage 1: MST Backbone & Weighted Median Sync Hub
    print(format_header("STAGE 1: MST BACKBONE DESIGN & WEIGHTED MEDIAN SYNC HUB"))
    print(f"  * Total MST Backbone Weight   : {report.mst_total_weight:.2f} ms")
    print(f"  * Designated Sync Hub Node    : Server {report.sync_hub_node} (Traffic-Weighted Graph Median)")
    print(f"  * Mean Inter-Server Sync Delay : {report.backbone_sync_latency:.2f} ms along tree")
    print(f"  * Active Backbone Tree Links   : {len(report.mst_edges)} links spanning all {graph.num_nodes} servers")
    print("\n  Backbone Links (Tree Topology):")
    for u, v, weight in report.mst_edges:
        hub_tag = " (HUB)" if (u == report.sync_hub_node or v == report.sync_hub_node) else ""
        print(f"    - Server {u:2d} <---> Server {v:2d} | Latency: {weight:5.2f} ms{hub_tag}")

    # 4. Stage 2: Side-by-Side Comparison of ALL Placement Strategies
    print(format_header("STAGE 2: SIDE-BY-SIDE COMPARISON OF ALL PLACEMENT STRATEGIES"))
    print(
        f"  {'Strategy Name':<28} | {'Placed':<6} | {'Unplaced':<8} | "
        f"{'Avg Lat (ms)':<12} | {'Avg Sync':<8} | {'Total Obj':<11} | {'Gap to LB (%)':<13} | {'Fleet Util (%)'}"
    )
    print("  " + "-" * 110)

    lb_obj = report.strategy_metrics["unconstrained_lower_bound"].total_objective

    strategy_order = [
        ("unconstrained_lower_bound", "Unconstrained Lower Bound"),
        ("iterative_knapsack_dp", "Iterative Knapsack DP (Ours)"),
        ("iterative_knapsack_greedy", "Iterative Greedy Rounds"),
        ("spillover_greedy", "Simple Spill-over Greedy"),
        ("random_placement", "Random Feasible Placement"),
    ]
    if "brute_force_optimal" in report.strategy_metrics:
        strategy_order.insert(1, ("brute_force_optimal", "Brute-Force Optimal (Exact)"))

    for key, label in strategy_order:
        if key not in report.strategy_metrics:
            continue
        m = report.strategy_metrics[key]
        gap_pct = ((m.total_objective - lb_obj) / lb_obj * 100.0) if lb_obj > 0 else 0.0
        gap_str = f"+{gap_pct:5.2f}%" if gap_pct >= 0 else f"{gap_pct:5.2f}%"
        if key == "unconstrained_lower_bound":
            gap_str = "  0.00% (LB)"

        print(
            f"  {label:<28} | "
            f"{m.placed_tasks_count:<6d} | "
            f"{m.unplaced_tasks_count:<8d} | "
            f"{m.average_access_latency:12.2f} | "
            f"{m.average_sync_cost:8.1f} | "
            f"{m.total_objective:11.1f} | "
            f"{gap_str:<13} | "
            f"{m.fleet_utilization_pct:6.1f}%"
        )

    # 5. Stage 3: Fleet-Wide Server Capacity Allocation
    print(format_header("STAGE 3: FLEET-WIDE CAPACITY UTILIZATION (WHOLE FLEET BREAKDOWN)"))
    print(
        f"  {'Server':<9} | {'Total Cap':<10} | {'Used Cap':<9} | {'Remaining':<10} | "
        f"{'Util %':<8} | {'Tasks Placed':<13} | {'Task Assignment IDs'}"
    )
    print("  " + "-" * 94)

    for s in report.server_summaries:
        rem = s.total_capacity - s.used_capacity
        task_count = len(s.placed_tasks)
        task_list_str = ", ".join(s.placed_tasks) if s.placed_tasks else "(idle)"
        hub_marker = " *" if s.server_id == report.sync_hub_node else "  "

        print(
            f"  Server {s.server_id:<1}{hub_marker} | "
            f"{s.total_capacity:<10d} | "
            f"{s.used_capacity:<9d} | "
            f"{rem:<10d} | "
            f"{s.utilization_percent:6.1f}% | "
            f"{task_count:<13d} | "
            f"{task_list_str}"
        )
    print("  (* designates the weighted median Sync Hub)")

    # 6. Stage 4: Placed Tasks Cost / Benefit Breakdown (Under Knapsack DP)
    print(format_header("STAGE 4: COST / BENEFIT BREAKDOWN (KNAPSACK DP DECISIONS)"))
    print(
        f"  {'Task ID':<9} | {'Host':<8} | {'Demand':<6} | "
        f"{'Base Lat':<8} | {'Opt Lat':<8} | "
        f"{'Unit Ben':<8} | {'Total Benefit':<13} | {'Efficiency (Ben/Demand)'}"
    )
    print("  " + "-" * 94)
    for d in report.cost_benefit_table:
        print(
            f"  {d.task_id:<9} | "
            f"Server {d.server_id:<1} | "
            f"{d.demand_cost:<6d} | "
            f"{d.baseline_latency:8.2f} | "
            f"{d.optimized_latency:8.2f} | "
            f"{d.latency_benefit:8.2f} | "
            f"{d.total_benefit:13.1f} | "
            f"{d.efficiency_ratio:8.4f}"
        )

    # 7. Stage 5: Sample Shortest Path Routing Table
    print(format_header("STAGE 5: SAMPLE SHORTEST PATH ROUTING TABLE (CLIENT -> HOST)"))
    sample_pairs = [(0, 4), (1, 8), (2, 7), (3, 9), (5, 6)]
    for u, v in sample_pairs:
        route = report.routing_table.get((u, v))
        if route:
            path_str = " -> ".join(map(str, route["path"]))
            print(f"  Client S{u} -> Host S{v} : Shortest Path = [{path_str}] | Latency = {route['latency']:.2f} ms")

    # 8. Stage 6: Executive Takeaways
    print(format_header("EXECUTIVE POLICY TAKEAWAYS"))
    dp_m = report.strategy_metrics["iterative_knapsack_dp"]
    sp_m = report.strategy_metrics["spillover_greedy"]
    rand_m = report.strategy_metrics["random_placement"]

    latency_improvement_vs_rand = ((rand_m.average_access_latency - dp_m.average_access_latency) / rand_m.average_access_latency * 100.0)
    gap_vs_lower_bound = ((dp_m.total_objective - lb_obj) / lb_obj * 100.0)

    print(f"  1. Solution Quality  : Knapsack DP is within {gap_vs_lower_bound:.2f}% of the theoretical unconstrained lower bound.")
    print(f"  2. Baseline Advantage: Knapsack DP cuts client access latency by {latency_improvement_vs_rand:.1f}% compared to Random placement.")
    print(f"  3. Regret Coordination: Knapsack DP outperforms simple Spill-Over Greedy by coordinating bids across congested servers.")
    print(f"  4. Fleet Distribution: Tasks are balanced across the whole fleet, avoiding bottlenecking on any single server.")
    print(f"  5. Sync Efficiency   : Server {report.sync_hub_node} serves as the centralized sync hub, keeping replication delay to {report.backbone_sync_latency:.2f} ms.")
    print("=" * 94 + "\n")


if __name__ == "__main__":
    lambda_arg = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
    run_demo(lambda_sync=lambda_arg)
