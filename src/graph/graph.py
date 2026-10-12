"""Adjacency-list based Graph data structure for Cloud Task Placement.

Implemented from scratch with zero external dependencies to fulfill DAA PBL requirements.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple


@dataclass
class Node:
    """Represents a physical server / data center node."""
    node_id: int
    capacity: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "capacity": self.capacity,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Node:
        return cls(
            node_id=int(data["node_id"]),
            capacity=float(data["capacity"]),
            metadata=data.get("metadata", {}),
        )


class Graph:
    """Undirected / Directed Network Graph using Adjacency Lists.
    
    Attributes:
        nodes: Mapping of node_id -> Node object.
        adj: Adjacency list mapping u -> {v: latency}.
    """

    def __init__(self, directed: bool = False):
        self.directed: bool = directed
        self._nodes: Dict[int, Node] = {}
        self._adj: Dict[int, Dict[int, float]] = {}

    @property
    def num_nodes(self) -> int:
        """Returns total number of server nodes in the graph."""
        return len(self._nodes)

    @property
    def num_edges(self) -> int:
        """Returns total number of unique links in the graph."""
        total_directed_edges = sum(len(neighbors) for neighbors in self._adj.values())
        return total_directed_edges if self.directed else total_directed_edges // 2

    def add_node(self, node_id: int, capacity: float = 100.0, **metadata: Any) -> Node:
        """Adds a server node with a specific resource capacity.
        
        Args:
            node_id: Unique integer identifier for the server.
            capacity: Total resource capacity (e.g. CPU/RAM slots).
            **metadata: Arbitrary attributes (e.g., (x, y) coordinates, region name).
        
        Returns:
            The created or updated Node object.
        """
        node_id = int(node_id)
        if capacity < 0:
            raise ValueError(f"Capacity cannot be negative: {capacity}")
        if node_id not in self._nodes:
            self._nodes[node_id] = Node(node_id=node_id, capacity=float(capacity), metadata=metadata)
            self._adj[node_id] = {}
        else:
            self._nodes[node_id].capacity = float(capacity)
            self._nodes[node_id].metadata.update(metadata)
        return self._nodes[node_id]

    def add_edge(
        self,
        u: int,
        v: int,
        latency: float,
        directed: Optional[bool] = None,
        allow_negative: bool = False,
    ) -> None:
        """Adds or updates a link with a given latency weight.
        
        Args:
            u: Source server node ID.
            v: Destination server node ID.
            latency: Network delay weight in milliseconds.
            directed: If specified, overrides the graph's default directedness.
            allow_negative: Set to True if negative weights are permitted (e.g. for Bellman-Ford tests).
        """
        u, v = int(u), int(v)
        if u == v:
            raise ValueError(f"Self-loops are not permitted in cloud topology: node {u}")
        if latency < 0 and not allow_negative:
            raise ValueError(f"Link latency cannot be negative: {latency}")

        # Ensure both nodes exist (assign default capacity 100.0 if not already added)
        if u not in self._nodes:
            self.add_node(u)
        if v not in self._nodes:
            self.add_node(v)

        is_directed = self.directed if directed is None else directed
        self._adj[u][v] = float(latency)
        if not is_directed:
            self._adj[v][u] = float(latency)

    def remove_edge(self, u: int, v: int, directed: Optional[bool] = None) -> None:
        """Removes a link between two nodes."""
        u, v = int(u), int(v)
        is_directed = self.directed if directed is None else directed
        if u in self._adj and v in self._adj[u]:
            del self._adj[u][v]
        if not is_directed and v in self._adj and u in self._adj[v]:
            del self._adj[v][u]

    def has_node(self, node_id: int) -> bool:
        """Checks if a server node exists in the network."""
        return int(node_id) in self._nodes

    def has_edge(self, u: int, v: int) -> bool:
        """Checks if a direct link exists between node u and node v."""
        u, v = int(u), int(v)
        return u in self._adj and v in self._adj[u]

    def get_latency(self, u: int, v: int) -> float:
        """Returns the latency weight of edge (u, v). Raises KeyError if no edge."""
        u, v = int(u), int(v)
        if not self.has_edge(u, v):
            raise KeyError(f"No direct link between server {u} and server {v}")
        return self._adj[u][v]

    def get_capacity(self, node_id: int) -> float:
        """Returns the resource capacity of a server node."""
        node_id = int(node_id)
        if node_id not in self._nodes:
            raise KeyError(f"Node {node_id} does not exist in graph")
        return self._nodes[node_id].capacity

    def set_capacity(self, node_id: int, capacity: float) -> None:
        """Updates the resource capacity of a server node."""
        node_id = int(node_id)
        if node_id not in self._nodes:
            raise KeyError(f"Node {node_id} does not exist in graph")
        if capacity < 0:
            raise ValueError(f"Capacity cannot be negative: {capacity}")
        self._nodes[node_id].capacity = float(capacity)

    def get_node(self, node_id: int) -> Node:
        """Returns the Node object for a given node_id."""
        node_id = int(node_id)
        if node_id not in self._nodes:
            raise KeyError(f"Node {node_id} does not exist in graph")
        return self._nodes[node_id]

    def neighbors(self, node_id: int) -> List[Tuple[int, float]]:
        """Returns a list of (neighbor_id, latency) tuples for node_id."""
        node_id = int(node_id)
        if node_id not in self._adj:
            raise KeyError(f"Node {node_id} does not exist in graph")
        return list(self._adj[node_id].items())

    def degree(self, node_id: int) -> int:
        """Returns the degree (number of connected incident links) of a node."""
        node_id = int(node_id)
        if node_id not in self._adj:
            raise KeyError(f"Node {node_id} does not exist in graph")
        return len(self._adj[node_id])

    def get_nodes(self) -> List[int]:
        """Returns a sorted list of all node IDs."""
        return sorted(self._nodes.keys())

    def get_edges(self) -> List[Tuple[int, int, float]]:
        """Returns all edges as (u, v, latency) tuples.
        
        For undirected graphs, each edge is reported once with u < v.
        """
        edges: List[Tuple[int, int, float]] = []
        for u in sorted(self._adj.keys()):
            for v in sorted(self._adj[u].keys()):
                if self.directed or u < v:
                    edges.append((u, v, self._adj[u][v]))
        return edges

    def is_connected(self) -> bool:
        """Checks if all nodes are mutually reachable via Breadth-First Search (BFS).
        
        Returns:
            True if graph is connected (or empty), False otherwise.
        """
        if self.num_nodes <= 1:
            return True

        start_node = next(iter(self._nodes.keys()))
        visited: Set[int] = {start_node}
        queue: List[int] = [start_node]

        while queue:
            curr = queue.pop(0)
            for neighbor, _ in self._adj[curr].items():
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return len(visited) == self.num_nodes

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the graph topology and attributes into a dictionary."""
        return {
            "directed": self.directed,
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "edges": [
                {"u": u, "v": v, "latency": latency}
                for u, v, latency in self.get_edges()
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Graph:
        """Reconstructs a Graph instance from a serialized dictionary."""
        g = cls(directed=data.get("directed", False))
        for node_data in data.get("nodes", []):
            node = Node.from_dict(node_data)
            g.add_node(node.node_id, capacity=node.capacity, **node.metadata)
        for edge_data in data.get("edges", []):
            g.add_edge(
                u=edge_data["u"],
                v=edge_data["v"],
                latency=edge_data["latency"],
            )
        return g

    def save_to_json(self, filepath: str) -> None:
        """Saves graph to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_json(cls, filepath: str) -> Graph:
        """Loads a Graph from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def __repr__(self) -> str:
        return f"Graph(nodes={self.num_nodes}, edges={self.num_edges}, directed={self.directed})"
