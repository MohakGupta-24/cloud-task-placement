"""Comprehensive Experimental Suite for Cloud Task Placement PBL.

Conducts empirical benchmarking, sensitivity analysis, and solution quality evaluations:
1. MST Runtime Comparison: Prim's vs Kruskal's algorithm (varying |V| and edge density).
2. SSSP Runtime Comparison: Dijkstra's vs Bellman-Ford algorithm (varying |V|).
3. APSP Runtime Comparison: Floyd-Warshall vs Repeated Dijkstra from every node.
4. Placement Quality Comparison: 0-1 Knapsack DP vs Greedy heuristic across capacity limits.
5. Saves CSV summaries and generates publication-grade Matplotlib figures:
   - experiments/results/runtime_vs_size.png
   - experiments/results/latency_vs_capacity.png
   - experiments/results/mst_backbone_topology.png
"""

import csv
import os
import sys
import time
from typing import Any, Dict, List, Tuple

# Headless matplotlib backend for non-interactive saving
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure root is in sys.path
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


def benchmark_mst(sizes: List[int], density: float = 0.25, trials: int = 3) -> List[Dict[str, Any]]:
    """Benchmarks Kruskal's vs Prim's algorithm across graph sizes."""
    print("\n--- Running MST Benchmark: Kruskal vs Prim ---")
    results = []

    for n in sizes:
        kruskal_times, prim_times = [], []
        edges_count = 0
        weight_k, weight_p = 0.0, 0.0

        for t in range(trials):
            g = generate_cloud_topology(
                num_nodes=n,
                edge_density=density,
                latency_range=(1.0, 50.0),
                seed=1000 + n * 10 + t,
                ensure_connected=True,
            )
            edges_count = g.num_edges

            # Kruskal
            t0 = time.perf_counter()
            _, weight_k = kruskal_mst(g)
            t1 = time.perf_counter()
            kruskal_times.append((t1 - t0) * 1000.0)  # ms

            # Prim
            t0 = time.perf_counter()
            _, weight_p = prim_mst(g)
            t1 = time.perf_counter()
            prim_times.append((t1 - t0) * 1000.0)  # ms

        avg_k = sum(kruskal_times) / len(kruskal_times)
        avg_p = sum(prim_times) / len(prim_times)

        row = {
            "num_nodes": n,
            "num_edges": edges_count,
            "density": density,
            "kruskal_runtime_ms": round(avg_k, 3),
            "prim_runtime_ms": round(avg_p, 3),
            "mst_weight": round(weight_k, 2),
        }
        results.append(row)
        print(f"  |V|={n:3d}, |E|={edges_count:4d} | Kruskal: {avg_k:6.2f} ms | Prim: {avg_p:6.2f} ms | Weight: {weight_k:.1f}")

    # Save to CSV
    csv_path = os.path.join(RESULTS_DIR, "mst_runtime_comparison.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {csv_path}")
    return results


def benchmark_sssp(sizes: List[int], density: float = 0.20, trials: int = 3) -> List[Dict[str, Any]]:
    """Benchmarks Dijkstra vs Bellman-Ford single-source shortest paths."""
    print("\n--- Running SSSP Benchmark: Dijkstra vs Bellman-Ford ---")
    results = []

    for n in sizes:
        dijk_times, bf_times = [], []
        edges_count = 0

        for t in range(trials):
            g = generate_cloud_topology(
                num_nodes=n,
                edge_density=density,
                latency_range=(1.0, 50.0),
                seed=2000 + n * 10 + t,
                ensure_connected=True,
            )
            edges_count = g.num_edges

            # Dijkstra
            t0 = time.perf_counter()
            dijkstra(g, source=0)
            t1 = time.perf_counter()
            dijk_times.append((t1 - t0) * 1000.0)

            # Bellman-Ford
            t0 = time.perf_counter()
            bellman_ford(g, source=0)
            t1 = time.perf_counter()
            bf_times.append((t1 - t0) * 1000.0)

        avg_d = sum(dijk_times) / len(dijk_times)
        avg_bf = sum(bf_times) / len(bf_times)

        row = {
            "num_nodes": n,
            "num_edges": edges_count,
            "dijkstra_runtime_ms": round(avg_d, 3),
            "bellman_ford_runtime_ms": round(avg_bf, 3),
            "speedup_ratio": round(avg_bf / avg_d, 2) if avg_d > 0 else 0.0,
        }
        results.append(row)
        print(f"  |V|={n:3d}, |E|={edges_count:4d} | Dijkstra: {avg_d:6.2f} ms | Bellman-Ford: {avg_bf:7.2f} ms | Speedup: {row['speedup_ratio']}x")

    csv_path = os.path.join(RESULTS_DIR, "sssp_runtime_comparison.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {csv_path}")
    return results


