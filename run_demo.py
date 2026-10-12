"""Runnable Demonstration Script for Cloud Task Placement Optimizer.

Executes the full algorithmic pipeline on the small cloud network topology (10 nodes)
and outputs structured policy recommendations, routing tables, and cost/benefit breakdowns.
"""

import os
import sys

# Ensure src is in Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.graph.graph import Graph
from src.optimizer.workload import generate_synthetic_workload
from src.optimizer.placement_optimizer import CloudPlacementOptimizer


def format_table_header(title: str, width: int = 86) -> str:
    line = "=" * width
    return f"\n{line}\n  {title}\n{line}"


def run_demo() -> None:
    data_path = os.path.join(current_dir, "data", "small_topology.json")
    if not os.path.exists(data_path):
        print(f"Dataset not found at {data_path}. Please run generate_datasets.py first.")
        return

    print("\n" + "#" * 86)
    print("   CLOUD TASK PLACEMENT OPTIMIZER (DAA PBL GROUP 3)")
    print("   Algorithms: MST (Backbone) + APSP (Routing) + 0-1 Knapsack DP (Placement)")
    print("#" * 86)

    # 1. Load topology and generate workload
    graph = Graph.load_from_json(data_path)
    print(f"\n[+] Loaded Cloud Network Topology: {graph.num_nodes} servers, {graph.num_edges} links")

    tasks = generate_synthetic_workload(
        graph=graph,
        num_tasks=15,
        demand_range=(15, 45),
        requests_per_task=(25.0, 150.0),
        seed=42,
    )
    print(f"[+] Ingested Workload: {len(tasks)} service tasks/VMs with client request profiles")

    # 2. Run the optimizer
    optimizer = CloudPlacementOptimizer(graph, tasks)
    report = optimizer.optimize()

    # 3. Print MST Backbone Summary
    print(format_table_header("STAGE 1: MINIMUM SPANNING TREE (MST) BACKBONE DESIGN"))
    print(f"Total Backbone Tree Weight : {report.mst_total_weight:.2f} ms")
    print(f"Mean Inter-Server Sync Delay: {report.backbone_sync_latency:.2f} ms across backbone")
    print(f"Number of Backbone Links    : {len(report.mst_edges)}")
    print("\nBackbone Links:")
    for u, v, weight in report.mst_edges:
        print(f"  * Server {u:2d} <---> Server {v:2d}  (Link Latency: {weight:5.2f} ms)")

    # 4. Print Server Placement & Capacity Summary
    print(format_table_header("STAGE 2 & 3: SERVER PLACEMENTS & CAPACITY ALLOCATION (0-1 KNAPSACK DP)"))
    print(f"{'Server':<8} | {'Capacity':<10} | {'Used':<8} | {'Util %':<8} | {'Latency Benefit':<16} | {'Placed Tasks'}")
    print("-" * 86)
    for s in report.server_summaries:
        tasks_str = ", ".join(s.placed_tasks) if s.placed_tasks else "(idle)"
        print(
            f"Server {s.server_id:<1} | "
            f"{s.total_capacity:<10} | "
            f"{s.used_capacity:<8} | "
            f"{s.utilization_percent:6.1f}% | "
            f"{s.total_latency_benefit:13.2f} ms | "
            f"{tasks_str}"
        )

    # 5. Print Cost / Benefit Table
    print(format_table_header("STAGE 4: COST / BENEFIT TABLE (PER TASK PLACEMENT)"))
    print(
        f"{'Task ID':<8} | {'Host':<5} | {'Cost':<5} | "
        f"{'Base Lat':<8} | {'Opt Lat':<8} | "
        f"{'Unit Ben':<8} | {'Total Benefit':<13} | {'Efficiency'}"
    )
    print("-" * 86)
    for d in report.cost_benefit_table:
        print(
            f"{d.task_id:<8} | "
            f"Svr {d.server_id:<1} | "
            f"{d.demand_cost:<5} | "
            f"{d.baseline_latency:8.2f} | "
            f"{d.optimized_latency:8.2f} | "
            f"{d.latency_benefit:8.2f} | "
            f"{d.total_benefit:13.1f} | "
            f"{d.efficiency_ratio:8.4f}"
        )

    # 6. Sample Routing Table
    print(format_table_header("STAGE 5: SAMPLE SHORTEST PATH ROUTING TABLE (CLIENT -> HOST)"))
    sample_pairs = [(0, 4), (1, 8), (2, 7), (3, 9), (5, 6)]
    for u, v in sample_pairs:
        route = report.routing_table.get((u, v))
        if route:
            path_str = " -> ".join(map(str, route["path"]))
            print(f"  Client {u} -> Host {v} : Path = [{path_str}] | Latency = {route['latency']:.2f} ms")

    # 7. Executive System Metrics & Policy Comparison
    print(format_table_header("EXECUTIVE POLICY RECOMMENDATIONS & PERFORMANCE METRICS"))
    print(f"Baseline Average Client Latency    : {report.baseline_average_latency:.2f} ms")
    print(f"Greedy Baseline Average Latency    : {report.greedy_optimized_latency:.2f} ms ({report.greedy_latency_reduction_percent:.1f}% reduction)")
    print(f"Optimal DP Average Client Latency  : {report.optimized_average_latency:.2f} ms ({report.latency_reduction_percent:.1f}% reduction)")
    print(f"Fleet-Wide Capacity Utilization    : {report.total_capacity_utilization:.1f}%")
    print(f"Total Tasks Placed vs Ingested     : {len(report.cost_benefit_table)} / {len(tasks)}")
    print(f"Backbone Inter-Replica Sync Delay  : {report.backbone_sync_latency:.2f} ms")
    print("=" * 86 + "\n")


if __name__ == "__main__":
    run_demo()
