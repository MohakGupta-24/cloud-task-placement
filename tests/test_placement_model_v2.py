"""Integration and property validation tests for the revised Cloud Task Placement model.

Tests verify:
1. Server capacity constraints are strictly respected across all strategies.
2. Every task is either placed on a server or listed in unplaced_task_ids (no fake latencies).
3. Exact brute-force assignment solver on tiny instances benchmarks DP with a provable optimality gap.
4. Unconstrained lower bound is never beaten by any valid placement.
5. Lambda sensitivity: lambda=0 isolates access latency; lambda > 0 incorporates MST sync cost.
6. Fleet utilization is distributed across multiple servers rather than bottlenecked on 1 server.
"""

import os
import unittest
from typing import Dict, List

from src.graph.graph import Graph
from src.graph.generator import generate_cloud_topology
from src.optimizer.workload import Task, generate_synthetic_workload
from src.optimizer.placement_optimizer import CloudPlacementOptimizer


class TestPlacementModelV2(unittest.TestCase):
    def setUp(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.small_topology_path = os.path.join(base_dir, "data", "small_topology.json")
        self.graph = Graph.load_from_json(self.small_topology_path)

    def test_server_capacity_never_exceeded(self):
        """Verifies that no server's capacity is ever exceeded under any placement strategy."""
        tasks = generate_synthetic_workload(
            graph=self.graph,
            num_tasks=25,
            demand_range=(20, 60),
            requests_per_task=(10.0, 100.0),
            seed=101,
        )

        optimizer = CloudPlacementOptimizer(self.graph, tasks, lambda_sync=0.5)
        report = optimizer.optimize()

        # Constrained strategies must never violate server capacities
        constrained_strategies = [
            "iterative_knapsack_dp",
            "iterative_knapsack_greedy",
            "spillover_greedy",
            "random_placement",
        ]
        if "brute_force_optimal" in report.strategy_metrics:
            constrained_strategies.append("brute_force_optimal")

        nodes = self.graph.get_nodes()
        for strat_name in constrained_strategies:
            self.assertIn(strat_name, report.strategy_metrics)
            metrics = report.strategy_metrics[strat_name]

            # Calculate server usage
            server_used: Dict[int, int] = {n: 0 for n in nodes}
            for t_id, s in metrics.assignments.items():
                task = optimizer.task_map[t_id]
                server_used[s] += task.demand

            for s in nodes:
                cap = int(self.graph.get_capacity(s))
                self.assertLessEqual(
                    server_used[s],
                    cap,
                    f"Strategy '{strat_name}' overloaded Server {s} (used {server_used[s]} > cap {cap})",
                )

    def test_every_task_placed_or_listed_as_unplaced(self):
        """Verifies all tasks are accounted for: placed + unplaced == total_tasks, with disjoint sets."""
        tasks = generate_synthetic_workload(
            graph=self.graph,
            num_tasks=35,
            demand_range=(30, 80),  # Heavy workload designed to trigger capacity bottlenecks
            requests_per_task=(10.0, 50.0),
            seed=202,
        )

        optimizer = CloudPlacementOptimizer(self.graph, tasks, lambda_sync=0.2)
        report = optimizer.optimize()
        all_task_ids = {t.task_id for t in tasks}

        for strat_name, metrics in report.strategy_metrics.items():
            placed_ids = set(metrics.assignments.keys())
            unplaced_ids = set(metrics.unplaced_task_ids)

            # Placed count and unplaced count must sum to total tasks
            self.assertEqual(
                metrics.placed_tasks_count + metrics.unplaced_tasks_count,
                len(tasks),
                f"Strategy '{strat_name}' count mismatch",
            )
            self.assertEqual(len(placed_ids), metrics.placed_tasks_count)
            self.assertEqual(len(unplaced_ids), metrics.unplaced_tasks_count)

            # Sets must be mutually disjoint and cover all tasks
            self.assertTrue(
                placed_ids.isdisjoint(unplaced_ids),
                f"Strategy '{strat_name}' has overlapping placed and unplaced tasks",
            )
            self.assertEqual(
                placed_ids | unplaced_ids,
                all_task_ids,
                f"Strategy '{strat_name}' did not account for all tasks",
            )

    def test_unconstrained_lower_bound_is_never_beaten(self):
        """Validates that unconstrained lower bound objective is <= all valid placement strategies."""
        tasks = generate_synthetic_workload(
            graph=self.graph,
            num_tasks=15,
            demand_range=(10, 30),
            requests_per_task=(20.0, 100.0),
            seed=303,
        )

        optimizer = CloudPlacementOptimizer(self.graph, tasks, lambda_sync=0.5)
        report = optimizer.optimize()

        lb_metrics = report.strategy_metrics["unconstrained_lower_bound"]
        # On workloads where all tasks are placed, LB objective <= any constrained strategy
        for strat_name, metrics in report.strategy_metrics.items():
            if metrics.unplaced_tasks_count == 0:
                self.assertLessEqual(
                    lb_metrics.total_objective,
                    metrics.total_objective + 1e-4,
                    f"Lower bound ({lb_metrics.total_objective}) beat by '{strat_name}' ({metrics.total_objective})",
                )

    def test_brute_force_vs_iterative_dp_on_tiny_instances(self):
        """Cross-checks iterative knapsack DP against exact brute-force assignment on a tiny instance."""
        # 5 servers, 6 tasks (5^6 = 15,625 full combos, 6^6 = 46,656 with unplaced)
        tiny_graph = generate_cloud_topology(
            num_nodes=5,
            edge_density=0.8,
            latency_range=(5.0, 30.0),
            capacity_range=(40, 70),
            seed=42,
        )

        tasks = [
            Task(
                task_id=f"tiny_task_{i}",
                demand=d,
                client_requests={0: 10.0, 2: 20.0, 4: 15.0},
                replication_traffic=5.0,
            )
            for i, d in enumerate([15, 20, 25, 10, 18, 12])
        ]

        optimizer = CloudPlacementOptimizer(tiny_graph, tasks, lambda_sync=0.3)
        report = optimizer.optimize()

        self.assertIn("brute_force_optimal", report.strategy_metrics)
        bf_metrics = report.strategy_metrics["brute_force_optimal"]
        dp_metrics = report.strategy_metrics["iterative_knapsack_dp"]

        # 1. Both find feasible assignments
        self.assertEqual(bf_metrics.placed_tasks_count, len(tasks))
        self.assertEqual(dp_metrics.placed_tasks_count, len(tasks))

        # 2. Brute force is provably optimal; DP total objective must be >= BF
        self.assertLessEqual(
            bf_metrics.total_objective,
            dp_metrics.total_objective + 1e-4,
            "Brute force must be <= DP objective",
        )

        # 3. Verify optimality gap is bounded and small (<= 5%)
        optimality_gap = (
            (dp_metrics.total_objective - bf_metrics.total_objective)
            / bf_metrics.total_objective
        )
        self.assertLessEqual(
            optimality_gap,
            0.05,
            f"Optimality gap ({optimality_gap:.4f}) exceeded 5%",
        )

    def test_lambda_zero_vs_lambda_positive_behavior(self):
        """Tests that lambda=0 isolates access latency while lambda > 0 penalizes distance from MST hub."""
        tasks = generate_synthetic_workload(
            graph=self.graph,
            num_tasks=12,
            demand_range=(15, 35),
            requests_per_task=(20.0, 80.0),
            replication_traffic_range=(15.0, 40.0),
            seed=505,
        )

        # Run with lambda = 0 (pure access latency)
        opt_zero = CloudPlacementOptimizer(self.graph, tasks, lambda_sync=0.0)
        rep_zero = opt_zero.optimize()
        dp_zero = rep_zero.strategy_metrics["iterative_knapsack_dp"]

        # Run with lambda = 2.0 (strong sync penalty)
        opt_pos = CloudPlacementOptimizer(self.graph, tasks, lambda_sync=2.0)
        rep_pos = opt_pos.optimize()
        dp_pos = rep_pos.strategy_metrics["iterative_knapsack_dp"]

        # When lambda = 0, total_objective is access delay only (no sync penalty)
        from src.shortest_paths.floyd_warshall import floyd_warshall
        dist_matrix, _ = floyd_warshall(self.graph)
        computed_access_delay = sum(
            sum(req * dist_matrix[c][s] for c, req in opt_zero.task_map[tid].client_requests.items())
            for tid, s in dp_zero.assignments.items()
        )
        self.assertAlmostEqual(dp_zero.total_objective, round(computed_access_delay, 2), places=2)

        # When lambda > 0, objective incorporates sync cost
        self.assertGreater(dp_pos.total_objective, 0.0)

        # High lambda incentivizes lower sync cost
        self.assertLessEqual(
            dp_pos.average_sync_cost,
            dp_zero.average_sync_cost + 1e-4,
            "Placements under lambda > 0 should have equal or lower average sync cost",
        )

    def test_fleet_utilization_distribution(self):
        """Verifies fleet utilization is distributed across multiple servers (fixing old 4% bottleneck)."""
        tasks = generate_synthetic_workload(
            graph=self.graph,
            num_tasks=20,
            demand_range=(15, 40),
            requests_per_task=(15.0, 60.0),
            seed=606,
        )

        optimizer = CloudPlacementOptimizer(self.graph, tasks, lambda_sync=0.2)
        report = optimizer.optimize()

        dp_metrics = report.strategy_metrics["iterative_knapsack_dp"]
        hosting_servers = set(dp_metrics.assignments.values())

        # Old model placed tasks on only ~1-3 servers out of 10-50, fleet utilization was ~4%
        # New model should distribute across servers and achieve healthy utilization
        self.assertGreater(len(hosting_servers), 3)
    def test_pythonhashseed_determinism(self):
        """Verifies identical placement assignments under different PYTHONHASHSEED values via subprocess."""
        import subprocess
        import sys
        import json

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        topo_path = self.small_topology_path.replace("\\", "/")
        script = (
            "import json, os, sys\n"
            "from src.graph.graph import Graph\n"
            "from src.optimizer.workload import generate_synthetic_workload\n"
            "from src.optimizer.placement_optimizer import CloudPlacementOptimizer\n"
            f"graph = Graph.load_from_json('{topo_path}')\n"
            "tasks = generate_synthetic_workload(graph, num_tasks=30, demand_range=(10, 50), seed=42)\n"
            "optimizer = CloudPlacementOptimizer(graph, tasks, lambda_sync=0.5)\n"
            "report = optimizer.optimize()\n"
            "results = {\n"
            "    strat: m.assignments\n"
            "    for strat, m in report.strategy_metrics.items()\n"
            "}\n"
            "print(json.dumps(results, sort_keys=True))\n"
        )

        outputs = []
        for seed_val in ["0", "42", "99999"]:
            env = os.environ.copy()
            env["PYTHONHASHSEED"] = seed_val
            res = subprocess.run(
                [sys.executable, "-c", script],
                cwd=base_dir,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            outputs.append(res.stdout.strip())

        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[1], outputs[2])


if __name__ == "__main__":
    unittest.main()
