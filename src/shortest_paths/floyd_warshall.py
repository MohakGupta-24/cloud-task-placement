"""Floyd-Warshall All-Pairs Shortest Path (APSP) Algorithm implemented from scratch.

Computes the shortest paths between all pairs of vertices via Dynamic Programming.
Detects negative-weight cycles if any diagonal entry dist[i][i] < 0.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from ..graph.graph import Graph
from .bellman_ford import NegativeCycleError


def floyd_warshall(
    graph: Graph,
) -> Tuple[Dict[int, Dict[int, float]], Dict[int, Dict[int, Optional[int]]]]:
    """Computes All-Pairs Shortest Paths (APSP) using the Floyd-Warshall DP algorithm.

    Algorithm Overview (CLRS DP Formulation):
      Let d^{(k)}[i][j] be the shortest path from i to j using intermediate vertices
      only from {1, 2, ..., k}.
      Base Case:
        d^{(0)}[i][i] = 0
        d^{(0)}[i][j] = weight(i, j) if (i, j) in E, else infinity
      Recurrence:
        d^{(k)}[i][j] = min( d^{(k-1)}[i][j], d^{(k-1)}[i][k] + d^{(k-1)}[k][j] )

    Time Complexity:
      - Triple nested loops over V vertices: O(V^3)
      - Total Time Complexity: O(V^3)
    Space Complexity:
      - O(V^2) auxiliary space for distance matrix and predecessor matrix.

    Args:
        graph: Graph instance (directed or undirected).

    Returns:
        Tuple containing:
          - dist: 2D dictionary where dist[u][v] is shortest distance from u to v.
          - pred: 2D dictionary where pred[u][v] is the predecessor of v on shortest path from u.

    Raises:
        NegativeCycleError: If any vertex is part of a negative-weight cycle (dist[i][i] < 0).
    """
    nodes = graph.get_nodes()
    
    # 1. Initialize distance and predecessor matrices
    dist: Dict[int, Dict[int, float]] = {u: {v: float("inf") for v in nodes} for u in nodes}
    pred: Dict[int, Dict[int, Optional[int]]] = {u: {v: None for v in nodes} for u in nodes}

    for u in nodes:
        dist[u][u] = 0.0
        for v, weight in graph.neighbors(u):
            # In case of multiple edges (though graph enforces single), take min
            if weight < dist[u][v]:
                dist[u][v] = weight
                pred[u][v] = u

    # 2. Dynamic Programming recurrence: iterate through each intermediate vertex k
    for k in nodes:
        for i in nodes:
            d_ik = dist[i][k]
            if d_ik == float("inf"):
                continue  # Skip unreachable path through k

            for j in nodes:
                d_kj = dist[k][j]
                if d_kj == float("inf"):
                    continue

                new_dist = d_ik + d_kj
                if new_dist < dist[i][j] - 1e-9:
                    dist[i][j] = new_dist
                    pred[i][j] = pred[k][j]

    # 3. Detect negative-weight cycles
    for i in nodes:
        if dist[i][i] < -1e-9:
            raise NegativeCycleError(
                f"Negative-weight cycle detected in graph: dist[{i}][{i}] = {dist[i][i]}"
            )

    return dist, pred


def reconstruct_apsp_path(
    pred: Dict[int, Dict[int, Optional[int]]],
    u: int,
    v: int,
) -> List[int]:
    """Reconstructs the shortest path from u to v using the Floyd-Warshall predecessor matrix.

    Time Complexity: O(V)
    Space Complexity: O(V)
    """
    if u == v:
        return [u]
    if pred[u][v] is None:
        return []

    path = [v]
    curr = v
    while curr != u:
        curr = pred[u][curr]
        if curr is None:
            return []
        path.append(curr)

    path.reverse()
    return path
