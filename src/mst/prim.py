"""Prim's Minimum Spanning Tree Algorithm implemented from scratch.

Uses custom indexed Binary Min-Heap Priority Queue.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
from ..graph.graph import Graph
from ..graph.min_heap import MinHeap


def prim_mst(
    graph: Graph,
    start_node: Optional[int] = None,
) -> Tuple[List[Tuple[int, int, float]], float]:
    """Computes the Minimum Spanning Tree (MST) of a connected graph using Prim's algorithm.

    Algorithm Overview (CLRS):
      1. Initialize keys of all vertices to infinity (except start vertex = 0).
      2. Insert all vertices into an indexed Min-Heap keyed by minimal connecting edge weight.
      3. Repeatedly extract the vertex u with minimal key.
      4. For each adjacent vertex v, if v is still in the heap and edge weight(u, v) < key[v],
         update parent[v] = u and decrease_key(v, weight(u, v)).
      5. Construct the MST edges from parent links.

    Time Complexity:
      - Inserting V vertices into heap: O(V log V)
      - V extract-min operations: O(V log V)
      - E decrease-key updates: O(E log V)
      - Total Time Complexity: O((V + E) log V)
    Space Complexity:
      - O(V) auxiliary space for MinHeap, parent pointers, and key mappings.

    Args:
        graph: An undirected Graph instance.
        start_node: Optional starting vertex. Defaults to the minimum node ID.

    Returns:
        Tuple containing:
          - mst_edges: List of edges in the MST as (u, v, latency) with u < v.
          - total_weight: Sum of weights of edges in the MST.
    """
    nodes = graph.get_nodes()
    if len(nodes) <= 1:
        return [], 0.0

    if start_node is None:
        start_node = nodes[0]
    elif not graph.has_node(start_node):
        raise KeyError(f"start_node {start_node} does not exist in graph")

    heap = MinHeap()
    parent: Dict[int, Optional[int]] = {}
    key: Dict[int, float] = {}
    in_mst: Set[int] = set()

    for node_id in nodes:
        k = 0.0 if node_id == start_node else float("inf")
        key[node_id] = k
        parent[node_id] = None
        heap.push(node_id, k)

    mst_edges: List[Tuple[int, int, float]] = []
    total_weight: float = 0.0

    while not heap.is_empty():
        u, min_k = heap.pop()
        in_mst.add(u)

        if parent[u] is not None:
            edge_weight = graph.get_latency(parent[u], u)
            mst_edges.append((min(parent[u], u), max(parent[u], u), edge_weight))
            total_weight += edge_weight

        for v, weight in graph.neighbors(u):
            if v not in in_mst and weight < key[v]:
                key[v] = weight
                parent[v] = u
                heap.decrease_key(v, weight)

    return mst_edges, round(total_weight, 6)
