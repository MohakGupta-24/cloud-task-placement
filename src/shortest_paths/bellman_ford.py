"""Bellman-Ford Single-Source Shortest Path Algorithm implemented from scratch.

Supports negative edge weights and detects negative-weight cycles.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from ..graph.graph import Graph


class NegativeCycleError(Exception):
    """Exception raised when a negative-weight cycle is reachable from the source vertex."""
    pass


def bellman_ford(
    graph: Graph,
    source: int,
) -> Tuple[Dict[int, float], Dict[int, Optional[int]]]:
    """Computes single-source shortest paths using the Bellman-Ford algorithm.

    Algorithm Overview (CLRS):
      1. Initialize distance to source as 0 and all other vertices to infinity.
      2. Relax all edges |V| - 1 times:
           For each directed edge (u, v) with weight w:
             If dist[u] + w < dist[v], then dist[v] = dist[u] + w, pred[v] = u.
         (Applies early termination if no relaxation occurs in a pass).
      3. Check for negative-weight cycles:
           If any edge (u, v) can still be relaxed, a negative-weight cycle exists.

    Time Complexity:
      - Worst-case Time Complexity: O(V * E)
      - Best-case Time Complexity (early termination): O(E)
    Space Complexity:
      - O(V) auxiliary space for distances and predecessor map.

    Args:
        graph: Graph instance (directed or undirected).
        source: Source server node ID.

    Returns:
        Tuple containing:
          - distances: Dict mapping node_id -> shortest path distance from source.
          - predecessors: Dict mapping node_id -> previous node on shortest path.

    Raises:
        KeyError: If source is not in the graph.
        NegativeCycleError: If a negative-weight cycle is reachable from the source.
    """
    if not graph.has_node(source):
        raise KeyError(f"Source node {source} not present in graph")

    nodes = graph.get_nodes()
    num_nodes = len(nodes)
    distances: Dict[int, float] = {node: float("inf") for node in nodes}
    predecessors: Dict[int, Optional[int]] = {node: None for node in nodes}

    distances[source] = 0.0

    # Collect directed edges
    # For undirected graphs, an edge between u and v is treated as two directed edges: u->v and v->u
    directed_edges: List[Tuple[int, int, float]] = []
    for u in nodes:
        for v, weight in graph.neighbors(u):
            directed_edges.append((u, v, weight))

    EPSILON = 1e-9

    # 2. Relax all edges |V| - 1 times
    for _ in range(num_nodes - 1):
        updated = False
        for u, v, weight in directed_edges:
            if distances[u] != float("inf") and distances[u] + weight < distances[v] - EPSILON:
                distances[v] = distances[u] + weight
                predecessors[v] = u
                updated = True
        if not updated:
            # Early exit: no edges were relaxed in this pass
            break

    # 3. Check for negative-weight cycles (|V|-th pass)
    for u, v, weight in directed_edges:
        if distances[u] != float("inf") and distances[u] + weight < distances[v] - EPSILON:
            raise NegativeCycleError(
                f"Negative-weight cycle detected on edge ({u}, {v}) reachable from source {source}"
            )

    return distances, predecessors
