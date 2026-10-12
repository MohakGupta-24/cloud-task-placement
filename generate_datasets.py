"""Dataset generator script for Cloud Task Placement PBL.

Generates three standard benchmark topologies:
1. small_topology.json  (10 nodes, local cluster/edge topology)
2. medium_topology.json (50 nodes, campus/metro datacenter network)
3. large_topology.json  (200 nodes, multi-region cloud backbone network)
"""

import os
import sys

# Ensure src is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.graph.generator import generate_cloud_topology


def generate_all_datasets(data_dir: str = "data") -> None:
    os.makedirs(data_dir, exist_ok=True)

    configs = [
        {
            "name": "small_topology.json",
            "num_nodes": 10,
            "edge_density": 0.35,
            "latency_range": (1.0, 25.0),
            "capacity_range": (50.0, 200.0),
            "seed": 42,
            "description": "Small 10-node edge/micro-datacenter cluster",
        },
        {
            "name": "medium_topology.json",
            "num_nodes": 50,
            "edge_density": 0.15,
            "latency_range": (2.0, 75.0),
            "capacity_range": (100.0, 500.0),
            "seed": 42,
            "description": "Medium 50-node regional datacenter network",
        },
        {
            "name": "large_topology.json",
            "num_nodes": 200,
            "edge_density": 0.05,
            "latency_range": (5.0, 150.0),
            "capacity_range": (200.0, 1000.0),
            "seed": 42,
            "description": "Large 200-node multi-region cloud backbone network",
        },
    ]

    print("Generating benchmark cloud topologies...")
    for cfg in configs:
        target_path = os.path.join(data_dir, cfg["name"])
        graph = generate_cloud_topology(
            num_nodes=cfg["num_nodes"],
            edge_density=cfg["edge_density"],
            latency_range=cfg["latency_range"],
            capacity_range=cfg["capacity_range"],
            seed=cfg["seed"],
            ensure_connected=True,
        )
        graph.save_to_json(target_path)
        print(
            f" [OK] Created {cfg['name']}: {graph.num_nodes} nodes, "
            f"{graph.num_edges} links, connected={graph.is_connected()} -> {target_path}"
        )


if __name__ == "__main__":
    generate_all_datasets()
