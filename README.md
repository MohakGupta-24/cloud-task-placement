# Cloud Task Placement: Routing & Resource Allocation Suite

**Course**: Design and Analysis of Algorithms (DAA) — Problem-Based Learning (PBL)  
**Assigned Topic**: Problem 3 — Cloud Task Placement  
**Team (Group 3)**:
- Naman Singla (`25WU0101084`)
- Mohak Gupta (`25WU0101074`)
- Mohammed Amaan Khan (`25WU0101075`)

---

## 1. Problem Synopsis

In distributed multi-region cloud and edge computing environments, client requests and virtual machine (VM) replicas / microservices must be placed across physical server nodes under strict physical constraints:

1. **Capacity Constraints**: Each physical server has finite computing capacity ($C_v$) such as CPU cores, RAM, and VM slots.
2. **Backbone & Routing Latency**: Network links between servers exhibit propagation and transmission delays (latencies $w(u, v)$).
3. **Core Algorithmic Suite**:
   - **Minimum Spanning Tree (MST - Kruskal / Prim)**: Identifies the minimal-latency backbone tree connecting all datacenters with zero redundant cycles.
   - **Shortest Paths (Dijkstra / Bellman-Ford / Floyd-Warshall / Johnson)**: Computes single-source and all-pairs minimal communication routing delays between clients and host servers.
   - **Dynamic Programming (0-1 Knapsack Variant)**: Selects optimal task subsets to place on servers to maximize accepted workload/utility while strictly observing capacity limits.
   - **Greedy Schedulers**: Provide fast baseline heuristics to benchmark against the exact DP solutions.

> **Zero-External-Solver Guarantee**: All graph representations, priority queues, disjoint-set data structures, and core algorithms are implemented **strictly from scratch** in pure Python.

---

## 2. Repository Structure

```text
cloud-task-placement/
│
├── README.md                      # Project documentation and setup instructions
├── requirements.txt               # Testing and visualization dependencies
├── generate_datasets.py           # CLI generator for benchmark datasets
│
├── src/                           # Pure Python source code (from scratch)
│   ├── __init__.py
│   └── graph/                     # Graph primitives and topology generator
│       ├── __init__.py
│       ├── graph.py               # Adjacency-list Graph and Node classes
│       └── generator.py           # Synthetic cloud network topology generator
│
├── data/                          # Benchmark dataset topologies
│   ├── small_topology.json        # 10 servers, 16 links, edge cluster
│   ├── medium_topology.json       # 50 servers, 184 links, regional datacenter network
│   └── large_topology.json        # 200 servers, 995 links, cloud backbone network
│
├── tests/                         # Unit tests
│   ├── __init__.py
│   ├── test_graph.py              # Tests for Graph mutations, capacity, latency, JSON I/O
│   └── test_generator.py          # Tests for seed reproducibility, connectivity, bounds
│
├── experiments/                   # Performance & empirical scaling scripts (Stage 5)
├── notebooks/                     # Interactive exploration & visual dashboards (Stage 6)
└── report/                        # Technical report & LaTeX documents (10-12 pages)
```

---

## 3. Getting Started & Running

### Requirements
- Python 3.10+ (tested on Python 3.14)
- Standard library (zero external dependencies required for Stage 1)

Optional dependencies for testing and upcoming visual dashboards:
```bash
pip install -r requirements.txt
```

### Running the Test Suite
Run the built-in test runner across all tests in `tests/`:

```bash
python -m unittest discover -s tests -v
```

Or using `pytest`:
```bash
pytest -v tests/
```

### Generating Benchmark Datasets
To regenerate or inspect the three default topologies in `/data`:

```bash
python generate_datasets.py
```

### Using the Graph & Generator in Python
```python
from src.graph.generator import generate_cloud_topology
from src.graph.graph import Graph

# 1. Generate a reproducible 25-node cloud network
network = generate_cloud_topology(
    num_nodes=25,
    edge_density=0.20,
    latency_range=(2.0, 50.0),      # ms
    capacity_range=(100.0, 500.0),  # compute units
    seed=42,
    ensure_connected=True,
)

print(network)
# Output: Graph(nodes=25, edges=60, directed=False)

# 2. Inspect node attributes and incident links
print("Server 0 capacity:", network.get_capacity(0))
for neighbor, latency in network.neighbors(0):
    print(f"  -> Link to Server {neighbor}: {latency} ms")

# 3. Save / Load from JSON
network.save_to_json("data/custom_topology.json")
loaded_network = Graph.load_from_json("data/custom_topology.json")
```

### Running the End-to-End Placement Optimizer Demo
Execute the full optimization pipeline (MST backbone + Floyd-Warshall routing + 0-1 Knapsack DP placement + metrics table):

```bash
python run_demo.py
```

---

## 4. Benchmark Datasets (in `/data`)

| Dataset | Nodes ($|V|$) | Edges ($|E|$) | Edge Density | Latency Range (ms) | Server Capacity | Connected |
|---|---|---|---|---|---|---|
| `small_topology.json` | 10 | 16 | 0.35 | 1.0 – 25.0 | 50 – 200 | Yes |
| `medium_topology.json` | 50 | 184 | 0.15 | 2.0 – 75.0 | 100 – 500 | Yes |
| `large_topology.json` | 200 | 995 | 0.05 | 5.0 – 150.0 | 200 – 1000 | Yes |

---

## 5. Implementation Roadmap

- [x] **Stage 1**: Repository skeleton, custom Adjacency List Graph, reproducible synthetic topology generator, sample datasets, and unit test suite.
- [x] **Stage 2**: From-scratch Priority Queue (Min-Heap), Disjoint Set Union (DSU), MST algorithms (Prim & Kruskal), and Shortest Paths (Dijkstra, Bellman-Ford, Floyd-Warshall).
- [x] **Stage 3**: 0-1 Knapsack Dynamic Programming & Greedy placement heuristics.
- [x] **Stage 4**: End-to-end task placement optimizer (`CloudPlacementOptimizer`), routing tables, cost/benefit tables, and runnable demo (`run_demo.py`).
- [ ] **Stage 5**: Complexity benchmarks, empirical runtime validation, and robustness under link failures.
- [ ] **Stage 6**: Interactive visual dashboard and 10–12 page technical report.
