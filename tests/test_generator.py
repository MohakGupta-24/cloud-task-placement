"""Unit tests for the Synthetic Server Topology Generator."""

import unittest

from src.graph.generator import generate_cloud_topology


class TestTopologyGenerator(unittest.TestCase):
    def test_seed_reproducibility(self):
        g1 = generate_cloud_topology(num_nodes=20, edge_density=0.25, seed=123)
        g2 = generate_cloud_topology(num_nodes=20, edge_density=0.25, seed=123)

        self.assertEqual(g1.num_nodes, g2.num_nodes)
        self.assertEqual(g1.num_edges, g2.num_edges)
        self.assertEqual(g1.get_edges(), g2.get_edges())

        for node_id in g1.get_nodes():
            self.assertEqual(g1.get_capacity(node_id), g2.get_capacity(node_id))
            self.assertEqual(
                g1.get_node(node_id).metadata,
                g2.get_node(node_id).metadata,
            )

    def test_different_seeds_produce_different_topologies(self):
        g1 = generate_cloud_topology(num_nodes=20, edge_density=0.25, seed=111)
        g2 = generate_cloud_topology(num_nodes=20, edge_density=0.25, seed=999)

        self.assertNotEqual(g1.get_edges(), g2.get_edges())

    def test_node_count_and_connectivity(self):
        for n in [5, 15, 30]:
            g = generate_cloud_topology(num_nodes=n, edge_density=0.2, seed=42, ensure_connected=True)
            self.assertEqual(g.num_nodes, n)
            self.assertTrue(g.is_connected(), f"Graph with {n} nodes should be connected")

    def test_parameter_bounds(self):
        lat_range = (5.0, 45.0)
        cap_range = (50.0, 300.0)
        g = generate_cloud_topology(
            num_nodes=25,
            edge_density=0.3,
            latency_range=lat_range,
            capacity_range=cap_range,
            seed=42,
        )

        for u, v, lat in g.get_edges():
            self.assertGreaterEqual(lat, lat_range[0])
            self.assertLessEqual(lat, lat_range[1])

        for node_id in g.get_nodes():
            cap = g.get_capacity(node_id)
            self.assertGreaterEqual(cap, cap_range[0])
            self.assertLessEqual(cap, cap_range[1])

    def test_single_node_graph(self):
        g = generate_cloud_topology(num_nodes=1, edge_density=0.5, seed=42)
        self.assertEqual(g.num_nodes, 1)
        self.assertEqual(g.num_edges, 0)
        self.assertTrue(g.is_connected())

    def test_invalid_parameters_raise(self):
        with self.assertRaises(ValueError):
            generate_cloud_topology(num_nodes=0, edge_density=0.5)

        with self.assertRaises(ValueError):
            generate_cloud_topology(num_nodes=10, edge_density=0.0)

        with self.assertRaises(ValueError):
            generate_cloud_topology(num_nodes=10, edge_density=1.5)

        with self.assertRaises(ValueError):
            generate_cloud_topology(num_nodes=10, edge_density=0.5, latency_range=(50.0, 10.0))

        with self.assertRaises(ValueError):
            generate_cloud_topology(num_nodes=10, edge_density=0.5, capacity_range=(-5.0, 100.0))


if __name__ == "__main__":
    unittest.main()