def benchmark_apsp(sizes: List[int], density: float = 0.20, trials: int = 3) -> List[Dict[str, Any]]:
    """Benchmarks Floyd-Warshall O(V^3) vs Repeated Dijkstra O(V*(V+E)log V)."""
    print("\n--- Running APSP Benchmark: Floyd-Warshall vs Repeated Dijkstra ---")
    results = []

    for n in sizes:
        fw_times, rep_dijk_times = [], []
        edges_count = 0

        for t in range(trials):
            g = generate_cloud_topology(
                num_nodes=n,
                edge_density=density,
                latency_range=(1.0, 50.0),
                seed=3000 + n * 10 + t,
                ensure_connected=True,
            )
            edges_count = g.num_edges

            # Floyd-Warshall
            t0 = time.perf_counter()
            floyd_warshall(g)
            t1 = time.perf_counter()
            fw_times.append((t1 - t0) * 1000.0)

            # Repeated Dijkstra from every vertex
            t0 = time.perf_counter()
            for s in g.get_nodes():
                dijkstra(g, source=s)
            t1 = time.perf_counter()
            rep_dijk_times.append((t1 - t0) * 1000.0)

        avg_fw = sum(fw_times) / len(fw_times)
        avg_rd = sum(rep_dijk_times) / len(rep_dijk_times)

        row = {
            "num_nodes": n,
            "num_edges": edges_count,
            "floyd_warshall_ms": round(avg_fw, 3),
            "repeated_dijkstra_ms": round(avg_rd, 3),
        }
        results.append(row)
        print(f"  |V|={n:3d}, |E|={edges_count:4d} | Floyd-Warshall: {avg_fw:7.2f} ms | Repeated Dijkstra: {avg_rd:7.2f} ms")

    csv_path = os.path.join(RESULTS_DIR, "apsp_runtime_comparison.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {csv_path}")
    return results


def benchmark_placement_capacity(
    capacity_multipliers: List[float],
) -> List[Dict[str, Any]]:
    """Evaluates solution quality (average latency, utilization) as capacity varies."""
    print("\n--- Running Placement Sensitivity Benchmark: DP vs Greedy across Capacity ---")
    base_data_path = os.path.join(project_root, "data", "medium_topology.json")
    if not os.path.exists(base_data_path):
        base_g = generate_cloud_topology(50, 0.15, (2.0, 75.0), (100.0, 500.0), seed=42)
    else:
        base_g = Graph.load_from_json(base_data_path)

    # Generate 40 tasks
    tasks = generate_synthetic_workload(
        graph=base_g,
        num_tasks=40,
        demand_range=(20, 80),
        requests_per_task=(30.0, 200.0),
        seed=101,
    )

    results = []

    for mult in capacity_multipliers:
        # Scale each server's capacity
        scaled_g = Graph(directed=False)
        for node_id in base_g.get_nodes():
            orig_cap = base_g.get_capacity(node_id)
            scaled_g.add_node(
                node_id,
                capacity=max(1, int(orig_cap * mult)),
                **base_g.get_node(node_id).metadata,
            )
        for u, v, lat in base_g.get_edges():
            scaled_g.add_edge(u, v, latency=lat)

        optimizer = CloudPlacementOptimizer(scaled_g, tasks)
        report = optimizer.optimize()

        row = {
            "capacity_multiplier": mult,
            "baseline_latency_ms": report.baseline_average_latency,
            "dp_latency_ms": report.optimized_average_latency,
            "dp_reduction_pct": report.latency_reduction_percent,
            "greedy_latency_ms": report.greedy_optimized_latency,
            "greedy_reduction_pct": report.greedy_latency_reduction_percent,
            "fleet_utilization_pct": report.total_capacity_utilization,
            "tasks_placed": len(report.cost_benefit_table),
        }
        results.append(row)
        print(
            f"  Cap Multiplier {mult:4.2f}x | "
            f"Base: {report.baseline_average_latency:.1f}ms | "
            f"DP: {report.optimized_average_latency:.1f}ms (-{report.latency_reduction_percent:.1f}%) | "
            f"Greedy: {report.greedy_optimized_latency:.1f}ms (-{report.greedy_latency_reduction_percent:.1f}%) | "
            f"Util: {report.total_capacity_utilization:4.1f}% | "
            f"Tasks: {len(report.cost_benefit_table)}/40"
        )

    csv_path = os.path.join(RESULTS_DIR, "placement_comparison.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {csv_path}")
    return results


