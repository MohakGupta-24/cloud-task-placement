"""Greedy Scheduler Baseline and Fractional Knapsack Upper Bound.

Includes:
1. greedy_placement_selection: 0-1 greedy heuristic based on efficiency ratio (benefit / cost).
2. fractional_knapsack_greedy: Optimal continuous knapsack relaxation, providing an exact upper bound.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
from .models import PlacementOption, PlacementResult


@dataclass
class FractionalKnapsackResult:
    """Result of fractional knapsack relaxation."""
    total_benefit: float
    total_cost: float
    selected_items: List[Tuple[PlacementOption, float]]


def greedy_placement_selection(
    items: List[PlacementOption],
    capacity: int,
) -> PlacementResult:
    """Greedy heuristic selection baseline for placement under capacity limits.

    Algorithm Overview:
      1. Calculate efficiency ratio for each candidate:
           ratio = benefit / cost  (if cost > 0, else infinity)
      2. Sort candidate items in descending order of ratio (ties broken by higher benefit).
      3. Sequentially admit items into the server if they fit within remaining capacity.

    Time Complexity:
      - Sorting candidates by efficiency ratio: O(n log n), where n = len(items)
      - Greedy linear scan: O(n)
      - Total Time Complexity: O(n log n)
    Space Complexity:
      - O(n) auxiliary space for sorted candidates and selected output list.

    Args:
        items: List of candidate PlacementOption objects.
        capacity: Maximum available server capacity (integer >= 0).

    Returns:
        PlacementResult containing greedily selected placement items, total benefit,
        and total cost.

    Raises:
        ValueError: If capacity is negative.
    """
    if capacity < 0:
        raise ValueError(f"Capacity cannot be negative: {capacity}")

    if not items or capacity == 0:
        return PlacementResult(
            selected_items=[],
            total_benefit=0.0,
            total_cost=0,
            capacity_limit=capacity,
        )

    # Sort by ratio = benefit / cost descending; if cost == 0, treat ratio as infinity
    def sort_key(item: PlacementOption):
        ratio = (item.benefit / item.cost) if item.cost > 0 else float("inf")
        return (ratio, item.benefit, -item.cost)

    sorted_items = sorted(items, key=sort_key, reverse=True)

    selected: List[PlacementOption] = []
    remaining_capacity = capacity
    total_benefit = 0.0
    total_cost = 0

    for item in sorted_items:
        if item.cost <= remaining_capacity:
            selected.append(item)
            remaining_capacity -= item.cost
            total_benefit += item.benefit
            total_cost += item.cost

    return PlacementResult(
        selected_items=selected,
        total_benefit=round(total_benefit, 6),
        total_cost=total_cost,
        capacity_limit=capacity,
    )


def fractional_knapsack_greedy(
    items: List[PlacementOption],
    capacity: int,
) -> FractionalKnapsackResult:
    """Computes the optimal fractional knapsack relaxation.

    Greedily takes items with the highest efficiency ratio, taking a partial fraction
    of the final item if capacity runs out.

    Mathematical Invariant:
      For any knapsack instance:
        value(0-1 Knapsack DP) <= value(Fractional Knapsack Greedy)
      Thus, fractional knapsack serves as a guaranteed theoretical upper bound.

    Time Complexity: O(n log n)
    Space Complexity: O(n)
    """
    if capacity < 0:
        raise ValueError(f"Capacity cannot be negative: {capacity}")

    if not items or capacity == 0:
        return FractionalKnapsackResult(
            total_benefit=0.0,
            total_cost=0.0,
            selected_items=[],
        )

    def sort_key(item: PlacementOption):
        ratio = (item.benefit / item.cost) if item.cost > 0 else float("inf")
        return (ratio, item.benefit, -item.cost)

    sorted_items = sorted(items, key=sort_key, reverse=True)

    rem_cap = float(capacity)
    total_benefit = 0.0
    total_cost = 0.0
    selected: List[Tuple[PlacementOption, float]] = []

    for item in sorted_items:
        if rem_cap <= 0.0:
            break
        if item.cost <= rem_cap:
            selected.append((item, 1.0))
            rem_cap -= item.cost
            total_cost += item.cost
            total_benefit += item.benefit
        else:
            fraction = rem_cap / item.cost
            selected.append((item, fraction))
            total_cost += item.cost * fraction
            total_benefit += item.benefit * fraction
            rem_cap = 0.0
            break

    return FractionalKnapsackResult(
        total_benefit=round(total_benefit, 6),
        total_cost=round(total_cost, 6),
        selected_items=selected,
    )
