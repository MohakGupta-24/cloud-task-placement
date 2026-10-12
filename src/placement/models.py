"""Data structures for Cloud Task / VM Replica Placement Selection."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Union


@dataclass
class PlacementOption:
    """Represents a candidate task / VM replica placement.

    Attributes:
        item_id: Unique identifier for the placement decision or task.
        cost: Resource capacity cost incurred (e.g., CPU/RAM slots, non-negative integer).
        benefit: Latency-reduction benefit achieved (e.g., milliseconds saved, float >= 0.0).
        metadata: Arbitrary attributes (e.g., server_id, task_name, region).
    """
    item_id: Union[int, str]
    cost: int
    benefit: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.cost < 0:
            raise ValueError(f"Placement cost cannot be negative: {self.cost}")
        if self.benefit < 0:
            raise ValueError(f"Placement benefit cannot be negative: {self.benefit}")
        self.cost = int(self.cost)
        self.benefit = float(self.benefit)


@dataclass
class PlacementResult:
    """Represents the outcome of a knapsack-based placement selection.

    Attributes:
        selected_items: List of selected PlacementOption instances.
        total_benefit: Aggregate latency reduction achieved.
        total_cost: Aggregate capacity consumed.
        capacity_limit: Maximum allowed capacity limit.
    """
    selected_items: List[PlacementOption]
    total_benefit: float
    total_cost: int
    capacity_limit: int

    @property
    def selected_ids(self) -> List[Union[int, str]]:
        """Returns sorted IDs of all selected items."""
        return [item.item_id for item in self.selected_items]
