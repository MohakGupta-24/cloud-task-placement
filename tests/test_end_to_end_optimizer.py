"""End-to-End integration test for the CloudPlacementOptimizer on the small dataset."""

import os
import unittest

from src.graph.graph import Graph
from src.optimizer.workload import Task, generate_synthetic_workload
from src.optimizer.placement_optimizer import CloudPlacementOptimizer


class TestEndToEndOptimizer(unittest.TestCase):
    def setUp(self):
        # Locate data/small_topology.json
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_path = os.path.join(base_dir, "data", "small_topology.json")
        self.assertTrue(os.path.exists(self.data_path), f"Dataset not found at {self.data_path}")
        self.graph = Graph.load_from_json(self.data_path)

    def test_end_to_end_optimization_pipeline(self):
        """Runs the entire pipeline on small_topology.json and verifies all core outputs."""
        # 1. Generate realistic 15-task workload
        tasks = generate_synthetic_workload(
            graph=self.graph,
            num_tasks=15,
            demand_range=(15, 45),
            requests_per_task=(20.0, 150.0),
            seed=42,
        )

        # 2. Run optimizer
        optimizer = CloudPlacementOptimizer(self.graph, tasks)
        report = optimizer.optimize()

        # 3. Verify MST Backbone
        num_nodes = self.graph.num_nodes
        self.assertEqual(len(report.mst_edges), num_nodes - 1)
        self.assertGreater(report.mst_total_weight, 0.0)
        self.assertGreater(report.backbone_sync_latency, 0.0)

        # 4. Verify Routing Table
        for u in self.graph.get_nodes():
            for v in self.graph.get_nodes():
                self.assertIn((u, v), report.routing_table)
                entry = report.routing_table[(u, v)]
                self.assertIn("path", entry)
                self.assertIn("latency", entry)
                if u == v:
                    self.assertEqual(entry["latency"], 0.0)
                    self.assertEqual(entry["path"], [u])
                else:
                    self.assertEqual(entry["path"][0], u)
                    self.assertEqual(entry["path"][-1], v)
                    self.assertGreater(entry["latency"], 0.0)

        # 5. Verify Capacity Constraints on every server
        total_used_capacity = 0
        for summary in report.server_summaries:
            self.assertLessEqual(
                summary.used_capacity,
                summary.total_capacity,
                f"Server {summary.server_id} exceeded its capacity!",
            )
            total_used_capacity += summary.used_capacity

        # 6. Verify Cost/Benefit Table
        self.assertGreater(len(report.cost_benefit_table), 0)
        for decision in report.cost_benefit_table:
            self.assertGreater(decision.demand_cost, 0)
            self.assertGreaterEqual(decision.latency_benefit, 0.0)
            self.assertGreater(decision.baseline_latency, decision.optimized_latency - 1e-6)
            self.assertAlmostEqual(
                decision.latency_benefit,
                decision.baseline_latency - decision.optimized_latency,
                places=3,
            )

        # 7. Verify Latency Optimization
        self.assertLess(
            report.optimized_average_latency,
            report.baseline_average_latency,
            "Optimized latency should be strictly lower than baseline!",
        )
        self.assertGreater(report.latency_reduction_percent, 0.0)

        # 8. Verify DP matches or outperforms Greedy
        self.assertLessEqual(
            report.optimized_average_latency,
            report.greedy_optimized_latency + 1e-4,
            "DP should achieve equal or lower average latency compared to greedy baseline!",
        )


if __name__ == "__main__":
    unittest.main()
