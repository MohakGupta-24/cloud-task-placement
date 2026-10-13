"""Comprehensive Experimental Suite for Cloud Task Placement PBL (Revision 2).

Conducts empirical benchmarking, sensitivity analysis, and solution quality evaluations:
1. Runtime Benchmarks (10 repeats on fixed graphs, reporting mean and std):
   - MST: Kruskal vs Prim (sparse density 0.20 and dense density 0.80).
   - SSSP: Dijkstra vs Bellman-Ford across |V|.
   - APSP: Floyd-Warshall vs Repeated Dijkstra (sparse 0.20 and dense 0.80).
2. Placement Experiments (10 random seeds per condition, reporting mean and std):
   - Capacity Multiplier sweep (0.25x to 2.0x).
   - Task Count sweep (15 to 75 tasks).
   - Graph Size (|V| in 15 to 75) and Edge Density (0.15 to 0.85) sweeps.
   - Lambda (sync weight) sweep (0.0, 0.5, 1.0, 2.0).
   - Strategies compared:
       * random_placement ("random")
       * spillover_greedy ("spill-over greedy")
       * iterative_knapsack_dp ("knapsack-rounds DP")
       * iterative_knapsack_greedy ("greedy-rounds")
       * unconstrained_lower_bound ("unconstrained lower bound")
   - Gap to unconstrained lower bound reported for every strategy.
3. Saves CSV tables and high-resolution Matplotlib figures with error bars:
   - experiments/results/runtime_vs_size.png
   - experiments/results/latency_vs_capacity.png
   - experiments/results/placement_sensitivity_tasks.png
   - experiments/results/placement_sensitivity_lambda.png
   - experiments/results/mst_backbone_topology.png
"""

from __future__ import annotations
import csv
import os
import statistics
import sys
import time
from typing import Any, Dict, List, Tuple

# Headless matplotlib backend for non-interactive rendering
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.graph.graph import Graph
from src.graph.generator import generate_cloud_topology
from src.mst.kruskal import kruskal_mst
from src.mst.prim import prim_mst
from src.shortest_paths.dijkstra import dijkstra
from src.shortest_paths.bellman_ford import bellman_ford
from src.shortest_paths.floyd_warshall import floyd_warshall
from src.optimizer.workload import generate_synthetic_workload
from src.optimizer.placement_optimizer import CloudPlacementOptimizer

