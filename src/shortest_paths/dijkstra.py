"""Dijkstra's Single-Source Shortest Path (SSSP) Algorithm implemented from scratch.

Uses custom indexed Binary Min-Heap Priority Queue.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from ..graph.graph import Graph
from ..graph.min_heap import MinHeap


def dijkstra(
    graph: Graph,
    source: int,
) -> Tuple[Dict[int, float], Dict[int, Optional[int]]]:
    """Computes single-source shortest paths from `source` to all nodes using Dijkstra's algorithm.

    Algorithm Overview (CLRS):
      1. Initialize distance to source as 0 and all other nodes to infinity.
      2. Insert all vertices into an indexed Min-Heap.
      3. Repeatedly extract vertex u with minimal known distance.
      4. For each adjacent link (u, v) with weight w:
         Relax edge: if dist[u] + w < dist[v], update dist[v] and decrease_key(v).
      5. Repeat until the heap is empty.

    Time Complexity:
      - Heap initialization: O(V log V)
      - V extract-min operations: O(V log V)
      - E edge relaxation decrease-key operations: O(E log V)
      - Total Time Complexity: O((V + E) log V)
    Space Complexity:
      - O(V) auxiliary space for distances, predecessor map, and min-heap.

    Args:
        graph: Graph instance (directed or undirected) with non-negative edge weights.
        source: Source server node ID.

    Returns:
        Tuple containing:
          - distances: Dict mapping node_id -> shortest path distance from source (inf if unreachable).
          - predecessors: Dict mapping node_id -> previous node on shortest path (None for source/unreachable).

    Raises:
        KeyError: If source is not in the graph.
        ValueError: If any negative edge weight is detected along traversed edges.
    """
    if not graph.has_node(source):
        raise KeyError(f"Source node {source} not present in graph")

    nodes = graph.get_nodes()
    distances: Dict[int, float] = {node: float("inf") for node in nodes}
    predecessors: Dict[int, Optional[int]] = {node: None for node in nodes}

    distances[source] = 0.0

    heap = MinHeap()
    for node in nodes:
        heap.push(node, distances[node])

    while not heap.is_empty():
        u, d_u = heap.pop()

        if d_u == float("inf"):
            # Remaining nodes in heap are unreachable from source
            break

        for v, weight in graph.neighbors(u):
            if weight < 0:
                raise ValueError(
                    f"Dijkstra's algorithm cannot handle negative edge weights: link ({u}, {v}) has weight {weight}"
                )

            new_dist = d_u + weight
            if new_dist < distances[v]:
                distances[v] = new_dist
                predecessors[v] = u
                heap.decrease_key(v, new_dist)

    return distances, predecessors


def reconstruct_path(predecessors: Dict[int, Optional[int]], target: int) -> List[int]:
    """Reconstructs the shortest path from source to target using predecessor map.

    Args:
        predecessors: Predecessor mapping returned by dijkstra or bellman_ford.
        target: Target destination node.

    Returns:
        List of node IDs from source to target, or empty list if target is unreachable.

    Time Complexity: O(V)
    Space Complexity: O(V)
    """
    if target not in predecessors:
        return []

    path: List[int] = []
    curr: Optional[int] = target
    while curr is not None:
        path.append(curr)
        curr = predecessors[curr]

    path.reverse()
    # If path only contains target and target's predecessor is None,
    # verify if target was indeed the source or unreachable
    if len(path) == 1 and predecessors[target] is None:
        return path

    return path
