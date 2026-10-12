"""Task and Workload definitions for Cloud Placement."""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from ..graph.graph import Graph


@dataclass
class Task:
    """Represents a virtual machine (VM) or cloud service task.

    Attributes:
        task_id: Unique string or int identifier.
        demand: Integer compute/RAM resource capacity required.
        client_requests: Dict mapping client node_id -> request volume / traffic rate.
        metadata: Arbitrary task metadata (e.g., service type, SLA tier).
    """
    task_id: str
    demand: int
    client_requests: Dict[int, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.demand <= 0:
            raise ValueError(f"Task demand must be positive: {self.demand}")
        self.demand = int(self.demand)

    @property
    def total_requests(self) -> float:
        """Total client request volume across all client nodes."""
        return sum(self.client_requests.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "demand": self.demand,
            "client_requests": {str(k): v for k, v in self.client_requests.items()},
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Task:
        return cls(
            task_id=data["task_id"],
            demand=data["demand"],
            client_requests={int(k): float(v) for k, v in data.get("client_requests", {}).items()},
            metadata=data.get("metadata", {}),
        )


def generate_synthetic_workload(
    graph: Graph,
    num_tasks: int = 15,
    demand_range: tuple[int, int] = (10, 40),
    requests_per_task: tuple[float, float] = (10.0, 100.0),
    active_client_ratio: float = 0.5,
    seed: Optional[int] = 42,
) -> List[Task]:
    """Generates a realistic set of cloud tasks with client request distributions.

    Args:
        graph: The target cloud network topology.
        num_tasks: Number of tasks to generate.
        demand_range: Min and max integer resource demand.
        requests_per_task: Min and max traffic volume per client.
        active_client_ratio: Fraction of nodes generating traffic for a given task.
        seed: Random seed for reproducibility.

    Returns:
        List of Task instances.
    """
    rng = random.Random(seed)
    nodes = graph.get_nodes()
    tasks: List[Task] = []

    k_clients = max(1, int(round(len(nodes) * active_client_ratio)))

    for i in range(num_tasks):
        demand = rng.randint(demand_range[0], demand_range[1])
        client_subset = rng.sample(nodes, k_clients)
        client_requests = {
            node: round(rng.uniform(requests_per_task[0], requests_per_task[1]), 1)
            for node in client_subset
        }

        tasks.append(
            Task(
                task_id=f"task_{i:02d}",
                demand=demand,
                client_requests=client_requests,
                metadata={"service_tier": "critical" if i % 3 == 0 else "standard"},
            )
        )

    return tasks