RESULTS_DIR = os.path.join(current_dir, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Helper for mean and std
def stats(vals: List[float]) -> Tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    m = statistics.mean(vals)
    s = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return round(m, 3), round(s, 3)


# ==============================================================================
# 1. RUNTIME BENCHMARKS (MST, SSSP, APSP)
# ==============================================================================

def benchmark_mst(
    sizes: List[int],
    density_sparse: float = 0.20,
    density_dense: float = 0.80,
    repeats: int = 10,
) -> List[Dict[str, Any]]:
    """Benchmarks Kruskal vs Prim on fixed topologies with repeats."""
    print("\n--- Running MST Benchmark: Kruskal vs Prim (10 repeats, sparse vs dense) ---")
    results = []

    for n in sizes:
        for dens, tag in [(density_sparse, "sparse"), (density_dense, "dense")]:
            g = generate_cloud_topology(
                num_nodes=n,
                edge_density=dens,
                latency_range=(1.0, 50.0),
                seed=42,
                ensure_connected=True,
            )

            kruskal_times, prim_times = [], []
            for _ in range(repeats):
                t0 = time.perf_counter()
                kruskal_mst(g)
                kruskal_times.append((time.perf_counter() - t0) * 1000.0)

                t0 = time.perf_counter()
                prim_mst(g)
                prim_times.append((time.perf_counter() - t0) * 1000.0)

            k_mean, k_std = stats(kruskal_times)
            p_mean, p_std = stats(prim_times)

            row = {
                "num_nodes": n,
                "num_edges": g.num_edges,
                "density": dens,
                "graph_type": tag,
                "kruskal_mean_ms": k_mean,
                "kruskal_std_ms": k_std,
                "prim_mean_ms": p_mean,
                "prim_std_ms": p_std,
            }
            results.append(row)
            print(
                f"  |V|={n:3d}, {tag:6s} (|E|={g.num_edges:4d}) | "
                f"Kruskal: {k_mean:6.3f} ± {k_std:5.3f} ms | "
                f"Prim: {p_mean:6.3f} ± {p_std:5.3f} ms"
            )

    csv_path = os.path.join(RESULTS_DIR, "mst_runtime_comparison.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {csv_path}")
    return results


def benchmark_sssp(
    sizes: List[int],
    density: float = 0.20,
    repeats: int = 10,
) -> List[Dict[str, Any]]:
    """Benchmarks Dijkstra vs Bellman-Ford on fixed topologies with repeats."""
    print("\n--- Running SSSP Benchmark: Dijkstra vs Bellman-Ford (10 repeats) ---")
    results = []

    for n in sizes:
        g = generate_cloud_topology(
            num_nodes=n,
            edge_density=density,
            latency_range=(1.0, 50.0),
            seed=42,
            ensure_connected=True,
        )

        dijk_times, bf_times = [], []
        for _ in range(repeats):
            t0 = time.perf_counter()
            dijkstra(g, source=0)
            dijk_times.append((time.perf_counter() - t0) * 1000.0)

            t0 = time.perf_counter()
            bellman_ford(g, source=0)
            bf_times.append((time.perf_counter() - t0) * 1000.0)

        d_mean, d_std = stats(dijk_times)
        bf_mean, bf_std = stats(bf_times)

        row = {
            "num_nodes": n,
            "num_edges": g.num_edges,
            "density": density,
            "dijkstra_mean_ms": d_mean,
            "dijkstra_std_ms": d_std,
            "bellman_ford_mean_ms": bf_mean,
            "bellman_ford_std_ms": bf_std,
            "speedup_ratio": round(bf_mean / d_mean, 2) if d_mean > 0 else 0.0,
        }
        results.append(row)
        print(
            f"  |V|={n:3d}, |E|={g.num_edges:4d} | "
            f"Dijkstra: {d_mean:6.3f} ± {d_std:5.3f} ms | "
            f"Bellman-Ford: {bf_mean:7.3f} ± {bf_std:5.3f} ms | "
            f"Speedup: {row['speedup_ratio']}x"
        )

    csv_path = os.path.join(RESULTS_DIR, "sssp_runtime_comparison.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {csv_path}")
    return results


def benchmark_apsp(
    sizes: List[int],
    density_sparse: float = 0.20,
    density_dense: float = 0.80,
    repeats: int = 10,
) -> List[Dict[str, Any]]:
    """Benchmarks Floyd-Warshall vs Repeated Dijkstra on sparse vs dense graphs."""
    print("\n--- Running APSP Benchmark: Floyd-Warshall vs Repeated Dijkstra (10 repeats) ---")
    results = []

    for n in sizes:
        for dens, tag in [(density_sparse, "sparse"), (density_dense, "dense")]:
            g = generate_cloud_topology(
                num_nodes=n,
                edge_density=dens,
                latency_range=(1.0, 50.0),
                seed=42,
                ensure_connected=True,
            )

            fw_times, rep_dijk_times = [], []
            for _ in range(repeats):
                t0 = time.perf_counter()
                floyd_warshall(g)
                fw_times.append((time.perf_counter() - t0) * 1000.0)

                t0 = time.perf_counter()
                for s in g.get_nodes():
                    dijkstra(g, source=s)
                rep_dijk_times.append((time.perf_counter() - t0) * 1000.0)

            fw_mean, fw_std = stats(fw_times)
            rd_mean, rd_std = stats(rep_dijk_times)

            row = {
                "num_nodes": n,
                "num_edges": g.num_edges,
                "density": dens,
                "graph_type": tag,
                "floyd_warshall_mean_ms": fw_mean,
                "floyd_warshall_std_ms": fw_std,
                "repeated_dijkstra_mean_ms": rd_mean,
                "repeated_dijkstra_std_ms": rd_std,
                "fw_to_rep_dijk_ratio": round(fw_mean / rd_mean, 2) if rd_mean > 0 else 0.0,
            }
            results.append(row)
            print(
                f"  |V|={n:3d}, {tag:6s} (|E|={g.num_edges:4d}) | "
                f"FW: {fw_mean:7.3f} ± {fw_std:5.3f} ms | "
                f"RepDijkstra: {rd_mean:7.3f} ± {rd_std:5.3f} ms | "
                f"Ratio: {row['fw_to_rep_dijk_ratio']}x"
            )

    csv_path = os.path.join(RESULTS_DIR, "apsp_runtime_comparison.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {csv_path}")
    return results


# ==============================================================================
# 2. PLACEMENT EXPERIMENTS OVER 10 SEEDS
# ==============================================================================

STRATEGIES = [
    "unconstrained_lower_bound",
    "iterative_knapsack_dp",
    "iterative_knapsack_greedy",
    "spillover_greedy",
    "random_placement",
]

def run_placement_trial(
    graph: Graph,
    tasks: List[Any],
    lambda_sync: float = 0.5,
) -> Dict[str, Dict[str, float]]:
    """Runs optimizer on one instance and extracts standardized metrics for all 5 strategies."""
    opt = CloudPlacementOptimizer(graph, tasks, lambda_sync=lambda_sync)
    report = opt.optimize()

    out: Dict[str, Dict[str, float]] = {}
    lb_metrics = report.strategy_metrics["unconstrained_lower_bound"]
    lb_obj = lb_metrics.total_objective
    lb_lat = lb_metrics.average_access_latency

    for s in STRATEGIES:
        m = report.strategy_metrics[s]
        gap_obj = ((m.total_objective - lb_obj) / lb_obj * 100.0) if lb_obj > 0 else 0.0
        gap_lat = ((m.average_access_latency - lb_lat) / lb_lat * 100.0) if lb_lat > 0 else 0.0
        out[s] = {
            "access_latency": m.average_access_latency,
            "sync_cost": m.average_sync_cost,
            "total_objective": m.total_objective,
            "fleet_utilization_pct": m.fleet_utilization_pct,
            "unplaced_tasks_count": float(m.unplaced_tasks_count),
            "gap_to_lb_obj_pct": gap_obj,
            "gap_to_lb_lat_pct": gap_lat,
        }
    return out


def benchmark_placement_capacity(
    multipliers: List[float],
    num_seeds: int = 10,
    base_n: int = 30,
    num_tasks: int = 35,
    lambda_sync: float = 0.5,
) -> List[Dict[str, Any]]:
    """Evaluates placement performance across capacity multipliers (0.25x - 2.0x) over 10 seeds."""
    print(f"\n--- Running Placement Capacity Sweep (0.25x - 2.0x, {num_seeds} seeds) ---")
    results = []

    for mult in multipliers:
        strat_data: Dict[str, Dict[str, List[float]]] = {
            s: {k: [] for k in ["access_latency", "sync_cost", "total_objective", "fleet_utilization_pct", "unplaced_tasks_count", "gap_to_lb_obj_pct", "gap_to_lb_lat_pct"]}
            for s in STRATEGIES
        }

        for seed_idx in range(num_seeds):
            seed = 100 + seed_idx
            raw_g = generate_cloud_topology(base_n, 0.25, (1.0, 50.0), (50.0, 200.0), seed=seed)
            tasks = generate_synthetic_workload(raw_g, num_tasks=num_tasks, demand_range=(20, 60), seed=seed)

            # Scale graph capacity by multiplier
            scaled_g = Graph(directed=False)
            for n in raw_g.get_nodes():
                scaled_g.add_node(n, capacity=max(1, int(raw_g.get_capacity(n) * mult)))
            for u, v, w in raw_g.get_edges():
                scaled_g.add_edge(u, v, latency=w)

            trial_metrics = run_placement_trial(scaled_g, tasks, lambda_sync=lambda_sync)
            for s in STRATEGIES:
                for k in strat_data[s]:
                    strat_data[s][k].append(trial_metrics[s][k])

        row: Dict[str, Any] = {"capacity_multiplier": mult}
        for s in STRATEGIES:
            for metric_key in ["access_latency", "total_objective", "gap_to_lb_obj_pct", "gap_to_lb_lat_pct", "unplaced_tasks_count", "fleet_utilization_pct"]:
                m_val, s_val = stats(strat_data[s][metric_key])
                row[f"{s}_{metric_key}_mean"] = m_val
                row[f"{s}_{metric_key}_std"] = s_val

        results.append(row)
        print(
            f"  Mult {mult:4.2f}x | "
            f"DP Gap: {row['iterative_knapsack_dp_gap_to_lb_obj_pct_mean']:5.2f}% ± {row['iterative_knapsack_dp_gap_to_lb_obj_pct_std']:4.2f}% | "
            f"Greedy Gap: {row['iterative_knapsack_greedy_gap_to_lb_obj_pct_mean']:5.2f}% | "
            f"Spill Gap: {row['spillover_greedy_gap_to_lb_obj_pct_mean']:5.2f}% | "
            f"Rand Gap: {row['random_placement_gap_to_lb_obj_pct_mean']:5.2f}% | "
            f"DP Unplaced: {row['iterative_knapsack_dp_unplaced_tasks_count_mean']:.1f}"
        )

    # Save to CSV
    csv_path = os.path.join(RESULTS_DIR, "placement_capacity_sensitivity.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {csv_path}")

    # Also save primary placement_comparison.csv for backward compatibility
    csv_compat = os.path.join(RESULTS_DIR, "placement_comparison.csv")
    compat_rows = []
    for r in results:
        compat_rows.append({
            "capacity_multiplier": r["capacity_multiplier"],
            "lower_bound_obj_mean": r["unconstrained_lower_bound_total_objective_mean"],
            "dp_obj_mean": r["iterative_knapsack_dp_total_objective_mean"],
            "dp_obj_std": r["iterative_knapsack_dp_total_objective_std"],
            "dp_gap_pct_mean": r["iterative_knapsack_dp_gap_to_lb_obj_pct_mean"],
            "dp_gap_pct_std": r["iterative_knapsack_dp_gap_to_lb_obj_pct_std"],
            "greedy_gap_pct_mean": r["iterative_knapsack_greedy_gap_to_lb_obj_pct_mean"],
            "spillover_gap_pct_mean": r["spillover_greedy_gap_to_lb_obj_pct_mean"],
            "random_gap_pct_mean": r["random_placement_gap_to_lb_obj_pct_mean"],
            "dp_fleet_utilization_mean": r["iterative_knapsack_dp_fleet_utilization_pct_mean"],
            "dp_unplaced_tasks_mean": r["iterative_knapsack_dp_unplaced_tasks_count_mean"],
        })
    with open(csv_compat, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=compat_rows[0].keys())
        writer.writeheader()
        writer.writerows(compat_rows)
    print(f"Saved: {csv_compat}")

    return results


def benchmark_placement_num_tasks(
    task_counts: List[int],
    num_seeds: int = 10,
    base_n: int = 30,
    lambda_sync: float = 0.5,
) -> List[Dict[str, Any]]:
    """Evaluates placement performance as task count varies over 10 seeds."""
    print(f"\n--- Running Task Count Sensitivity Sweep ({num_seeds} seeds) ---")
    results = []

    for k in task_counts:
        strat_data = {
            s: {"total_objective": [], "gap_to_lb_obj_pct": [], "unplaced_tasks_count": []}
            for s in STRATEGIES
        }

        for seed_idx in range(num_seeds):
            seed = 200 + seed_idx
            g = generate_cloud_topology(base_n, 0.25, seed=seed)
            tasks = generate_synthetic_workload(g, num_tasks=k, seed=seed)
            trial = run_placement_trial(g, tasks, lambda_sync=lambda_sync)
            for s in STRATEGIES:
                strat_data[s]["total_objective"].append(trial[s]["total_objective"])
                strat_data[s]["gap_to_lb_obj_pct"].append(trial[s]["gap_to_lb_obj_pct"])
                strat_data[s]["unplaced_tasks_count"].append(trial[s]["unplaced_tasks_count"])

        row: Dict[str, Any] = {"num_tasks": k}
        for s in STRATEGIES:
            row[f"{s}_obj_mean"], row[f"{s}_obj_std"] = stats(strat_data[s]["total_objective"])
            row[f"{s}_gap_mean"], row[f"{s}_gap_std"] = stats(strat_data[s]["gap_to_lb_obj_pct"])
            row[f"{s}_unplaced_mean"], _ = stats(strat_data[s]["unplaced_tasks_count"])

        results.append(row)
        print(
            f"  Tasks: {k:2d} | "
            f"DP Gap: {row['iterative_knapsack_dp_gap_mean']:5.2f}% ± {row['iterative_knapsack_dp_gap_std']:4.2f}% | "
            f"Greedy: {row['iterative_knapsack_greedy_gap_mean']:5.2f}% | "
            f"Spill: {row['spillover_greedy_gap_mean']:5.2f}% | "
            f"Rand: {row['random_placement_gap_mean']:5.2f}%"
        )

    csv_path = os.path.join(RESULTS_DIR, "placement_tasks_sensitivity.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {csv_path}")
    return results


def benchmark_placement_graph_size_and_density(
    sizes: List[int],
    densities: List[float],
    num_seeds: int = 10,
    num_tasks: int = 35,
    lambda_sync: float = 0.5,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Evaluates placement performance across graph sizes and edge densities."""
    print(f"\n--- Running Graph Size & Density Sweeps ({num_seeds} seeds) ---")
    size_results, density_results = [], []

    # 1. Size Sweep (fixed density 0.25)
    for n in sizes:
        strat_data = {s: {"total_objective": [], "gap_to_lb_obj_pct": []} for s in STRATEGIES}
        for seed_idx in range(num_seeds):
            seed = 300 + seed_idx
            g = generate_cloud_topology(n, 0.25, seed=seed)
            tasks = generate_synthetic_workload(g, num_tasks=num_tasks, seed=seed)
            trial = run_placement_trial(g, tasks, lambda_sync=lambda_sync)
            for s in STRATEGIES:
                strat_data[s]["total_objective"].append(trial[s]["total_objective"])
                strat_data[s]["gap_to_lb_obj_pct"].append(trial[s]["gap_to_lb_obj_pct"])

        row: Dict[str, Any] = {"num_nodes": n}
        for s in STRATEGIES:
            row[f"{s}_gap_mean"], row[f"{s}_gap_std"] = stats(strat_data[s]["gap_to_lb_obj_pct"])
        size_results.append(row)
        print(f"  |V|={n:2d} | DP Gap: {row['iterative_knapsack_dp_gap_mean']:5.2f}% ± {row['iterative_knapsack_dp_gap_std']:4.2f}% | Spill: {row['spillover_greedy_gap_mean']:5.2f}% | Rand: {row['random_placement_gap_mean']:5.2f}%")

    csv_size = os.path.join(RESULTS_DIR, "placement_graph_size_sensitivity.csv")
    with open(csv_size, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=size_results[0].keys())
        writer.writeheader()
        writer.writerows(size_results)
    print(f"Saved: {csv_size}")

    # 2. Density Sweep (fixed n = 30)
    for d in densities:
        strat_data = {s: {"total_objective": [], "gap_to_lb_obj_pct": []} for s in STRATEGIES}
        for seed_idx in range(num_seeds):
            seed = 400 + seed_idx
            g = generate_cloud_topology(30, d, seed=seed)
            tasks = generate_synthetic_workload(g, num_tasks=num_tasks, seed=seed)
            trial = run_placement_trial(g, tasks, lambda_sync=lambda_sync)
            for s in STRATEGIES:
                strat_data[s]["total_objective"].append(trial[s]["total_objective"])
                strat_data[s]["gap_to_lb_obj_pct"].append(trial[s]["gap_to_lb_obj_pct"])

        row = {"density": d}
        for s in STRATEGIES:
            row[f"{s}_gap_mean"], row[f"{s}_gap_std"] = stats(strat_data[s]["gap_to_lb_obj_pct"])
        density_results.append(row)
        print(f"  Density={d:4.2f} | DP Gap: {row['iterative_knapsack_dp_gap_mean']:5.2f}% ± {row['iterative_knapsack_dp_gap_std']:4.2f}% | Spill: {row['spillover_greedy_gap_mean']:5.2f}% | Rand: {row['random_placement_gap_mean']:5.2f}%")

    csv_density = os.path.join(RESULTS_DIR, "placement_density_sensitivity.csv")
    with open(csv_density, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=density_results[0].keys())
        writer.writeheader()
        writer.writerows(density_results)
    print(f"Saved: {csv_density}")

    return size_results, density_results


def benchmark_placement_lambda(
    lambdas: List[float],
    num_seeds: int = 10,
    base_n: int = 30,
    num_tasks: int = 35,
) -> List[Dict[str, Any]]:
    """Evaluates access latency vs MST sync cost trade-off across lambda weights."""
    lambda_str = ", ".join(f"{l}" for l in lambdas)
    print(f"\n--- Running Lambda Sensitivity Sweep ([{lambda_str}], {num_seeds} seeds) ---")
    results = []

    for lmb in lambdas:
        strat_data = {
            s: {"access_latency": [], "sync_cost": [], "total_objective": [], "gap_to_lb_obj_pct": []}
            for s in STRATEGIES
        }

        for seed_idx in range(num_seeds):
            seed = 500 + seed_idx
            g = generate_cloud_topology(base_n, 0.25, seed=seed)
            tasks = generate_synthetic_workload(g, num_tasks=num_tasks, seed=seed)
            trial = run_placement_trial(g, tasks, lambda_sync=lmb)
            for s in STRATEGIES:
                strat_data[s]["access_latency"].append(trial[s]["access_latency"])
                strat_data[s]["sync_cost"].append(trial[s]["sync_cost"])
                strat_data[s]["total_objective"].append(trial[s]["total_objective"])
                strat_data[s]["gap_to_lb_obj_pct"].append(trial[s]["gap_to_lb_obj_pct"])

        row: Dict[str, Any] = {"lambda_sync": lmb}
        for s in STRATEGIES:
            row[f"{s}_lat_mean"], row[f"{s}_lat_std"] = stats(strat_data[s]["access_latency"])
            row[f"{s}_sync_mean"], row[f"{s}_sync_std"] = stats(strat_data[s]["sync_cost"])
            row[f"{s}_obj_mean"], row[f"{s}_obj_std"] = stats(strat_data[s]["total_objective"])
            row[f"{s}_gap_mean"], row[f"{s}_gap_std"] = stats(strat_data[s]["gap_to_lb_obj_pct"])

        results.append(row)
        print(
            f"  Lambda={lmb:5.1f} | "
            f"Access Lat: {row['iterative_knapsack_dp_lat_mean']:5.2f} ± {row['iterative_knapsack_dp_lat_std']:4.2f} ms | "
            f"Sync Cost: {row['iterative_knapsack_dp_sync_mean']:5.1f} ± {row['iterative_knapsack_dp_sync_std']:4.1f} | "
            f"DP Gap: {row['iterative_knapsack_dp_gap_mean']:5.2f}%"
        )

    csv_path = os.path.join(RESULTS_DIR, "placement_lambda_sensitivity.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {csv_path}")
    return results


def benchmark_brute_force_optimality(
    num_instances: int = 60,
    num_servers: int = 5,
    num_tasks: int = 6,
) -> Dict[str, Any]:
    """Evaluates Iterative Knapsack DP against the exact Brute-Force optimum on random tiny instances.

    Generates num_instances random tiny instances with random server capacities,
    link latencies, task demands, client access traffic, and replication traffic.
    Saves results to brute_force_optimality_gap.csv.
    """
    print(f"\n--- Running Brute-Force Optimality Experiment ({num_instances} instances: {num_servers} servers, {num_tasks} tasks) ---")
    rows: List[Dict[str, Any]] = []
    gaps: List[float] = []

    for i in range(num_instances):
        seed = 2000 + i
        g = generate_cloud_topology(
            num_nodes=num_servers,
            edge_density=0.50,
            latency_range=(5.0, 30.0),
            capacity_range=(35, 65),
            seed=seed,
        )
        tasks = generate_synthetic_workload(
            graph=g,
            num_tasks=num_tasks,
            demand_range=(15, 35),
            requests_per_task=(10.0, 100.0),
            replication_traffic_range=(2.0, 20.0),
            seed=seed,
        )
        opt = CloudPlacementOptimizer(g, tasks, lambda_sync=1.0)
        report = opt.optimize()

        bf = report.strategy_metrics.get("brute_force_optimal")
        dp = report.strategy_metrics.get("iterative_knapsack_dp")

        if bf is not None and dp is not None and bf.total_objective > 0:
            gap_pct = max(0.0, ((dp.total_objective - bf.total_objective) / bf.total_objective) * 100.0)
            gaps.append(gap_pct)
            rows.append({
                "instance_id": i + 1,
                "seed": seed,
                "num_servers": num_servers,
                "num_tasks": num_tasks,
                "bf_total_objective": round(bf.total_objective, 2),
                "dp_total_objective": round(dp.total_objective, 2),
                "optimality_gap_pct": round(gap_pct, 4),
                "bf_placed_tasks": bf.placed_tasks_count,
                "dp_placed_tasks": dp.placed_tasks_count,
                "bf_access_latency_ms": round(bf.average_access_latency, 2),
                "dp_access_latency_ms": round(dp.average_access_latency, 2),
                "bf_sync_cost": round(bf.average_sync_cost, 2),
                "dp_sync_cost": round(dp.average_sync_cost, 2),
            })

    csv_path = os.path.join(RESULTS_DIR, "brute_force_optimality_gap.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved: {csv_path}")

    mean_gap = statistics.mean(gaps)
    median_gap = statistics.median(gaps)
    max_gap = max(gaps)
    exceed_5 = sum(1 for g in gaps if g > 5.0)

    print("\n--- Brute-Force Optimality Summary ---")
    print(f"  Total Tiny Instances Evaluated : {len(gaps)}")
    print(f"  Mean Optimality Gap            : {mean_gap:.4f}%")
    print(f"  Median Optimality Gap          : {median_gap:.4f}%")
    print(f"  Maximum Optimality Gap         : {max_gap:.4f}%")
    print(f"  Instances Exceeding 5% Gap     : {exceed_5} / {len(gaps)} ({exceed_5 / len(gaps) * 100.0:.1f}%)")

    return {
        "mean_gap": mean_gap,
        "median_gap": median_gap,
        "max_gap": max_gap,
        "exceed_5_count": exceed_5,
        "total_instances": len(gaps),
    }


# ==============================================================================
# 3. MATPLOTLIB VISUALIZATIONS WITH ERROR BARS
# ==============================================================================

def plot_runtime_vs_size(
    mst_res: List[Dict],
    sssp_res: List[Dict],
    apsp_res: List[Dict],
) -> None:
    """Generates a 4-panel runtime figure with error bars (sparse vs dense APSP/MST)."""
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # 1. MST Runtime (Sparse vs Dense)
    mst_sparse = [r for r in mst_res if r["graph_type"] == "sparse"]
    mst_dense = [r for r in mst_res if r["graph_type"] == "dense"]
    v_s = [r["num_nodes"] for r in mst_sparse]

    ax = axes[0, 0]
    ax.errorbar(v_s, [r["kruskal_mean_ms"] for r in mst_sparse], yerr=[r["kruskal_std_ms"] for r in mst_sparse], fmt="o-", capsize=3, label="Kruskal (Sparse d=0.2)", color="#1f77b4", linewidth=2)
    ax.errorbar(v_s, [r["prim_mean_ms"] for r in mst_sparse], yerr=[r["prim_std_ms"] for r in mst_sparse], fmt="s--", capsize=3, label="Prim (Sparse d=0.2)", color="#ff7f0e", linewidth=2)
    ax.errorbar(v_s, [r["kruskal_mean_ms"] for r in mst_dense], yerr=[r["kruskal_std_ms"] for r in mst_dense], fmt="^-", capsize=3, label="Kruskal (Dense d=0.8)", color="#2ca02c", linewidth=2)
    ax.errorbar(v_s, [r["prim_mean_ms"] for r in mst_dense], yerr=[r["prim_std_ms"] for r in mst_dense], fmt="v--", capsize=3, label="Prim (Dense d=0.8)", color="#d62728", linewidth=2)
    ax.set_title("MST Runtime vs Graph Size (Kruskal vs Prim)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Number of Nodes (|V|)", fontsize=10)
    ax.set_ylabel("Execution Time (ms)", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.6)

    # 2. SSSP Runtime (Dijkstra vs Bellman-Ford)
    ax = axes[0, 1]
    sssp_v = [r["num_nodes"] for r in sssp_res]
    ax.errorbar(sssp_v, [r["dijkstra_mean_ms"] for r in sssp_res], yerr=[r["dijkstra_std_ms"] for r in sssp_res], fmt="o-", capsize=3, label="Dijkstra Min-Heap O((V+E) log V)", color="#1b9e77", linewidth=2)
    ax.errorbar(sssp_v, [r["bellman_ford_mean_ms"] for r in sssp_res], yerr=[r["bellman_ford_std_ms"] for r in sssp_res], fmt="s-", capsize=3, label="Bellman-Ford O(V · E)", color="#e7298a", linewidth=2)
    ax.set_title("SSSP Runtime: Dijkstra vs Bellman-Ford", fontsize=12, fontweight="bold")
    ax.set_xlabel("Number of Nodes (|V|)", fontsize=10)
    ax.set_ylabel("Execution Time (ms)", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.6)

    # 3. APSP Sparse (density 0.20)
    ax = axes[1, 0]
    apsp_sparse = [r for r in apsp_res if r["graph_type"] == "sparse"]
    apsp_v = [r["num_nodes"] for r in apsp_sparse]
    ax.errorbar(apsp_v, [r["floyd_warshall_mean_ms"] for r in apsp_sparse], yerr=[r["floyd_warshall_std_ms"] for r in apsp_sparse], fmt="o-", capsize=3, label="Floyd-Warshall O(V³)", color="#7570b3", linewidth=2)
    ax.errorbar(apsp_v, [r["repeated_dijkstra_mean_ms"] for r in apsp_sparse], yerr=[r["repeated_dijkstra_std_ms"] for r in apsp_sparse], fmt="d-", capsize=3, label="Repeated Dijkstra O(V(V+E)log V)", color="#e6ab02", linewidth=2)
    ax.set_title("APSP Runtime on Sparse Graphs (Density = 0.20)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Number of Nodes (|V|)", fontsize=10)
    ax.set_ylabel("Execution Time (ms)", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.6)

    # 4. APSP Dense (density 0.80)
    ax = axes[1, 1]
    apsp_dense = [r for r in apsp_res if r["graph_type"] == "dense"]
    ax.errorbar(apsp_v, [r["floyd_warshall_mean_ms"] for r in apsp_dense], yerr=[r["floyd_warshall_std_ms"] for r in apsp_dense], fmt="o-", capsize=3, label="Floyd-Warshall O(V³)", color="#7570b3", linewidth=2)
    ax.errorbar(apsp_v, [r["repeated_dijkstra_mean_ms"] for r in apsp_dense], yerr=[r["repeated_dijkstra_std_ms"] for r in apsp_dense], fmt="d-", capsize=3, label="Repeated Dijkstra O(V³ log V)", color="#e6ab02", linewidth=2)
    ax.set_title("APSP Runtime on Dense Graphs (Density = 0.80)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Number of Nodes (|V|)", fontsize=10)
    ax.set_ylabel("Execution Time (ms)", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    output_path = os.path.join(RESULTS_DIR, "runtime_vs_size.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated Plot: {output_path}")


def plot_latency_vs_capacity(cap_res: List[Dict]) -> None:
    """Generates 2-panel figure showing Access Latency and Gap to Lower Bound vs Capacity."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    mults = [r["capacity_multiplier"] for r in cap_res]

    # Panel 1: Average Access Latency with error bars
    styles = {
        "unconstrained_lower_bound": ("k--", "x", "Unconstrained Lower Bound", "#333333"),
        "iterative_knapsack_dp": ("-", "o", "Iterative Knapsack DP", "#2ca02c"),
        "iterative_knapsack_greedy": ("--", "s", "Iterative Knapsack Greedy", "#1f77b4"),
        "spillover_greedy": ("-.", "^", "Spill-Over Greedy", "#ff7f0e"),
        "random_placement": (":", "v", "Random Feasible Placement", "#d62728"),
    }

    for strat, (ls, marker, label, color) in styles.items():
        means = [r[f"{strat}_access_latency_mean"] for r in cap_res]
        stds = [r[f"{strat}_access_latency_std"] for r in cap_res]
        ax1.errorbar(mults, means, yerr=stds, fmt=f"{marker}{ls}", capsize=3, label=label, color=color, linewidth=2)

    ax1.set_title("Average Access Latency vs Server Capacity Multiplier\n(Mean ± Std across 10 Seeds)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Capacity Multiplier (0.25x to 2.0x)", fontsize=11)
    ax1.set_ylabel("Average Access Latency (ms)", fontsize=11)
    ax1.legend(fontsize=9)
    ax1.grid(True, linestyle="--", alpha=0.6)

    # Panel 2: Access Latency Gap to Lower Bound (%) with error bars
    for strat in ["iterative_knapsack_dp", "iterative_knapsack_greedy", "spillover_greedy", "random_placement"]:
        _, marker, label, color = styles[strat]
        means = [r[f"{strat}_gap_to_lb_lat_pct_mean"] for r in cap_res]
        stds = [r[f"{strat}_gap_to_lb_lat_pct_std"] for r in cap_res]
        ax2.errorbar(mults, means, yerr=stds, fmt=f"{marker}-", capsize=3, label=f"{label}", color=color, linewidth=2)

    ax2.set_title("Access Latency Gap to Lower Bound (%)\n(Mean ± Std across 10 Seeds)", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Capacity Multiplier (0.25x to 2.0x)", fontsize=11)
    ax2.set_ylabel("Access Latency Gap (%)", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    output_path = os.path.join(RESULTS_DIR, "latency_vs_capacity.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated Plot: {output_path}")


def plot_placement_sensitivity_tasks(task_res: List[Dict]) -> None:
    """Generates 2-panel figure showing Objective and Gap vs Task Count."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    tasks = [r["num_tasks"] for r in task_res]

    styles = {
        "unconstrained_lower_bound": ("k--", "x", "Lower Bound", "#333333"),
        "iterative_knapsack_dp": ("-", "o", "Knapsack DP", "#2ca02c"),
        "iterative_knapsack_greedy": ("--", "s", "Greedy Rounds", "#1f77b4"),
        "spillover_greedy": ("-.", "^", "Spillover Greedy", "#ff7f0e"),
        "random_placement": (":", "v", "Random", "#d62728"),
    }

    # Panel 1: Total Objective vs Tasks
    for strat, (ls, marker, label, color) in styles.items():
        means = [r[f"{strat}_obj_mean"] for r in task_res]
        stds = [r[f"{strat}_obj_std"] for r in task_res]
        ax1.errorbar(tasks, means, yerr=stds, fmt=f"{marker}{ls}", capsize=3, label=label, color=color, linewidth=2)

    ax1.set_title("Total Objective Cost vs Number of Tasks\n(Mean ± Std across 10 Seeds)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Number of Cloud Tasks (Workload)", fontsize=11)
    ax1.set_ylabel("Composite Objective Cost", fontsize=11)
    ax1.legend(fontsize=9)
    ax1.grid(True, linestyle="--", alpha=0.6)

    # Panel 2: Gap vs Tasks
    for strat in ["iterative_knapsack_dp", "iterative_knapsack_greedy", "spillover_greedy", "random_placement"]:
        _, marker, label, color = styles[strat]
        means = [r[f"{strat}_gap_mean"] for r in task_res]
        stds = [r[f"{strat}_gap_std"] for r in task_res]
        ax2.errorbar(tasks, means, yerr=stds, fmt=f"{marker}-", capsize=3, label=label, color=color, linewidth=2)

    ax2.set_title("Optimality Gap to Lower Bound vs Workload Size\n(Mean ± Std across 10 Seeds)", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Number of Cloud Tasks (Workload)", fontsize=11)
    ax2.set_ylabel("Optimality Gap (%)", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    output_path = os.path.join(RESULTS_DIR, "placement_sensitivity_tasks.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated Plot: {output_path}")


def plot_placement_sensitivity_lambda(lambda_res: List[Dict]) -> None:
    """Generates 2-panel figure showing Trade-off and Gap vs Lambda."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    lmb_vals = [r["lambda_sync"] for r in lambda_res]

    # Panel 1: Access Latency vs Sync Cost (Trade-off for Knapsack DP)
    dp_lats = [r["iterative_knapsack_dp_lat_mean"] for r in lambda_res]
    dp_lat_stds = [r["iterative_knapsack_dp_lat_std"] for r in lambda_res]
    dp_syncs = [r["iterative_knapsack_dp_sync_mean"] for r in lambda_res]
    dp_sync_stds = [r["iterative_knapsack_dp_sync_std"] for r in lambda_res]

    ax1_twin = ax1.twinx()
    line1 = ax1.errorbar(lmb_vals, dp_lats, yerr=dp_lat_stds, fmt="o-", capsize=3, color="#1f77b4", linewidth=2.2, label="Access Latency (ms)")
    line2 = ax1_twin.errorbar(lmb_vals, dp_syncs, yerr=dp_sync_stds, fmt="s--", capsize=3, color="#d62728", linewidth=2.2, label="MST Sync Cost")

    ax1.set_title("Access Latency vs MST Sync Cost vs Lambda Weight\n(Knapsack DP, Mean ± Std)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Sync Penalty Weight (Lambda)", fontsize=11)
    ax1.set_ylabel("Average Access Latency (ms)", color="#1f77b4", fontsize=11)
    ax1_twin.set_ylabel("Replication Sync Cost along MST", color="#d62728", fontsize=11)
    ax1.grid(True, linestyle="--", alpha=0.6)

    # Combined legend
    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper center", fontsize=10)

    # Panel 2: Optimality Gap vs Lambda across strategies
    styles = {
        "iterative_knapsack_dp": ("o-", "Knapsack DP", "#2ca02c"),
        "iterative_knapsack_greedy": ("s--", "Greedy Rounds", "#1f77b4"),
        "spillover_greedy": ("^-", "Spillover Greedy", "#ff7f0e"),
        "random_placement": ("v:", "Random Placement", "#d62728"),
    }
    for strat, (fmt, label, color) in styles.items():
        means = [r[f"{strat}_gap_mean"] for r in lambda_res]
        stds = [r[f"{strat}_gap_std"] for r in lambda_res]
        ax2.errorbar(lmb_vals, means, yerr=stds, fmt=fmt, capsize=3, label=label, color=color, linewidth=2)

    ax2.set_title("Optimality Gap to Lower Bound vs Lambda Weight\n(Mean ± Std across 10 Seeds)", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Sync Penalty Weight (Lambda)", fontsize=11)
    ax2.set_ylabel("Optimality Gap (%)", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    output_path = os.path.join(RESULTS_DIR, "placement_sensitivity_lambda.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated Plot: {output_path}")


def plot_mst_backbone_topology() -> None:
    """Visualizes the cloud network with MST backbone and weighted-median Sync Hub highlighted."""
    data_path = os.path.join(project_root, "data", "small_topology.json")
    if not os.path.exists(data_path):
        return

    graph = Graph.load_from_json(data_path)
    tasks = generate_synthetic_workload(graph, num_tasks=15, seed=42)
    opt = CloudPlacementOptimizer(graph, tasks, lambda_sync=0.5)
    report = opt.optimize()

    mst_edges = report.mst_edges
    sync_hub = report.sync_hub_node
    mst_set = {tuple(sorted((u, v))) for u, v, _ in mst_edges}

    fig, ax = plt.subplots(figsize=(10, 8))

    pos = {}
    for node_id in graph.get_nodes():
        node = graph.get_node(node_id)
        x = node.metadata.get("x", node_id * 10)
        y = node.metadata.get("y", (node_id * 17) % 100)
        pos[node_id] = (x, y)

    # 1. Background Mesh links
    for u, v, lat in graph.get_edges():
        if tuple(sorted((u, v))) not in mst_set:
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            ax.plot([x1, x2], [y1, y2], color="#cccccc", linestyle="--", linewidth=1.2, zorder=1)

    # 2. MST Backbone Links
    for u, v, lat in mst_edges:
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        ax.plot([x1, x2], [y1, y2], color="#0055d4", linestyle="-", linewidth=3.2, zorder=2)
        mid_x = (x1 + x2) / 2.0
        mid_y = (y1 + y2) / 2.0
        ax.text(mid_x, mid_y, f"{lat:.1f}ms", fontsize=8, color="#003380", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#e6f0ff", edgecolor="none", alpha=0.85))

    # 3. Server Nodes
    node_x = [pos[n][0] for n in graph.get_nodes()]
    node_y = [pos[n][1] for n in graph.get_nodes()]
    capacities = [graph.get_capacity(n) for n in graph.get_nodes()]
    sizes = [cap * 3.5 for cap in capacities]

    ax.scatter(node_x, node_y, s=sizes, color="#ff7f0e", edgecolors="#333333", linewidth=1.5, zorder=3)

    # Highlight Sync Hub with star marker
    hx, hy = pos[sync_hub]
    ax.scatter([hx], [hy], s=650, color="#ffd700", edgecolors="#b8860b", marker="*", linewidth=2.0, zorder=5)

    for n in graph.get_nodes():
        x, y = pos[n]
        label = f"S{n} (HUB)" if n == sync_hub else f"S{n}"
        ax.text(x, y - 3.5, label, fontsize=9, fontweight="bold", color="black", ha="center", va="top", zorder=6)

    ax.set_title(
        f"Cloud Network Topology, MST Backbone & Sync Hub\nTotal Backbone Weight: {report.mst_total_weight:.2f} ms | Sync Hub: Server {sync_hub} (Weighted Median)",
        fontsize=12,
        fontweight="bold",
    )
    ax.set_xlabel("X Coordinate (Logical / Geospatial)", fontsize=10)
    ax.set_ylabel("Y Coordinate (Logical / Geospatial)", fontsize=10)

    legend_elements = [
        Line2D([0], [0], color="#0055d4", lw=3.2, label="MST Backbone Link"),
        Line2D([0], [0], color="#cccccc", lw=1.2, linestyle="--", label="Physical Mesh Link"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#ff7f0e", markersize=10, label="Server (Size ~ Capacity)"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#ffd700", markeredgecolor="#b8860b", markersize=14, label=f"Sync Hub (S{sync_hub}, Weighted Median)"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=9, framealpha=0.9)
    ax.grid(True, linestyle=":", alpha=0.5)

    plt.tight_layout()
    output_path = os.path.join(RESULTS_DIR, "mst_backbone_topology.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
def plot_placement_sensitivity_combined(
    cap_res: List[Dict[str, Any]],
    task_res: List[Dict[str, Any]],
    lambda_res: List[Dict[str, Any]],
) -> None:
    """Generates a 4-panel combined placement sensitivity figure for publication/report."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel (0, 0): Latency vs Capacity
    mults = [float(r["capacity_multiplier"]) for r in cap_res]
    styles = {
        "unconstrained_lower_bound": ("k--", "x", "Lower Bound", "#333333"),
        "iterative_knapsack_dp": ("-", "o", "Knapsack DP", "#2ca02c"),
        "iterative_knapsack_greedy": ("--", "s", "Greedy Rounds", "#1f77b4"),
        "spillover_greedy": ("-.", "^", "Spill-Over Greedy", "#ff7f0e"),
        "random_placement": (":", "v", "Random Placement", "#d62728"),
    }
    for strat, (ls, marker, label, color) in styles.items():
        means = [float(r[f"{strat}_access_latency_mean"]) for r in cap_res]
        stds = [float(r[f"{strat}_access_latency_std"]) for r in cap_res]
        axes[0, 0].errorbar(mults, means, yerr=stds, fmt=f"{marker}{ls}", capsize=3, label=label, color=color, linewidth=1.8)
    axes[0, 0].set_title("(A) Client Access Latency vs Server Capacity", fontsize=11, fontweight="bold")
    axes[0, 0].set_xlabel("Capacity Multiplier", fontsize=10)
    axes[0, 0].set_ylabel("Access Latency (ms)", fontsize=10)
    axes[0, 0].legend(fontsize=8, loc="upper right")
    axes[0, 0].grid(True, linestyle="--", alpha=0.5)

    # Panel (0, 1): Gap vs Capacity
    for strat in ["iterative_knapsack_dp", "iterative_knapsack_greedy", "spillover_greedy", "random_placement"]:
        _, marker, label, color = styles[strat]
        means = [float(r[f"{strat}_gap_to_lb_obj_pct_mean"]) for r in cap_res]
        stds = [float(r[f"{strat}_gap_to_lb_obj_pct_std"]) for r in cap_res]
        axes[0, 1].errorbar(mults, means, yerr=stds, fmt=f"{marker}-", capsize=3, label=label, color=color, linewidth=1.8)
    axes[0, 1].set_title("(B) Optimality Gap to Lower Bound vs Server Capacity", fontsize=11, fontweight="bold")
    axes[0, 1].set_xlabel("Capacity Multiplier", fontsize=10)
    axes[0, 1].set_ylabel("Objective Gap to LB (%)", fontsize=10)
    axes[0, 1].legend(fontsize=8, loc="upper right")
    axes[0, 1].grid(True, linestyle="--", alpha=0.5)

    # Panel (1, 0): Workload Tasks Scaling
    tasks = [int(r["num_tasks"]) for r in task_res]
    for strat in styles:
        ls, marker, label, color = styles[strat]
        means = [float(r[f"{strat}_obj_mean"]) for r in task_res]
        stds = [float(r[f"{strat}_obj_std"]) for r in task_res]
        axes[1, 0].errorbar(tasks, means, yerr=stds, fmt=f"{marker}{ls}", capsize=3, label=label, color=color, linewidth=1.8)
    axes[1, 0].set_title("(C) Composite Objective Cost vs Workload Tasks", fontsize=11, fontweight="bold")
    axes[1, 0].set_xlabel("Number of Tasks (|T|)", fontsize=10)
    axes[1, 0].set_ylabel("Total Composite Cost", fontsize=10)
    axes[1, 0].legend(fontsize=8, loc="upper left")
    axes[1, 0].grid(True, linestyle="--", alpha=0.5)

    # Panel (1, 1): Lambda Trade-off
    lams = [float(r["lambda_sync"]) for r in lambda_res]
    ax4 = axes[1, 1]
    ax4_twin = ax4.twinx()
    acc_m = [float(r["iterative_knapsack_dp_lat_mean"]) for r in lambda_res]
    acc_s = [float(r["iterative_knapsack_dp_lat_std"]) for r in lambda_res]
    sync_m = [float(r["iterative_knapsack_dp_sync_mean"]) for r in lambda_res]
    sync_s = [float(r["iterative_knapsack_dp_sync_std"]) for r in lambda_res]
    l1 = ax4.errorbar(lams, acc_m, yerr=acc_s, fmt="o-", color="#1f77b4", capsize=3, linewidth=2, label="Access Latency (ms)")
    l2 = ax4_twin.errorbar(lams, sync_m, yerr=sync_s, fmt="s--", color="#d62728", capsize=3, linewidth=2, label="MST Sync Cost")
    ax4.set_xscale("symlog", linthresh=1.0)
    ax4.set_title("(D) Access Latency vs MST Replication Sync Cost", fontsize=11, fontweight="bold")
    ax4.set_xlabel("Replication Weight (\u03bb, log scale)", fontsize=10)
    ax4.set_ylabel("Access Latency (ms)", color="#1f77b4", fontsize=10)
    ax4_twin.set_ylabel("MST Replication Sync Cost", color="#d62728", fontsize=10)
    lines = [l1, l2]
    labels = [l.get_label() for l in lines]
    ax4.legend(lines, labels, loc="center right", fontsize=8)
    ax4.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    output_path = os.path.join(RESULTS_DIR, "placement_sensitivity_combined.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated Plot: {output_path}")


# ==============================================================================
# MAIN EXECUTION CONTROLLER
# ==============================================================================

def main():
    print("=" * 80)
    print("  STARTING RIGOROUS EMPIRICAL EVALUATION (REVISION 2)")
    print("  10 Random Seeds per Placement Benchmark | 10 Repeats on Fixed Graphs")
    print("=" * 80)

    # 1. Runtime Benchmarks
    mst_res = benchmark_mst(sizes=[10, 25, 50, 100, 150, 200], density_sparse=0.20, density_dense=0.80, repeats=10)
    sssp_res = benchmark_sssp(sizes=[10, 20, 35, 50, 75, 100], density=0.20, repeats=10)
    apsp_res = benchmark_apsp(sizes=[10, 25, 40, 60, 80], density_sparse=0.20, density_dense=0.80, repeats=10)

    # 2. Placement Benchmarks (10 seeds each)
    cap_res = benchmark_placement_capacity(multipliers=[0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00], num_seeds=10)
    task_res = benchmark_placement_num_tasks(task_counts=[15, 25, 35, 50, 75], num_seeds=10)
    size_res, density_res = benchmark_placement_graph_size_and_density(sizes=[15, 30, 50, 75], densities=[0.15, 0.35, 0.60, 0.85], num_seeds=10)
    lambda_res = benchmark_placement_lambda(lambdas=[0.0, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0], num_seeds=10)
    bf_res = benchmark_brute_force_optimality(num_instances=60, num_servers=5, num_tasks=6)

    # 3. Generate Visualizations with Error Bars
    print("\n--- Generating Publication-Grade Figures with Error Bars ---")
    plot_runtime_vs_size(mst_res, sssp_res, apsp_res)
    plot_latency_vs_capacity(cap_res)
    plot_placement_sensitivity_tasks(task_res)
    plot_placement_sensitivity_lambda(lambda_res)
    plot_placement_sensitivity_combined(cap_res, task_res, lambda_res)
    plot_mst_backbone_topology()

    print("\n[DONE] All experiments, statistical aggregations, and plots completed successfully!")


if __name__ == "__main__":
    main()
