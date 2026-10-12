"""Brute-Force Knapsack Solver for verification and ground-truth testing.

Exhaustively checks all 2^n subsets to find the global optimum.
Intended strictly for testing and validation on small inputs (n <= 20).
"""

from __future__ import annotations
from typing import List
from .models import PlacementOption, PlacementResult


def brute_force_knapsack(
    items: List[PlacementOption],
    capacity: int,
) -> PlacementResult:
    """Finds the optimal placement subset by exhaustively searching all 2^n subsets.

    Time Complexity: O(n * 2^n)
    Space Complexity: O(n)

    Args:
        items: List of candidate PlacementOption objects.
        capacity: Maximum available server capacity (integer >= 0).

    Returns:
        PlacementResult containing the globally optimal subset.
    """
    if capacity < 0:
        raise ValueError(f"Capacity cannot be negative: {capacity}")

    n = len(items)
    best_subset: List[PlacementOption] = []
    best_benefit: float = 0.0
    best_cost: int = 0

    num_subsets = 1 << n

    for mask in range(num_subsets):
        current_subset: List[PlacementOption] = []
        current_cost = 0
        current_benefit = 0.0

        for i in range(n):
            if (mask >> i) & 1:
                item = items[i]
                current_cost += item.cost
                current_benefit += item.benefit
                current_subset.append(item)

        if current_cost <= capacity:
            if current_benefit > best_benefit or (
                current_benefit == best_benefit and current_cost < best_cost
            ):
                best_benefit = current_benefit
                best_cost = current_cost
                best_subset = current_subset

    return PlacementResult(
        selected_items=best_subset,
        total_benefit=round(best_benefit, 6),
        total_cost=best_cost,
        capacity_limit=capacity,
    )
