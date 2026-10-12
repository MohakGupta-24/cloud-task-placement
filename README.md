# Cloud Task Placement: Routing & Resource Allocation Suite

**Course**: Design and Analysis of Algorithms (DAA) — Problem-Based Learning (PBL)  
**Assigned Topic**: Problem 3 — Cloud Task Placement  
**Team (Group 3)**:
- Naman Singla (`25WU0101084`)
- Mohak Gupta (`25WU0101074`)
- Mohammed Amaan Khan (`25WU0101075`)

---

## 1. Problem Synopsis & Mathematical Model

In distributed multi-region cloud and edge computing environments, client requests and virtual machine (VM) replicas / microservices must be placed across physical server nodes under strict physical capacity and communication constraints:

1. **Fleet Topology & Capacity Constraints**:
   - The cloud network is modeled as an undirected, weighted graph $G = (V, E)$, where each vertex $v \in V$ represents a server with compute capacity $C_v$.
   - Network links $(u, v) \in E$ exhibit physical propagation and transmission latencies $w(u, v) > 0$.
2. **Workload & Candidate Hosting**:
   - Each client task $t_j = (u_j, d_j, \tau_j, \rho_j)$ specifies client ingress node $u_j$, capacity demand $d_j$, access traffic volume $\tau_j$, and state replication traffic volume $\rho_j$.
   - **Flexible Hosting**: A task $t_j$ may be hosted on **any server** $s \in V$ that possesses sufficient remaining capacity ($c_s \ge d_j$).
3. **Composite Placement Cost & MST Synchronization**:
   - Placed tasks incur both client access latency and state synchronization overhead along the Minimum Spanning Tree (MST) communication backbone to the traffic-weighted median **Sync Hub** $h^*$:
     $$J(t_j, s) = \tau_j \cdot D[u_j, s] + \lambda \cdot \rho_j \cdot D_{\text{MST}}[s, h^*]$$
   - Parameter $\lambda \ge 0$ balances client access latency against distributed replica sync cost ($\lambda = 0$ corresponds to pure access latency).
4. **Iterative Knapsack Coordination with Opportunity Regret**:
   - Placement is solved via distributed bidding rounds. In each round, unplaced tasks submit proposals to their best available server.
   - If a server is oversubscribed, it executes **0-1 Knapsack DP** over the bidding tasks, where each task's benefit is its **opportunity regret**:
     $$\Delta J(t_j, s_1) = J(t_j, s_2) - J(t_j, s_1)$$
     (the performance penalty incurred if the task is rejected and forced to its next-best feasible alternative $s_2$).
   - Accepted tasks consume server capacity; rejected tasks re-propose to their next-best options in subsequent rounds until all fit or fleet capacity is exhausted.
5. **Zero-External-Solver Guarantee**:
   - All core graph primitives, min-heaps, Disjoint Set Union (DSU), MST algorithms (Prim, Kruskal), Shortest Paths (Dijkstra, Bellman-Ford, Floyd-Warshall), and Knapsack DP solvers are implemented **strictly from scratch** in pure Python.

---

## 2. Comparison Strategies

To benchmark placement quality rigorously, the suite evaluates five distinct allocation strategies alongside an exact brute-force assignment solver:

1. **Unconstrained Lower Bound**: Places every task on its globally optimal server ignoring server capacities ($\sum d_j > C_v$ allowed). Provides a theoretical lower bound on cost.
2. **Knapsack DP Rounds (Proposed)**: Iterative bidding rounds where each server solves local 0-1 Knapsack DP using regret-to-demand efficiency.
3. **Greedy Rounds**: Identical multi-round bidding process, but servers accept tasks using the greedy efficiency ratio $\frac{\Delta J(t_j, s)}{d_j}$.
4. **Spill-Over Greedy**: High-traffic tasks placed first-fit on their best available server with remaining capacity.
5. **Random Placement**: Uniformly places each task on a random server with sufficient capacity.
6. **Exact Brute-Force Assignment Solver**: Explores all $|V|^n$ candidate allocations on small instances ($\le 7$ tasks, $\le 6$ servers) to compute exact optimality gaps.

---

## 3. Repository Structure

