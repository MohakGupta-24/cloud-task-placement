"""0-1 Knapsack Dynamic Programming for Cloud Task / Replica Placement Selection.

Selects the subset of candidate task/VM placements that maximizes total latency-reduction benefit
without exceeding the server's resource capacity limit.
"""

from __future__ import annotations
from typing import List
from .models import PlacementOption, PlacementResult


def knapsack_01_dp(
    items: List[PlacementOption],
    capacity: int,
) -> PlacementResult:
    """Computes the exact optimal task placement subset using 0-1 Knapsack Dynamic Programming.

    Mathematical Formulation:
      Let dp[i][w] be the maximum latency-reduction benefit obtainable considering
      the first i candidate placements under remaining capacity w.

      Base Case:
        dp[0][w] = 0.0 for all w in [0, capacity]
        dp[i][0] = 0.0 for all i in [0, n]

      Recurrence:
        If cost[i - 1] > w:
          dp[i][w] = dp[i - 1][w]
        Else:
          dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - cost[i - 1]] + benefit[i - 1])

    Backtracking:
      Traces back from dp[n][capacity] to recover the exact subset of placed items.

    Time Complexity:
      - Table construction: O(n * W), where n = len(items) and W = capacity
      - Backtracking reconstruction: O(n)
      - Total Time Complexity: O(n * W) (pseudo-polynomial)
    Space Complexity:
      - O(n * W) auxiliary table space to support optimal item recovery.

    Args:
        items: List of candidate PlacementOption objects.
        capacity: Maximum available server capacity (integer >= 0).

    Returns:
        PlacementResult containing selected placement items, aggregate benefit,
        and aggregate capacity consumed.

    Raises:
        ValueError: If capacity is negative.
    """
    if capacity < 0:
        raise ValueError(f"Capacity cannot be negative: {capacity}")

    n = len(items)
    if n == 0 or capacity == 0:
        return PlacementResult(
            selected_items=[],
            total_benefit=0.0,
            total_cost=0,
            capacity_limit=capacity,
        )

    # 1. Build DP table: (n + 1) rows x (capacity + 1) columns
    dp: List[List[float]] = [[0.0] * (capacity + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        item = items[i - 1]
        cost = item.cost
        benefit = item.benefit

        for w in range(capacity + 1):
            if cost > w:
                dp[i][w] = dp[i - 1][w]
            else:
                incl = dp[i - 1][w - cost] + benefit
                excl = dp[i - 1][w]
                dp[i][w] = incl if incl > excl else excl

    # 2. Backtrack to reconstruct selected items
    selected: List[PlacementOption] = []
    curr_w = capacity
    total_cost = 0

    for i in range(n, 0, -1):
        # If value differs from row above, item i - 1 was selected
        if dp[i][curr_w] != dp[i - 1][curr_w]:
            item = items[i - 1]
            selected.append(item)
            curr_w -= item.cost
            total_cost += item.cost

    selected.reverse()
    total_benefit = round(dp[n][capacity], 6)

    return PlacementResult(
        selected_items=selected,
        total_benefit=total_benefit,
        total_cost=total_cost,
        capacity_limit=capacity,
    )
