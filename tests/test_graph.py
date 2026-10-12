"""Unit tests for the Adjacency-list Graph class."""

import os
import tempfile
import unittest

from src.graph.graph import Graph, Node


class TestGraph(unittest.TestCase):
    def setUp(self):
        self.graph = Graph(directed=False)

    def test_add_nodes_and_capacities(self):
        self.graph.add_node(0, capacity=120.0, region="us-east-1")
        self.graph.add_node(1, capacity=250.5, region="us-west-2")

        self.assertEqual(self.graph.num_nodes, 2)
        self.assertEqual(self.graph.get_capacity(0), 120.0)
        self.assertEqual(self.graph.get_capacity(1), 250.5)
        self.assertEqual(self.graph.get_node(0).metadata["region"], "us-east-1")

    def test_add_undirected_edges(self):
        self.graph.add_edge(0, 1, latency=15.5)
        
        self.assertTrue(self.graph.has_edge(0, 1))
        self.assertTrue(self.graph.has_edge(1, 0))
        self.assertEqual(self.graph.get_latency(0, 1), 15.5)
        self.assertEqual(self.graph.get_latency(1, 0), 15.5)
        self.assertEqual(self.graph.num_edges, 1)

    def test_add_directed_edges(self):
        dir_graph = Graph(directed=True)
        dir_graph.add_edge(0, 1, latency=10.0)

        self.assertTrue(dir_graph.has_edge(0, 1))
        self.assertFalse(dir_graph.has_edge(1, 0))
        self.assertEqual(dir_graph.num_edges, 1)

    def test_invalid_edges_and_nodes(self):
        # Self loop error
        with self.assertRaises(ValueError):
            self.graph.add_edge(0, 0, latency=5.0)

        # Negative latency error
        with self.assertRaises(ValueError):
            self.graph.add_edge(0, 1, latency=-1.0)

        # Negative capacity error
        with self.assertRaises(ValueError):
            self.graph.add_node(0, capacity=-10.0)
            self.graph.set_capacity(0, -10.0)

        # Non-existent node query error
        with self.assertRaises(KeyError):
            self.graph.get_capacity(99)

        with self.assertRaises(KeyError):
            self.graph.get_latency(99, 100)

    def test_edge_removal_and_degrees(self):
        self.graph.add_edge(0, 1, latency=5.0)
        self.graph.add_edge(0, 2, latency=7.0)

        self.assertEqual(self.graph.degree(0), 2)
        self.assertEqual(self.graph.degree(1), 1)

        self.graph.remove_edge(0, 1)
        self.assertFalse(self.graph.has_edge(0, 1))
        self.assertEqual(self.graph.degree(0), 1)
        self.assertEqual(self.graph.num_edges, 1)

    def test_connectivity_check(self):
        # Empty graph is trivially connected
        self.assertTrue(self.graph.is_connected())

        # Single node is connected
        self.graph.add_node(0)
        self.assertTrue(self.graph.is_connected())

        # Disconnected components
        self.graph.add_node(1)
        self.assertFalse(self.graph.is_connected())

        # Connect them
        self.graph.add_edge(0, 1, latency=10.0)
        self.assertTrue(self.graph.is_connected())

        # Add isolated 3rd node
        self.graph.add_node(2)
        self.assertFalse(self.graph.is_connected())
        self.graph.add_edge(1, 2, latency=12.0)
        self.assertTrue(self.graph.is_connected())

    def test_json_serialization_roundtrip(self):
        self.graph.add_node(0, capacity=100.0, label="alpha")
        self.graph.add_node(1, capacity=200.0, label="beta")
        self.graph.add_edge(0, 1, latency=14.2)

        data = self.graph.to_dict()
        reconstructed = Graph.from_dict(data)

        self.assertEqual(reconstructed.num_nodes, 2)
        self.assertEqual(reconstructed.num_edges, 1)
        self.assertEqual(reconstructed.get_capacity(0), 100.0)
        self.assertEqual(reconstructed.get_latency(0, 1), 14.2)
        self.assertEqual(reconstructed.get_node(1).metadata["label"], "beta")

        # Test file persistence
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.graph.save_to_json(tmp_path)
            loaded = Graph.load_from_json(tmp_path)
            self.assertEqual(loaded.num_nodes, self.graph.num_nodes)
            self.assertEqual(loaded.num_edges, self.graph.num_edges)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