```text
cloud-task-placement/
│
├── README.md                      # Project documentation and setup instructions
├── requirements.txt               # Testing, benchmark, and visualization dependencies
├── generate_datasets.py           # CLI generator for synthetic cloud topologies
├── run_demo.py                    # End-to-end multi-strategy optimizer demo
│
├── src/                           # Pure Python source code (from scratch)
│   ├── __init__.py
│   ├── graph/                     # Graph primitives and topology generation
│   │   ├── __init__.py
│   │   ├── graph.py               # Adjacency-list Graph and Node classes
│   │   ├── generator.py           # Reproducible synthetic topology generator
│   │   ├── min_heap.py            # Binary Min-Heap priority queue with decrease-key
│   │   └── disjoint_set.py        # Disjoint Set Union (DSU) with path compression & union-by-rank
│   ├── mst/                       # Minimum Spanning Tree algorithms
│   │   ├── __init__.py
│   │   ├── kruskal.py             # Kruskal's algorithm (O(E log E))
│   │   └── prim.py                # Prim's algorithm with Min-Heap (O(E log V))
│   ├── shortest_paths/            # Shortest path routing algorithms
│   │   ├── __init__.py
│   │   ├── dijkstra.py            # Dijkstra's SSSP and APSP
│   │   ├── bellman_ford.py        # Bellman-Ford SSSP (O(VE)) with negative cycle check
│   │   └── floyd_warshall.py      # Floyd-Warshall APSP (O(V^3))
│   ├── placement/                 # Resource allocation & knapsack schedulers
│   │   ├── __init__.py
│   │   ├── knapsack_dp.py         # 0-1 Knapsack DP (pseudo-polynomial O(n*W))
│   │   ├── greedy_scheduler.py    # Greedy ratio scheduler & fractional upper bound
│   │   ├── brute_force.py         # Exact brute-force assignment solver
│   │   └── models.py              # Placement dataclasses and solution containers
│   └── optimizer/                 # End-to-end optimizer pipeline
│       ├── __init__.py
│       ├── workload.py            # Task and Workload data classes
│       └── placement_optimizer.py # CloudPlacementOptimizer coordination engine
│
├── data/                          # Benchmark dataset topologies
│   ├── small_topology.json        # 10 servers, 16 links, edge cluster
│   ├── medium_topology.json       # 50 servers, 184 links, regional datacenter network
│   └── large_topology.json        # 200 servers, 995 links, cloud backbone network
│
├── tests/                         # Comprehensive unit test suite (32 tests)
│   ├── __init__.py
│   ├── test_graph.py              # Graph mutations, capacity, latency, JSON I/O
│   ├── test_generator.py          # Seed reproducibility, connectivity, bounds
│   ├── test_mst_networkx.py       # Kruskal & Prim cross-validation with NetworkX
│   ├── test_shortest_paths_networkx.py # SSSP/APSP cross-validation with NetworkX
│   ├── test_placement.py          # 0-1 Knapsack DP vs greedy vs brute force
│   ├── test_placement_model_v2.py # Regret benefit, multi-round invariants, lambda, lower bound
│   └── test_end_to_end_optimizer.py # Full optimizer pipeline integration test
│
├── experiments/                   # Empirical benchmarking suite
│   ├── run_experiments.py         # 10-repeat timing and 10-seed placement experiments
│   └── results/                   # Benchmark CSVs and generated figures
│       ├── mst_runtime_comparison.csv
│       ├── sssp_runtime_comparison.csv
│       ├── apsp_runtime_comparison.csv
│       ├── placement_comparison.csv
│       ├── placement_capacity_sensitivity.csv
│       ├── placement_tasks_sensitivity.csv
│       ├── placement_lambda_sensitivity.csv
│       ├── runtime_vs_size.png
│       ├── latency_vs_capacity.png
│       ├── placement_sensitivity_tasks.png
│       ├── placement_sensitivity_lambda.png
│       └── mst_backbone_topology.png
│
├── notebooks/                     # Interactive visual dashboard
│   └── placement_dashboard.ipynb  # Self-contained Jupyter notebook with saved outputs
│
└── report/                        # Technical report & documentation
    └── TECHNICAL_REPORT.md        # Comprehensive 12-page report with empirical analysis
```

---

## 4. Getting Started & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Virtual environment recommended

### Setup
```bash
# Clone the repository
git clone https://github.com/mohak-07/cloud-task-placement.git
cd cloud-task-placement

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install required testing and visualization packages
pip install -r requirements.txt
```

---

## 5. Running the Tests

Execute the full 32-test suite across unit tests, NetworkX cross-verification, and placement invariants:

```bash
pytest -v tests/
```

All 32 tests pass without warnings:
- Graph operations, JSON persistence, and topology generator bounds.
- Prim and Kruskal correctness vs. NetworkX minimum spanning trees.
- Dijkstra, Bellman-Ford, and Floyd-Warshall routing vs. NetworkX shortest path lengths.
- 0-1 Knapsack DP vs. fractional knapsack upper bound and small brute-force assignment.
- Multi-round placement invariants: capacity limits are never exceeded, every task is placed or recorded as unplaced, brute force optimality gap $\le 5\%$, and unconstrained lower bound is never beaten.

---

## 6. Running Demos & Benchmarks

### End-to-End Placement Optimizer Demo
Run the multi-strategy placement demo on a reproducible 10-node cloud network with 15 client tasks:

```bash
python run_demo.py
```

The script displays:
1. Physical network summary and MST communication backbone.
2. Traffic-weighted median Sync Hub identification.
3. Side-by-side strategy benchmark table (Objective, Latency, Sync Cost, Fleet Capacity Utilization, Placed Tasks).
4. Per-task placement routing breakdown.

### Running Empirical Experiments
To reproduce all runtime scaling and solution quality experiments (10 repeats for runtime, 10 seeds for placement):

