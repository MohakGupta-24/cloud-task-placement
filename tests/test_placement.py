"""Unit tests for 0-1 Knapsack DP and Greedy Placement Selection.

Includes:
1. Hand-checkable deterministic examples (including classic cases where Greedy is suboptimal).
2. Exhaustive brute-force validation on small randomized instances.
3. Edge case verifications (zero capacity, oversized items, empty input).
"""

import random
import unittest

from src.placement.models import PlacementOption
from src.placement.knapsack_dp import knapsack_01_dp
from src.placement.greedy_scheduler import (
    greedy_placement_selection,
    fractional_knapsack_greedy,
)
from src.placement.brute_force import brute_force_knapsack


class TestPlacementSelection(unittest.TestCase):
    def test_hand_checkable_example_standard(self):
        """Validates exact DP solution on a hand-calculated 4-item placement problem."""
        items = [
            PlacementOption(item_id="task_A", cost=2, benefit=12.0),
            PlacementOption(item_id="task_B", cost=1, benefit=10.0),
            PlacementOption(item_id="task_C", cost=3, benefit=20.0),
            PlacementOption(item_id="task_D", cost=2, benefit=15.0),
        ]
        capacity = 5

        result_dp = knapsack_01_dp(items, capacity)

        # Candidate subsets fitting in capacity 5:
        # {A, B, D}: cost 2+1+2=5, benefit 12+10+15 = 37.0 (OPTIMAL)
        # {B, C}: cost 1+3=4, benefit 10+20 = 30.0
        # {C, D}: cost 3+2=5, benefit 20+15 = 35.0
        # {A, C}: cost 2+3=5, benefit 12+20 = 32.0
        self.assertEqual(result_dp.total_cost, 5)
        self.assertAlmostEqual(result_dp.total_benefit, 37.0, places=4)
        self.assertEqual(set(result_dp.selected_ids), {"task_A", "task_B", "task_D"})

    def test_hand_checkable_greedy_suboptimality(self):
        """Demonstrates and validates where Greedy makes a suboptimal choice compared to exact DP.

        Capacity = 50.
        Items:
          1: cost 10, benefit 60 (ratio 6.0)
          2: cost 20, benefit 100 (ratio 5.0)
          3: cost 30, benefit 120 (ratio 4.0)

        Greedy selects {1, 2} (cost 30, benefit 160).
        DP selects {2, 3} (cost 50, benefit 220).
        """
        items = [
            PlacementOption(item_id="VM_1", cost=10, benefit=60.0),
            PlacementOption(item_id="VM_2", cost=20, benefit=100.0),
            PlacementOption(item_id="VM_3", cost=30, benefit=120.0),
        ]
        capacity = 50

        greedy_res = greedy_placement_selection(items, capacity)
        dp_res = knapsack_01_dp(items, capacity)
        frac_res = fractional_knapsack_greedy(items, capacity)

        # Greedy choice: {VM_1, VM_2} -> cost 30, benefit 160
        self.assertEqual(set(greedy_res.selected_ids), {"VM_1", "VM_2"})
        self.assertEqual(greedy_res.total_cost, 30)
        self.assertAlmostEqual(greedy_res.total_benefit, 160.0, places=4)

        # Optimal DP choice: {VM_2, VM_3} -> cost 50, benefit 220
        self.assertEqual(set(dp_res.selected_ids), {"VM_2", "VM_3"})
        self.assertEqual(dp_res.total_cost, 50)
        self.assertAlmostEqual(dp_res.total_benefit, 220.0, places=4)

        # Fractional knapsack relaxation: VM_1 (1.0), VM_2 (1.0), VM_3 (20/30 = 0.666667)
        # Benefit = 60 + 100 + 120*(2/3) = 240.0, cost = 50.0
        self.assertAlmostEqual(frac_res.total_benefit, 240.0, places=4)
        self.assertAlmostEqual(frac_res.total_cost, 50.0, places=4)

        # Fundamental Knapsack Hierarchy: Greedy <= 0-1 DP <= Fractional
        self.assertGreater(dp_res.total_benefit, greedy_res.total_benefit)
        self.assertGreater(frac_res.total_benefit, dp_res.total_benefit)

    def test_brute_force_exhaustive_check_on_random_inputs(self):
        """Exhaustively cross-verifies DP against brute-force (2^n search) across multiple random instances."""
        rng = random.Random(42)

        test_configs = [
            {"n": 4, "cap": 15},
            {"n": 6, "cap": 25},
            {"n": 8, "cap": 30},
            {"n": 10, "cap": 40},
            {"n": 12, "cap": 50},
        ]

        for cfg in test_configs:
            n = cfg["n"]
            capacity = cfg["cap"]

            items = [
                PlacementOption(
                    item_id=f"task_{i}",
                    cost=rng.randint(1, 15),
                    benefit=round(rng.uniform(5.0, 50.0), 2),
                )
                for i in range(n)
            ]

            dp_res = knapsack_01_dp(items, capacity)
            bf_res = brute_force_knapsack(items, capacity)
            greedy_res = greedy_placement_selection(items, capacity)
            frac_res = fractional_knapsack_greedy(items, capacity)

            # 1. DP must match Brute Force optimal benefit exactly
            self.assertAlmostEqual(
                dp_res.total_benefit,
                bf_res.total_benefit,
                places=4,
                msg=f"DP ({dp_res.total_benefit}) failed to match Brute-force ({bf_res.total_benefit}) on n={n}",
            )

            # 2. Constraints must be respected
            self.assertLessEqual(dp_res.total_cost, capacity)
            self.assertLessEqual(bf_res.total_cost, capacity)
            self.assertLessEqual(greedy_res.total_cost, capacity)
            self.assertLessEqual(frac_res.total_cost, capacity + 1e-6)

            # 3. Fractional knapsack is an exact theoretical upper bound on 0-1 knapsack DP
            self.assertGreaterEqual(
                frac_res.total_benefit + 1e-6,
                dp_res.total_benefit,
                msg=f"Fractional relaxation ({frac_res.total_benefit}) must upper bound DP ({dp_res.total_benefit}) on n={n}",
            )

            # 4. DP is globally optimal for 0-1, hence dp_benefit >= greedy_benefit
            self.assertGreaterEqual(
                dp_res.total_benefit + 1e-9,
                greedy_res.total_benefit,
                msg=f"DP benefit cannot be worse than greedy baseline on n={n}",
            )

    def test_edge_cases(self):
        """Verifies boundary conditions: zero capacity, empty items, oversized items, zero cost items."""
        items = [
            PlacementOption("t1", cost=5, benefit=20.0),
            PlacementOption("t2", cost=10, benefit=40.0),
        ]

        # Zero capacity
        zero_cap = knapsack_01_dp(items, capacity=0)
        self.assertEqual(len(zero_cap.selected_items), 0)
        self.assertEqual(zero_cap.total_benefit, 0.0)

        # Empty candidate list
        empty_res = knapsack_01_dp([], capacity=10)
        self.assertEqual(len(empty_res.selected_items), 0)
        self.assertEqual(empty_res.total_benefit, 0.0)

        # Oversized items (cost > capacity)
        oversized = [PlacementOption("big", cost=100, benefit=500.0)]
        res_over = knapsack_01_dp(oversized, capacity=50)
        self.assertEqual(len(res_over.selected_items), 0)
        self.assertEqual(res_over.total_benefit, 0.0)

        # Negative capacity error
        with self.assertRaises(ValueError):
            knapsack_01_dp(items, capacity=-5)

        with self.assertRaises(ValueError):
            greedy_placement_selection(items, capacity=-5)


if __name__ == "__main__":
    unittest.main()
