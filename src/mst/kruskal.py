"""Kruskal's Minimum Spanning Tree Algorithm implemented from scratch.

Uses Disjoint Set Union (Union-Find) with path compression and union by rank.
"""

from __future__ import annotations
from typing import List, Tuple
from ..graph.graph import Graph
from ..graph.disjoint_set import DisjointSetUnion


def kruskal_mst(graph: Graph) -> Tuple[List[Tuple[int, int, float]], float]:
    """Computes the Minimum Spanning Tree (MST) of a graph using Kruskal's algorithm.

    Algorithm Overview:
      1. Collect all unique edges from the graph.
      2. Sort edges in non-decreasing order of latency/weight.
      3. Initialize a Disjoint Set Union (DSU) with all nodes.
      4. Greedily add edge (u, v) if u and v are in different sets (avoiding cycles).
      5. Terminate when (V - 1) edges are added or all edges are examined.

    Time Complexity:
      - Edge sorting: O(E log E) = O(E log V)
      - DSU Operations: O(E * alpha(V)), where alpha is the inverse Ackermann function
      - Total Time Complexity: O(E log V)
    Space Complexity:
      - O(V + E) for edge list, MST output, and DSU data structures.

    Args:
        graph: An undirected Graph instance.

    Returns:
        Tuple containing:
          - mst_edges: List of edges in the MST as (u, v, latency) with u < v.
          - total_weight: Sum of weights of edges in the MST.
    """
    if graph.num_nodes <= 1:
        return [], 0.0

    # 1. Collect all undirected edges (u < v)
    edges = graph.get_edges()

    # 2. Sort edges by latency (weight) non-decreasingly
    # O(E log E) = O(E log V)
    edges.sort(key=lambda edge: edge[2])

    # 3. Initialize DSU for all nodes
    dsu = DisjointSetUnion(graph.get_nodes())

    mst_edges: List[Tuple[int, int, float]] = []
    total_weight: float = 0.0
    target_edges = graph.num_nodes - 1

    # 4. Greedily add edges that connect disjoint components
    for u, v, weight in edges:
        if dsu.union(u, v):
            mst_edges.append((min(u, v), max(u, v), weight))
            total_weight += weight
            if len(mst_edges) == target_edges:
                break

    return mst_edges, round(total_weight, 6)
