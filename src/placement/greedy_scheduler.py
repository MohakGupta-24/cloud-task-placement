"""Greedy Scheduler Baseline for Cloud Task / Replica Placement Selection.

Selects candidate task/VM placements by prioritizing items with the highest
latency-reduction benefit per unit of capacity cost (efficiency ratio).
Used to benchmark solution quality against exact 0-1 Knapsack DP.
"""

from __future__ import annotations
from typing import List
from .models import PlacementOption, PlacementResult


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
