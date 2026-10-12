"""Indexed Binary Min-Heap Priority Queue.

Implemented strictly from scratch for Dijkstra's and Prim's algorithms,
supporting O(log N) push, pop, and decrease_key operations.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


class MinHeap:
    """Indexed Binary Min-Heap Priority Queue.

    Maintains a binary heap where each entry is (priority, item).
    Maintains an index position mapping to enable O(log N) decrease_key.

    Time Complexity:
      - Push: O(log N)
      - Pop (extract-min): O(log N)
      - Decrease Key: O(log N)
      - Peek: O(1)
      - Contains: O(1)
    Space Complexity:
      - O(N) auxiliary space to store heap array and position index
    """

    def __init__(self) -> None:
        # Heap entries: List of [priority, item]
        self._heap: List[List[Any]] = []
        # Mapping item -> current index in self._heap
        self._pos: Dict[Any, int] = {}

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        """Returns True if the heap contains no elements."""
        return len(self._heap) == 0

    def contains(self, item: Any) -> bool:
        """Checks if an item is currently present in the heap in O(1) time."""
        return item in self._pos

    def peek(self) -> Tuple[Any, float]:
        """Returns the (item, min_priority) without removing it.

        Time Complexity: O(1)
        """
        if self.is_empty():
            raise IndexError("peek from empty MinHeap")
        priority, item = self._heap[0]
        return item, priority

    def push(self, item: Any, priority: float) -> None:
        """Inserts a new item with given priority into the min-heap.

        If the item already exists and new priority is smaller, updates priority (decrease_key).

        Time Complexity: O(log N)
        Space Complexity: O(1) auxiliary
        """
        if item in self._pos:
            self.decrease_key(item, priority)
            return

        idx = len(self._heap)
        self._heap.append([priority, item])
        self._pos[item] = idx
        self._sift_up(idx)

    def pop(self) -> Tuple[Any, float]:
        """Removes and returns the item with the smallest priority.

        Returns:
            Tuple of (item, priority).

        Time Complexity: O(log N)
        Space Complexity: O(1) auxiliary
        """
        if self.is_empty():
            raise IndexError("pop from empty MinHeap")

        min_entry = self._heap[0]
        min_priority, min_item = min_entry[0], min_entry[1]
        last_entry = self._heap.pop()
        del self._pos[min_item]

        if not self.is_empty():
            self._heap[0] = last_entry
            self._pos[last_entry[1]] = 0
            self._sift_down(0)

        return min_item, min_priority

    def decrease_key(self, item: Any, new_priority: float) -> None:
        """Decreases the priority of an existing item in the heap.

        Args:
            item: Item already present in the heap.
            new_priority: Lower priority value.

        Time Complexity: O(log N)
        Space Complexity: O(1) auxiliary
        """
        if item not in self._pos:
            raise KeyError(f"Item {item} not present in MinHeap")

        idx = self._pos[item]
        curr_priority = self._heap[idx][0]
        if new_priority > curr_priority:
            return  # Only decrease allowed

        self._heap[idx][0] = new_priority
        self._sift_up(idx)

    def _sift_up(self, idx: int) -> None:
        """Moves element at idx up to maintain heap invariant."""
        while idx > 0:
            parent = (idx - 1) // 2
            if self._heap[idx][0] < self._heap[parent][0]:
                self._swap(idx, parent)
                idx = parent
            else:
                break

    def _sift_down(self, idx: int) -> None:
        """Moves element at idx down to maintain heap invariant."""
        size = len(self._heap)
        while True:
            smallest = idx
            left = 2 * idx + 1
            right = 2 * idx + 2

            if left < size and self._heap[left][0] < self._heap[smallest][0]:
                smallest = left
            if right < size and self._heap[right][0] < self._heap[smallest][0]:
                smallest = right

            if smallest != idx:
                self._swap(idx, smallest)
                idx = smallest
            else:
                break

    def _swap(self, i: int, j: int) -> None:
        """Swaps two elements in the heap and updates position map."""
        item_i = self._heap[i][1]
        item_j = self._heap[j][1]
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]
        self._pos[item_i] = j
        self._pos[item_j] = i
