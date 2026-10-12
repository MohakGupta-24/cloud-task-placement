"""Synthetic Server Topology Generator for Cloud Task Placement.

Generates realistic, connected cloud network topologies with configurable:
- Server node counts
- Edge density / interconnectivity
- Link latency distributions (in milliseconds)
- Server resource capacities (e.g., CPU/RAM capacity slots)
- Fixed random seed for guaranteed reproducibility.
"""

from __future__ import annotations
import math
import random
from typing import Optional, Tuple
from .graph import Graph


def generate_cloud_topology(
    num_nodes: int,
    edge_density: float,
    latency_range: Tuple[float, float] = (1.0, 50.0),
    capacity_range: Tuple[float, float] = (50.0, 500.0),
    seed: Optional[int] = 42,
    ensure_connected: bool = True,
    round_precision: int = 2,
) -> Graph:
    """Generates a synthetic cloud datacenter / server network topology.
    
    Args:
        num_nodes: Number of server nodes (n >= 1).
        edge_density: Edge density in range (0.0, 1.0]. Represents the ratio of
            present links relative to the complete graph K_n.
        latency_range: Tuple of (min_latency_ms, max_latency_ms).
        capacity_range: Tuple of (min_capacity, max_capacity).
        seed: Random seed for deterministic reproducibility.
        ensure_connected: If True, guarantees the topology is fully connected
            by initializing a random spanning tree backbone before adding extra links.
        round_precision: Decimal places for latency and capacity values.

    Returns:
        Graph: An initialized Graph instance representing the cloud network.
    """
    if num_nodes < 1:
        raise ValueError("num_nodes must be at least 1")
    if not (0.0 < edge_density <= 1.0):
        raise ValueError(f"edge_density must be in (0.0, 1.0], got {edge_density}")
    if latency_range[0] < 0 or latency_range[0] > latency_range[1]:
        raise ValueError(f"Invalid latency_range: {latency_range}")
    if capacity_range[0] < 0 or capacity_range[0] > capacity_range[1]:
        raise ValueError(f"Invalid capacity_range: {capacity_range}")

    rng = random.Random(seed)
    graph = Graph(directed=False)

    # 1. Initialize nodes with 2D coordinates and capacities
    for i in range(num_nodes):
        cap = round(rng.uniform(capacity_range[0], capacity_range[1]), round_precision)
        x_coord = round(rng.uniform(0.0, 100.0), round_precision)
        y_coord = round(rng.uniform(0.0, 100.0), round_precision)
        graph.add_node(
            node_id=i,
            capacity=cap,
            x=x_coord,
            y=y_coord,
            region=f"region_{i % 5}",
        )

    if num_nodes == 1:
        return graph

    max_possible_edges = (num_nodes * (num_nodes - 1)) // 2
    
    if ensure_connected:
        # Minimum edges needed for connectivity is n - 1
        min_edges = num_nodes - 1
        target_edges = max(min_edges, int(round(edge_density * max_possible_edges)))
        target_edges = min(target_edges, max_possible_edges)

        # 2a. Build a random spanning tree to ensure full connectivity
        # Shuffle nodes to avoid linear chain bias
        nodes_shuffled = list(range(num_nodes))
        rng.shuffle(nodes_shuffled)
        connected_set = [nodes_shuffled[0]]
        tree_edges = set()

        for node in nodes_shuffled[1:]:
            # Connect the new node to a randomly chosen already-connected node
            parent = rng.choice(connected_set)
            u, v = min(parent, node), max(parent, node)
            tree_edges.add((u, v))
            connected_set.append(node)

        # Add tree edges to graph
        for u, v in tree_edges:
            latency = round(rng.uniform(latency_range[0], latency_range[1]), round_precision)
            graph.add_edge(u, v, latency=latency)

        # 2b. Add remaining edges uniformly at random until target_edges is reached
        all_possible_pairs = [
            (u, v)
            for u in range(num_nodes)
            for v in range(u + 1, num_nodes)
            if (u, v) not in tree_edges
        ]
        rng.shuffle(all_possible_pairs)

        needed_extra = target_edges - len(tree_edges)
        for u, v in all_possible_pairs[:needed_extra]:
            latency = round(rng.uniform(latency_range[0], latency_range[1]), round_precision)
            graph.add_edge(u, v, latency=latency)

    else:
        # Standard G(n, p) without connectivity guarantee
        for u in range(num_nodes):
            for v in range(u + 1, num_nodes):
                if rng.random() <= edge_density:
                    latency = round(rng.uniform(latency_range[0], latency_range[1]), round_precision)
                    graph.add_edge(u, v, latency=latency)

    return graph
