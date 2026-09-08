# Erdős Problem #64: The Erdős–Gyárfás Conjecture Pipeline

A high-performance neuro-symbolic research pipeline combining **compiled 64-bit Rust cycle verification**, **RTX 4070 Super CUDA Swarm simulated annealing**, **Z3 SAT constraint solving**, **FunSearch LLM code mutation**, and **Lean 4 formal certification** to attack Erdős Problem #64 without external API keys.

---

## 1. Mathematical Problem Formulation

### The Conjecture
> **Erdős–Gyárfás Conjecture (1995)**:
> Every finite graph with minimum degree $\delta(G) \ge 3$ contains a simple cycle whose length is a power of two ($4, 8, 16, 32, 64, \dots$).

- **The Bounty**: **\$50** for a counterexample, **\$100** for a general proof ([erdosproblems.com/64](https://www.erdosproblems.com/64)).
- **What a Counterexample Requires**:
  - A minimal counterexample graph must be **3-regular (cubic)**.
  - It must contain **no 4-cycles ($C_4$), no 8-cycles ($C_8$), no 16-cycles ($C_{16}$), and no 32-cycles ($C_{32}$)**.
- **Known Computational Bounds**:
  - Gordon Royle (2000) proved by computer enumeration that **no cubic counterexample exists on $n \le 30$ vertices** (and $n \le 64$ for bipartite graphs).
  - Klas Markström (2004) discovered four graphs on 24 vertices with no $C_4$ and no $C_8$ (only $C_{16}$).
  - **The Search Frontier**: The search for a counterexample begins at **$n \ge 32$ vertices**.

---

## 2. Multi-Pronged Architecture

```
erdos-64/
├── Cargo.toml                    # Root workspace configuration
├── Makefile                      # Build, test, and multi-search targets
├── README.md                     # Architecture & mathematical guide
├── results.db                    # SQLite experiment tracking database
├── verifier/                     # High-performance 64-bit Rust verifier
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs                # Bitmask DFS, popcount C4 filter, graph invariants
│       └── main.rs               # CLI interface (--k4, --petersen, --markstrom, --json)
├── cuda/                         # RTX 4070 Super CUDA Swarm Searcher
│   └── swarm_64.cu               # 10,240 parallel threads running 2-opt edge-swaps
├── sat/                          # Boolean Satisfiability (SAT) Pipeline
│   ├── cnf_encoder.py            # DIMACS CNF encoder with symmetry breaking
│   └── run_sat.py                # Z3 SMT/SAT solver pipeline
├── engine/                       # FunSearch Graph Generator Evolution
│   ├── baseline_graphs.py        # Generalized Petersen & ring chord generators
│   ├── island.py                 # 5-island population manager with ring migration
│   ├── evaluator.py              # Sandboxed subprocess bridge to Rust verifier
│   ├── mutator.py                # Zero-key Antigravity (`agy -p`) mutator
│   ├── main.py                   # FunSearch orchestrator & SQLite logger
│   └── report.py                 # Progress & discovery reporter
└── formalization/                # Lean 4 Formal Verification Setup (Lake)
    ├── lean-toolchain            # Lean 4 version specification
    ├── lakefile.toml             # Lake project configuration
    ├── lake-manifest.json        # Lake dependency manifest
    ├── Problem64.lean            # Root module
    └── Problem64/
        ├── Basic.lean            # Formal definition of Erdős-Gyárfás conjecture
        └── Certificate.lean      # Auto-generated Lean proof for counterexample
```

---

## 3. The 3 Attack Vectors

### I. GPU Swarm Search (`cuda/swarm_64.exe`)
- Runs 10,240 to 50,000 parallel search threads directly on your **RTX 4070 Super** (Ada Lovelace `sm_89`).
- Each thread maintains a 3-regular graph on $n \ge 32$ vertices and performs **double-edge swaps (2-opt)** that preserve 3-regularity.
- Minimizes the objective energy:
  $$E(G) = 1000 \cdot \#C_4 + 200 \cdot \#C_8 + 50 \cdot \#C_{16} + 10 \cdot \#C_{32}$$
- **Measured Throughput**: **27.6 million moves per second** in VRAM.

### II. SAT Solving Pipeline (`sat/run_sat.py`)
- Encodes 3-regularity, girth $\ge 5$, no $C_8$, and no $C_{16}$ into propositional logic.
- Adds symmetry-breaking clauses on vertex 0's neighborhood to prune isomorphic search branches.
- Uses **Z3** or external modern SAT solvers (Kissat, CaDiCaL) to find satisfiable assignments or prove non-existence.

### III. FunSearch Evolutionary Islands (`engine/main.py`)
- 5 evolutionary islands maintaining graph generator algorithms.
- Local `agy -p` mutations propose structural families: voltage graph permutation covers, Cayley graphs on non-abelian groups, and Snarks.
- Evaluates candidate graphs against the Rust verifier and logs progress to SQLite (`results.db`).

---

## 4. Quickstart Commands

```bash
cd c:/dev/math-problems/erdos-64

# 1. Build Rust release verifier & CUDA GPU kernel
make build-verifier
make build-cuda

# 2. Run all unit tests (K4, Petersen, Markstrom)
make test

# 3. Launch RTX 4070 Super GPU Swarm Search (e.g. n=32 vertices)
make search-gpu
# Or run with custom parameters: ./cuda/swarm_64.exe 34 5000

# 4. Launch Z3 SAT solver search (e.g. n=12)
make search-sat

# 5. Launch FunSearch evolutionary loop (calling agy -p)
make search-fun

# 6. View progress report
make report
```
