"""Unit tests verifying custom Shortest Path implementations (Dijkstra, Bellman-Ford, Floyd-Warshall) against NetworkX."""

import unittest
import networkx as nx

from src.graph.graph import Graph
from src.graph.generator import generate_cloud_topology
from src.shortest_paths.dijkstra import dijkstra, reconstruct_path
from src.shortest_paths.bellman_ford import bellman_ford, NegativeCycleError
from src.shortest_paths.floyd_warshall import floyd_warshall, reconstruct_apsp_path


def to_networkx_graph(graph: Graph) -> nx.Graph:
    """Converts a custom Graph instance to a NetworkX Graph."""
    nx_g = nx.DiGraph() if graph.directed else nx.Graph()
    for node_id in graph.get_nodes():
        nx_g.add_node(node_id, capacity=graph.get_capacity(node_id))
    for u, v, latency in graph.get_edges():
        nx_g.add_edge(u, v, weight=latency)
    return nx_g


class TestShortestPathsAgainstNetworkX(unittest.TestCase):
    def test_dijkstra_against_networkx_random_graphs(self):
        """Validates Dijkstra's single-source shortest path distances against NetworkX."""
        test_topologies = [
            {"num_nodes": 10, "density": 0.35, "seed": 42},
            {"num_nodes": 25, "density": 0.20, "seed": 77},
            {"num_nodes": 40, "density": 0.15, "seed": 105},
        ]

        for tc in test_topologies:
            graph = generate_cloud_topology(
                num_nodes=tc["num_nodes"],
                edge_density=tc["density"],
                latency_range=(1.0, 50.0),
                seed=tc["seed"],
                ensure_connected=True,
            )
            nx_g = to_networkx_graph(graph)

            # Test from multiple source nodes
            for source in [0, tc["num_nodes"] // 2, tc["num_nodes"] - 1]:
                custom_dist, custom_pred = dijkstra(graph, source)
                nx_dist, nx_paths = nx.single_source_dijkstra(nx_g, source=source, weight="weight")

                for target in graph.get_nodes():
                    self.assertAlmostEqual(
                        custom_dist[target],
                        nx_dist[target],
                        places=4,
                        msg=f"Dijkstra distance mismatch for source {source} to {target}",
                    )

                    # Verify reconstructed path cost
                    path = reconstruct_path(custom_pred, target)
                    self.assertEqual(path[0], source)
                    self.assertEqual(path[-1], target)
                    path_cost = sum(
                        graph.get_latency(path[i], path[i + 1])
                        for i in range(len(path) - 1)
                    )
                    self.assertAlmostEqual(path_cost, custom_dist[target], places=4)

    def test_bellman_ford_against_networkx(self):
        """Validates Bellman-Ford distances on random topologies against NetworkX."""
        graph = generate_cloud_topology(
            num_nodes=15,
            edge_density=0.30,
            latency_range=(1.0, 30.0),
            seed=42,
            ensure_connected=True,
        )
        nx_g = to_networkx_graph(graph)

        source = 0
        custom_dist, _ = bellman_ford(graph, source)
        nx_dist = nx.single_source_bellman_ford_path_length(nx_g, source=source, weight="weight")

        for target in graph.get_nodes():
            self.assertAlmostEqual(
                custom_dist[target],
                nx_dist[target],
                places=4,
                msg=f"Bellman-Ford mismatch for {source} -> {target}",
            )

    def test_bellman_ford_negative_cycle_detection(self):
        """Validates that Bellman-Ford correctly detects reachable negative-weight cycles."""
        # Directed graph with a negative cycle: 1 -> 2 -> 3 -> 1 with sum = -2
        g_neg = Graph(directed=True)
        g_neg.add_node(0)
        g_neg.add_node(1)
        g_neg.add_node(2)
        g_neg.add_node(3)
        g_neg.add_edge(0, 1, latency=5.0)
        g_neg.add_edge(1, 2, latency=2.0)
        g_neg.add_edge(2, 3, latency=3.0)
        g_neg.add_edge(3, 1, latency=-7.0, allow_negative=True)  # Cycle 1-2-3-1 weight = 2 + 3 - 7 = -2

        with self.assertRaises(NegativeCycleError):
            bellman_ford(g_neg, source=0)

        # NetworkX verification
        nx_neg = nx.DiGraph()
        nx_neg.add_edge(0, 1, weight=5.0)
        nx_neg.add_edge(1, 2, weight=2.0)
        nx_neg.add_edge(2, 3, weight=3.0)
        nx_neg.add_edge(3, 1, weight=-7.0)

        with self.assertRaises(nx.NetworkXUnbounded):
            nx.single_source_bellman_ford(nx_neg, source=0, weight="weight")

    def test_floyd_warshall_against_networkx_random_graphs(self):
        """Validates Floyd-Warshall APSP distance matrix against NetworkX."""
        test_topologies = [
            {"num_nodes": 8, "density": 0.40, "seed": 11},
            {"num_nodes": 20, "density": 0.25, "seed": 55},
        ]

        for tc in test_topologies:
            graph = generate_cloud_topology(
                num_nodes=tc["num_nodes"],
                edge_density=tc["density"],
                latency_range=(1.0, 40.0),
                seed=tc["seed"],
                ensure_connected=True,
            )
            nx_g = to_networkx_graph(graph)

            custom_dist, custom_pred = floyd_warshall(graph)
            nx_dist = dict(nx.floyd_warshall(nx_g, weight="weight"))

            nodes = graph.get_nodes()
            for u in nodes:
                for v in nodes:
                    self.assertAlmostEqual(
                        custom_dist[u][v],
                        nx_dist[u][v],
                        places=4,
                        msg=f"Floyd-Warshall distance mismatch between {u} and {v}",
                    )

            # Test path reconstruction
            u, v = 0, tc["num_nodes"] - 1
            path = reconstruct_apsp_path(custom_pred, u, v)
            if u != v:
                self.assertEqual(path[0], u)
                self.assertEqual(path[-1], v)
                cost = sum(graph.get_latency(path[i], path[i + 1]) for i in range(len(path) - 1))
                self.assertAlmostEqual(cost, custom_dist[u][v], places=4)

    def test_cross_algorithm_consistency(self):
        """Verifies that Dijkstra, Bellman-Ford, and Floyd-Warshall yield identical distance matrices."""
        graph = generate_cloud_topology(
            num_nodes=15,
            edge_density=0.25,
            latency_range=(2.0, 30.0),
            seed=999,
            ensure_connected=True,
        )

        fw_dist, _ = floyd_warshall(graph)

        for s in graph.get_nodes():
            dijk_dist, _ = dijkstra(graph, s)
            bf_dist, _ = bellman_ford(graph, s)

            for target in graph.get_nodes():
                self.assertAlmostEqual(dijk_dist[target], fw_dist[s][target], places=4)
                self.assertAlmostEqual(bf_dist[target], fw_dist[s][target], places=4)


if __name__ == "__main__":
    unittest.main()