def plot_runtime_vs_size(mst_res: List[Dict], sssp_res: List[Dict], apsp_res: List[Dict]) -> None:
    """Generates a 3-panel figure comparing runtimes vs graph size."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # 1. MST
    mst_v = [r["num_nodes"] for r in mst_res]
    kruskal_t = [r["kruskal_runtime_ms"] for r in mst_res]
    prim_t = [r["prim_runtime_ms"] for r in mst_res]

    axes[0].plot(mst_v, kruskal_t, "o-", label="Kruskal O(E log V)", color="#2b5c8f", linewidth=2)
    axes[0].plot(mst_v, prim_t, "s-", label="Prim (Min-Heap) O((V+E) log V)", color="#d95f02", linewidth=2)
    axes[0].set_title("MST Runtime vs Graph Size (|V|)", fontsize=13, fontweight="bold")
    axes[0].set_xlabel("Number of Nodes (|V|)", fontsize=11)
    axes[0].set_ylabel("Execution Time (ms)", fontsize=11)
    axes[0].legend(fontsize=10)
    axes[0].grid(True, linestyle="--", alpha=0.6)

    # 2. SSSP
    sssp_v = [r["num_nodes"] for r in sssp_res]
    dijk_t = [r["dijkstra_runtime_ms"] for r in sssp_res]
    bf_t = [r["bellman_ford_runtime_ms"] for r in sssp_res]

    axes[1].plot(sssp_v, dijk_t, "o-", label="Dijkstra (Min-Heap) O((V+E) log V)", color="#1b9e77", linewidth=2)
    axes[1].plot(sssp_v, bf_t, "^-", label="Bellman-Ford O(V * E)", color="#e7298a", linewidth=2)
    axes[1].set_title("SSSP Runtime: Dijkstra vs Bellman-Ford", fontsize=13, fontweight="bold")
    axes[1].set_xlabel("Number of Nodes (|V|)", fontsize=11)
    axes[1].set_ylabel("Execution Time (ms)", fontsize=11)
    axes[1].legend(fontsize=10)
    axes[1].grid(True, linestyle="--", alpha=0.6)

    # 3. APSP
    apsp_v = [r["num_nodes"] for r in apsp_res]
    fw_t = [r["floyd_warshall_ms"] for r in apsp_res]
    rd_t = [r["repeated_dijkstra_ms"] for r in apsp_res]

    axes[2].plot(apsp_v, fw_t, "o-", label="Floyd-Warshall O(V^3)", color="#7570b3", linewidth=2)
    axes[2].plot(apsp_v, rd_t, "d-", label="Repeated Dijkstra O(V*(V+E)log V)", color="#e6ab02", linewidth=2)
    axes[2].set_title("APSP: Floyd-Warshall vs Repeated Dijkstra", fontsize=13, fontweight="bold")
    axes[2].set_xlabel("Number of Nodes (|V|)", fontsize=11)
    axes[2].set_ylabel("Execution Time (ms)", fontsize=11)
    axes[2].legend(fontsize=10)
    axes[2].grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    output_path = os.path.join(RESULTS_DIR, "runtime_vs_size.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated Plot: {output_path}")


def plot_latency_vs_capacity(placement_res: List[Dict]) -> None:
    """Generates a 2-panel figure showing average latency and utilization vs capacity constraints."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    multipliers = [r["capacity_multiplier"] for r in placement_res]
    base_lats = [r["baseline_latency_ms"] for r in placement_res]
    dp_lats = [r["dp_latency_ms"] for r in placement_res]
    greedy_lats = [r["greedy_latency_ms"] for r in placement_res]
    utilization = [r["fleet_utilization_pct"] for r in placement_res]

    # Panel 1: Latency curves
    ax1.plot(multipliers, base_lats, "k--", label="Unoptimized Baseline", linewidth=1.8)
    ax1.plot(multipliers, greedy_lats, "s-", label="Greedy Heuristic", color="#e7298a", linewidth=2)
    ax1.plot(multipliers, dp_lats, "o-", label="Optimal 0-1 Knapsack DP", color="#1b9e77", linewidth=2.5)
    ax1.set_title("Average Client Latency vs Server Capacity", fontsize=13, fontweight="bold")
    ax1.set_xlabel("Capacity Multiplier (Relative to Baseline)", fontsize=11)
    ax1.set_ylabel("Average Access Latency (ms)", fontsize=11)
    ax1.legend(fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.6)

    # Panel 2: Capacity Utilization %
    ax2.plot(multipliers, utilization, "o-", color="#2b5c8f", linewidth=2.2, label="Fleet Capacity Utilization %")
    ax2.set_title("Fleet Capacity Utilization vs Capacity Multiplier", fontsize=13, fontweight="bold")
    ax2.set_xlabel("Capacity Multiplier", fontsize=11)
    ax2.set_ylabel("Utilization (%)", fontsize=11)
    ax2.set_ylim(0, 105)
    ax2.legend(fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    output_path = os.path.join(RESULTS_DIR, "latency_vs_capacity.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated Plot: {output_path}")


def plot_mst_backbone_topology() -> None:
    """Visualizes the cloud network with the MST backbone highlighted over the full graph."""
    data_path = os.path.join(project_root, "data", "small_topology.json")
    if not os.path.exists(data_path):
        return

    graph = Graph.load_from_json(data_path)
    mst_edges, total_weight = kruskal_mst(graph)
    mst_set = {tuple(sorted((u, v))) for u, v, _ in mst_edges}

    fig, ax = plt.subplots(figsize=(9, 7))

    # Node positions
    pos = {}
    for node_id in graph.get_nodes():
        node = graph.get_node(node_id)
        x = node.metadata.get("x", node_id * 10)
        y = node.metadata.get("y", (node_id * 17) % 100)
        pos[node_id] = (x, y)

    # 1. Draw background mesh links
    for u, v, lat in graph.get_edges():
        if tuple(sorted((u, v))) not in mst_set:
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            ax.plot([x1, x2], [y1, y2], color="#cccccc", linestyle="--", linewidth=1.2, zorder=1)

    # 2. Draw MST Backbone links (bold blue)
    for u, v, lat in mst_edges:
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        ax.plot([x1, x2], [y1, y2], color="#0055d4", linestyle="-", linewidth=3.2, zorder=2)
        # Edge weight label at midpoint
        mid_x = (x1 + x2) / 2.0
        mid_y = (y1 + y2) / 2.0
        ax.text(mid_x, mid_y, f"{lat:.1f}ms", fontsize=8, color="#003380", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#e6f0ff", edgecolor="none", alpha=0.85))

    # 3. Draw Server Nodes
    node_x = [pos[n][0] for n in graph.get_nodes()]
    node_y = [pos[n][1] for n in graph.get_nodes()]
    capacities = [graph.get_capacity(n) for n in graph.get_nodes()]

    # Size proportional to capacity
    sizes = [cap * 3.5 for cap in capacities]
    scatter = ax.scatter(node_x, node_y, s=sizes, color="#ff7f0e", edgecolors="#333333", linewidth=1.5, zorder=3)

    for n in graph.get_nodes():
        x, y = pos[n]
        ax.text(x, y, f"S{n}", fontsize=9, fontweight="bold", color="black", ha="center", va="center", zorder=4)

    # Title & custom legend
    ax.set_title(
        f"Cloud Network Topology & MST Backbone Overlay\nTotal Backbone Latency: {total_weight:.2f} ms ({len(mst_edges)} links)",
        fontsize=12,
        fontweight="bold",
    )
    ax.set_xlabel("X Coordinate (Geographic / Logical)", fontsize=10)
    ax.set_ylabel("Y Coordinate (Geographic / Logical)", fontsize=10)

    # Custom legend proxies
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color="#0055d4", lw=3, label="MST Backbone Link"),
        Line2D([0], [0], color="#cccccc", lw=1.2, linestyle="--", label="Physical Mesh Link"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#ff7f0e", markersize=10, label="Cloud Server (Size ~ Capacity)"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=9, framealpha=0.9)
    ax.grid(True, linestyle=":", alpha=0.5)

    plt.tight_layout()
    output_path = os.path.join(RESULTS_DIR, "mst_backbone_topology.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated Plot: {output_path}")


def main():
    print("=" * 70)
    print("  STARTING EXPERIMENTAL BENCHMARKS & EVALUATION")
    print("=" * 70)

    # 1. MST Benchmark: |V| in [10, 25, 50, 100, 150, 200]
    mst_res = benchmark_mst(sizes=[10, 25, 50, 100, 150, 200], density=0.20, trials=3)

    # 2. SSSP Benchmark: |V| in [10, 20, 35, 50, 75, 100]
    sssp_res = benchmark_sssp(sizes=[10, 20, 35, 50, 75, 100], density=0.20, trials=3)

    # 3. APSP Benchmark: |V| in [10, 25, 40, 60, 80]
    apsp_res = benchmark_apsp(sizes=[10, 25, 40, 60, 80], density=0.20, trials=2)

    # 4. Placement Sensitivity Benchmark across capacity multipliers
    placement_res = benchmark_placement_capacity(
        capacity_multipliers=[0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00]
    )

    # 5. Generate Matplotlib plots
    print("\n--- Generating Matplotlib Figures ---")
    plot_runtime_vs_size(mst_res, sssp_res, apsp_res)
    plot_latency_vs_capacity(placement_res)
    plot_mst_backbone_topology()

    print("\n[OK] All experimental benchmarks completed successfully!")
    print(f"All CSV tables and figures saved to: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