```bash
python experiments/run_experiments.py
```

Results and PNG figures are saved automatically in `experiments/results/`.

### Interactive Jupyter Dashboard
Launch the dashboard to interactively inspect topologies, vary $\lambda$, and visualize placements:

```bash
jupyter notebook notebooks/placement_dashboard.ipynb
```

*(Note: The notebook is committed with fully executed outputs and rendered figures for direct rendering on GitHub without running a local kernel).*

---

## 7. Key Experimental Findings

All experiments were executed over **10 random seeds** (placement) and **10 timing repeats** (algorithms):

### Placement Solution Quality (30 Nodes, 35 Tasks)
| Strategy | Latency Gap to Lower Bound ($1.0\times$ Cap) | Latency Gap ($2.0\times$ Cap) | Fleet Capacity Utilization |
| :--- | :---: | :---: | :---: |
| **Unconstrained Lower Bound** | $0.0\%$ (ideal) | $0.0\%$ (ideal) | N/A (unconstrained) |
| **Knapsack DP Rounds** | **$+6.41\% \pm 2.92\%$** | **$+1.74\% \pm 0.99\%$** | $34.4\% \pm 2.4\%$ |
| **Greedy Rounds** | **$+6.37\% \pm 2.95\%$** | **$+1.75\% \pm 1.01\%$** | $34.4\% \pm 2.4\%$ |
| **Spill-Over Greedy** | $+7.18\% \pm 3.12\%$ | $+2.39\% \pm 1.05\%$ | $34.4\% \pm 2.4\%$ |
| **Random Placement** | $+43.08\% \pm 11.27\%$ | $+43.02\% \pm 8.42\%$ | $34.4\% \pm 2.4\%$ |

- **Knapsack DP vs Greedy Rounds**: Produce virtually tied solution quality ($6.41\%$ vs $6.37\%$) because each server receives a modest set of candidate proposals per round (2–5 tasks), where greedy ratio ordering closely matches exact 0-1 knapsack selections.
- **Both Multi-Round Schedulers Beat Spill-Over Greedy**: Coordinated regret-based bidding prevents high-traffic tasks from greedily occupying servers that low-traffic tasks critically require.
- **Random Placement**: Exhibits severe degradation ($\sim 43\%$ gap) and cannot exploit additional capacity.

### MST Backbone & Replication Synchronization ($\lambda$ Trade-Off)
As $\lambda$ increases from $0.0$ to $2.0$:
- **Replication Sync Cost**: Decreases from $111.2$ down to $91.3$ (**$-17.9\%$ reduction**).
- **Client Access Latency**: Increases marginally from $18.23\,\text{ms}$ to $18.25\,\text{ms}$ (**$+0.1\%$ difference**).
- Demonstrates that factoring in the MST sync hub significantly optimizes replica state replication with negligible impact on client access latency.

### Algorithmic Runtime Scaling
- **MST (Kruskal vs. Prim)**: On sparse graphs ($d=0.20$), Kruskal is slightly faster ($2.65\,\text{ms}$ vs $3.01\,\text{ms}$ at $|V|=200$). On dense graphs ($d=0.80$), Prim is **$2.3\times$ faster** ($2.12\,\text{ms}$ vs $4.94\,\text{ms}$ at $|V|=200$) because Prim's heap scales with $|V|$, whereas Kruskal must sort $|E| = 15,920$ edges.
- **SSSP (Dijkstra vs. Bellman-Ford)**: Dijkstra with binary min-heap runs in $0.35\,\text{ms}$ at $|V|=80$, outperforming Bellman-Ford ($5.01\,\text{ms}$) by **$14.3\times$**.
- **APSP (Floyd-Warshall vs. Repeated Dijkstra)**: Repeated Dijkstra runs in $29.58\,\text{ms}$ on sparse graphs ($|V|=80$) compared to $77.85\,\text{ms}$ for Floyd-Warshall (**$2.63\times$ faster**).

---

## 8. Implementation Roadmap

- [x] **Stage 1**: Custom Adjacency List Graph, synthetic cloud topology generator, benchmark datasets, and unit tests.
- [x] **Stage 2**: Disjoint Set Union, Priority Queue Min-Heap, MST (Prim & Kruskal), and Shortest Paths (Dijkstra, Bellman-Ford, Floyd-Warshall).
- [x] **Stage 3**: 0-1 Knapsack Dynamic Programming, greedy ratio schedulers, and fractional upper bound.
- [x] **Stage 4**: Integrated multi-round placement optimizer (`CloudPlacementOptimizer`), regret coordination, routing tables, and demo (`run_demo.py`).
- [x] **Stage 5**: 10-repeat runtime benchmarks, 10-seed placement quality sensitivity experiments, and Matplotlib figure generation.
- [x] **Stage 6**: Interactive Jupyter dashboard (`placement_dashboard.ipynb`) and 12-page Technical Report (`report/TECHNICAL_REPORT.md`).
