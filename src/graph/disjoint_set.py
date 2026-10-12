"""Disjoint Set Union (Union-Find) Data Structure with Path Compression and Union by Rank.

Implemented from scratch to support Kruskal's Minimum Spanning Tree algorithm.
"""

from __future__ import annotations
from typing import Dict, Iterable, List


class DisjointSetUnion:
    """Disjoint Set Union (DSU) / Union-Find data structure.

    Optimizations:
      - Path compression in `find()`
      - Union by rank in `union()`

    Time Complexity:
      - Initialization: O(V)
      - Find: O(alpha(V)) amortized, where alpha is the inverse Ackermann function
      - Union: O(alpha(V)) amortized
      - Connected: O(alpha(V)) amortized
    Space Complexity:
      - O(V) auxiliary space to store parent and rank tables
    """

    def __init__(self, elements: Iterable[int]) -> None:
        """Initializes a disjoint set with each element as its own representative.

        Args:
            elements: An iterable of unique node IDs.

        Time Complexity: O(V) where V = len(elements)
        Space Complexity: O(V)
        """
        self._parent: Dict[int, int] = {}
        self._rank: Dict[int, int] = {}
        self.num_sets: int = 0

        for elem in elements:
            elem_id = int(elem)
            if elem_id not in self._parent:
                self._parent[elem_id] = elem_id
                self._rank[elem_id] = 0
                self.num_sets += 1

    def find(self, x: int) -> int:
        """Finds the root representative of the set containing element x with path compression.

        Args:
            x: Element ID.

        Returns:
            The canonical representative of the set containing x.

        Time Complexity: O(alpha(V)) amortized
        Space Complexity: O(alpha(V)) recursion stack space (or O(1) iterative)
        """
        x = int(x)
        if x not in self._parent:
            raise KeyError(f"Element {x} not present in DisjointSetUnion")

        # Two-pass iterative path compression
        root = x
        while self._parent[root] != root:
            root = self._parent[root]

        curr = x
        while curr != root:
            parent = self._parent[curr]
            self._parent[curr] = root
            curr = parent

        return root

    def union(self, x: int, y: int) -> bool:
        """Merges the sets containing x and y using union by rank.

        Args:
            x: First element ID.
            y: Second element ID.

        Returns:
            True if elements were in separate sets and are now merged;
            False if they were already in the same set (a cycle would form).

        Time Complexity: O(alpha(V)) amortized
        Space Complexity: O(1)
        """
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x == root_y:
            return False  # Already in same set

        # Attach smaller rank tree under root of higher rank tree
        if self._rank[root_x] < self._rank[root_y]:
            self._parent[root_x] = root_y
        elif self._rank[root_x] > self._rank[root_y]:
            self._parent[root_y] = root_x
        else:
            self._parent[root_y] = root_x
            self._rank[root_x] += 1

        self.num_sets -= 1
        return True

    def connected(self, x: int, y: int) -> bool:
        """Checks whether elements x and y belong to the same component.

        Time Complexity: O(alpha(V)) amortized
        Space Complexity: O(1)
        """
        return self.find(x) == self.find(y)

    def __len__(self) -> int:
        """Returns total number of disjoint sets."""
        return self.num_sets
