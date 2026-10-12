"""Unit tests verifying custom MST implementations (Prim & Kruskal) against NetworkX."""

import unittest
import networkx as nx

from src.graph.generator import generate_cloud_topology
from src.mst.kruskal import kruskal_mst
from src.mst.prim import prim_mst


def to_networkx_graph(graph) -> nx.Graph:
    """Converts a custom Graph instance to a NetworkX Graph."""
    nx_g = nx.Graph()
    for node_id in graph.get_nodes():
        nx_g.add_node(node_id, capacity=graph.get_capacity(node_id))
    for u, v, latency in graph.get_edges():
        nx_g.add_edge(u, v, weight=latency)
    return nx_g


class TestMSTAgainstNetworkX(unittest.TestCase):
    def test_kruskal_against_networkx_random_graphs(self):
        """Validates Kruskal's MST total weight and edge count against NetworkX across multiple seeds."""
        test_cases = [
            {"num_nodes": 6, "density": 0.5, "seed": 10},
            {"num_nodes": 15, "density": 0.3, "seed": 42},
            {"num_nodes": 30, "density": 0.2, "seed": 99},
            {"num_nodes": 50, "density": 0.15, "seed": 123},
        ]

        for tc in test_cases:
            graph = generate_cloud_topology(
                num_nodes=tc["num_nodes"],
                edge_density=tc["density"],
                latency_range=(1.0, 100.0),
                seed=tc["seed"],
                ensure_connected=True,
            )
            nx_g = to_networkx_graph(graph)

            # Custom Kruskal
            kruskal_edges, kruskal_weight = kruskal_mst(graph)

            # NetworkX Kruskal
            nx_mst = nx.minimum_spanning_tree(nx_g, algorithm="kruskal", weight="weight")
            nx_weight = sum(d["weight"] for _, _, d in nx_mst.edges(data=True))

            # Verifications
            self.assertEqual(len(kruskal_edges), tc["num_nodes"] - 1)
            self.assertAlmostEqual(
                kruskal_weight,
                nx_weight,
                places=4,
                msg=f"Kruskal weight mismatch on graph with {tc['num_nodes']} nodes",
            )

    def test_prim_against_networkx_random_graphs(self):
        """Validates Prim's MST total weight against NetworkX across multiple seeds."""
        test_cases = [
            {"num_nodes": 6, "density": 0.5, "seed": 10},
            {"num_nodes": 15, "density": 0.3, "seed": 42},
            {"num_nodes": 30, "density": 0.2, "seed": 99},
            {"num_nodes": 50, "density": 0.15, "seed": 123},
        ]

        for tc in test_cases:
            graph = generate_cloud_topology(
                num_nodes=tc["num_nodes"],
                edge_density=tc["density"],
                latency_range=(1.0, 100.0),
                seed=tc["seed"],
                ensure_connected=True,
            )
            nx_g = to_networkx_graph(graph)

            # Custom Prim
            prim_edges, prim_weight = prim_mst(graph)

            # NetworkX Prim
            nx_mst = nx.minimum_spanning_tree(nx_g, algorithm="prim", weight="weight")
            nx_weight = sum(d["weight"] for _, _, d in nx_mst.edges(data=True))

            # Verifications
            self.assertEqual(len(prim_edges), tc["num_nodes"] - 1)
            self.assertAlmostEqual(
                prim_weight,
                nx_weight,
                places=4,
                msg=f"Prim weight mismatch on graph with {tc['num_nodes']} nodes",
            )

    def test_kruskal_and_prim_equivalence(self):
        """Ensures that custom Kruskal and custom Prim yield identical total MST weight on all graphs."""
        for seed in [1, 7, 21, 77, 101]:
            graph = generate_cloud_topology(
                num_nodes=20,
                edge_density=0.25,
                latency_range=(5.0, 50.0),
                seed=seed,
                ensure_connected=True,
            )
            _, kruskal_weight = kruskal_mst(graph)
            _, prim_weight = prim_mst(graph)

            self.assertAlmostEqual(
                kruskal_weight,
                prim_weight,
                places=4,
                msg=f"Kruskal and Prim weight discrepancy on seed {seed}",
            )


if __name__ == "__main__":
    unittest.main()
