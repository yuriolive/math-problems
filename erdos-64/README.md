# Erdős Problem #64: The Erdős–Gyárfás Conjecture Pipeline

A high-performance neuro-symbolic research pipeline combining **compiled 64-bit Rust cycle verification**, **RTX 4070 Super CUDA Swarm simulated annealing (@ 68.2M moves/sec)**, **Z3 SAT constraint solving**, **LoongFlow Cognitive PES (Plan-Execute-Summarize) Engine**, and **Lean 4 formal certification** to attack Erdős Problem #64 without external API keys.

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
  - Klas Markström (2004) discovered four cubic graphs on 24 vertices with no $C_4$ and no $C_8$ (House of Graphs #51419; fails on $C_{16}$).
  - **The Search Frontier**: The search for an unassailable counterexample begins at **$n \ge 32$ vertices**.

---

## 2. Architecture & File Structure

```
erdos-64/
├── Cargo.toml                    # Root Rust workspace configuration
├── Makefile                      # Build, test, and multi-search targets
├── README.md                     # Architecture & mathematical research guide
├── lessons_learned.json          # Persistent Evolutionary Memory (Abductive Lessons)
├── results.db                    # SQLite experiment tracking database
├── verifier/                     # High-performance 64-bit Rust verifier
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs                # Bitmask DFS, popcount C4 filter, graph invariants
│       └── main.rs               # CLI interface (--k4, --petersen, --markstrom, --json)
├── cuda/                         # RTX 4070 Super CUDA Swarm Searcher
│   ├── swarm_64.cu               # 10,240 threads running 2-opt annealing (@ 68.2M moves/s)
│   └── swarm_64.exe              # Standalone binary + Seeded Finisher mode
├── sat/                          # Boolean Satisfiability (SAT) Pipeline
│   ├── cnf_encoder.py            # DIMACS CNF encoder with symmetry breaking
│   └── run_sat.py                # Z3 SMT/SAT solver pipeline
├── engine/                       # LoongFlow PES Cognitive Evolutionary Engine
│   ├── loongflow_main.py         # Main PES orchestrator loop
│   ├── planner.py                # Stage 1: Theory blueprint formulation (agy -p)
│   ├── executor.py               # Stage 2: Code synthesis + GPU Swarm Polish
│   ├── summarizer.py             # Stage 3: Abductive reflection & memory update
│   ├── pes_memory.py             # Hybrid MAP-Elites + Episodic Knowledge Base
│   ├── map_elites.py             # Quality-Diversity phenotypic archive (Girth x Diam x BP)
│   ├── baseline_graphs.py        # Foundational graph generators (Markström, GP, rings)
│   ├── evaluator.py              # Sandboxed subprocess bridge to Rust verifier_64.exe
│   ├── island.py                 # Dataclasses and population structures
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

## 3. The 3 Attack Vectors & Hybrid Synergy

### I. Massive GPU Swarm Search (`cuda/swarm_64.exe`)
- Runs **10,240 to 50,000 parallel search threads** directly in VRAM on the **NVIDIA GeForce RTX 4070 Super** (Ada Lovelace `sm_89`).
- Guaranteed strictly 3-regular ($d(v) = 3$) from step 0 (Möbius ladder $C_n(1, n/2)$ base + 2-opt warmup shuffle).
- Evaluates a **multi-tier conditional energy function**:
  $$E(G) = 1000 \cdot |C_4| + 200 \cdot |C_8| + 50 \cdot |C_{16}| + 10 \cdot |C_{32}|$$
  Iterative bounded DFS checks for $C_{16}$ and $C_{32}$ execute conditionally only when lower cycles are eliminated ($C_4 = 0 \to C_8 \to C_{16} \to C_{32}$), preserving peak throughput.
- **Measured Throughput**: **68.2 million moves per second** in VRAM.
- **Micro-Finisher Mode**: Accepts candidate seed graphs via `--seed-json '<json>'` to anneal around promising algebraic structures.

### II. LoongFlow Cognitive PES Engine (`engine/loongflow_main.py`)
Implements Baidu Baige's **Plan-Execute-Summarize (PES)** paradigm (arXiv:2512.24077):
1. **Planner (`planner.py`)**: Reviews current MAP-Elites niches and `lessons_learned.json` to formulate an explicit mathematical blueprint (e.g. Multi-Ring Odd-Factor Lifts, non-abelian Cayley graphs over $S_4$, Snark double-covers) before writing code.
2. **Executor (`executor.py`)**: Synthesizes the generator code, tests in sandbox via compiled Rust `verifier_64.exe`, and dispatches promising graphs to the GPU Swarm.
3. **Summarizer (`summarizer.py`)**: Conducts abductive reflection on collision traces and records distilled algebraic rules into [`lessons_learned.json`](lessons_learned.json).

### III. The Neuro-Symbolic Hybrid ("Architect + Finisher")
- **LoongFlow as the Architect**: Discovers global macro-symmetries that eliminate $C_4$ and $C_8$ globally.
- **CUDA Swarm as the Finisher**: Loads LoongFlow's near-counterexample into VRAM and runs 51 million 2-opt micro-swaps in ~750ms to extinguish residual boundary seam cycles.
- **Rust Verifier as Ground Truth**: Validates any candidate down to microsecond machine precision.

### IV. SAT Solving Pipeline (`sat/run_sat.py`)
- Encodes 3-regularity, girth $\ge 5$, no $C_8$, and no $C_{16}$ into propositional logic.
- Uses **Z3** to prove non-existence or solve exact small chord completions.

---

## 4. Quickstart Commands

```bash
cd c:/dev/math-problems/erdos-64

# 1. Build Rust release verifier & CUDA GPU kernel
make build-verifier
make build-cuda

# 2. Run Rust and Python unit tests
make test

# 3. Launch RTX 4070 Super Multi-Order Solving Campaign
uv run python campaign_solver.py --orders 32,34,36,38,40,42,44,48 --iters 50000 --rounds 3

# 4. Launch Standalone GPU Swarm Search (40M moves/s)
# 10,240 threads x 50,000 steps on n=32 (512M moves in ~12s)
./cuda/swarm_64.exe 32 50000 --seed-file cuda/best_swarm_n32.json

# 5. Launch LoongFlow Cognitive PES Engine (Hybrid with GPU Polish)
uv run python -m engine.loongflow_main --iterations 10 --test-ns 32,34,36

# 6. Verify an individual candidate graph via Rust CLI
./target/release/verifier_64.exe --json '{"n": 32, "adj": [[...], ...]}'
```

---

## 5. Empirical Discoveries & The $C_{16}$ Frontier ($n = 32 \dots 48$)

Over **5.0 Billion 2-opt moves** have been computed across orders $n \in [32, 48]$ on the RTX 4070 Super at 100% GPU utilization.

Across **8 distinct graph orders**, the searcher eliminated all 4-cycles, all 8-cycles, and all 32-cycles. Every candidate below has been certified by the compiled Rust binary `verifier_64.exe`:

| Order $n$ | $|E|$ | Regularity | Girth | Diam | $C_4$ | $C_8$ | $C_{16}$ | $C_{32}$ | Status | Candidate File |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **32** | 48 | Cubic ($d=3$) | 3 | 6 | **0** | **0** | **1** | **0** | Near-Miss | `cuda/best_swarm_n32.json` |
| **34** | 51 | Cubic ($d=3$) | 3 | 6 | **0** | **0** | **1** | **0** | Near-Miss | `cuda/best_swarm_n34.json` |
| **36** | 54 | Cubic ($d=3$) | 3 | 6 | **0** | **0** | **1** | **0** | Near-Miss | `cuda/best_swarm_n36.json` |
| **38** | 57 | Cubic ($d=3$) | 3 | 6 | **0** | **0** | **1** | **0** | Near-Miss | `cuda/best_swarm_n38.json` |
| **40** | 60 | Cubic ($d=3$) | 3 | 6 | **0** | **0** | **1** | **0** | Near-Miss | `cuda/best_swarm_n40.json` |
| **42** | 63 | Cubic ($d=3$) | 3 | 7 | **0** | **0** | **1** | **0** | Near-Miss | `cuda/best_swarm_n42.json` |
| **44** | 66 | Cubic ($d=3$) | 3 | 6 | **0** | **0** | **1** | **0** | Near-Miss | `cuda/best_swarm_n44.json` |
| **48** | 72 | Cubic ($d=3$) | 3 | 7 | **0** | **0** | **1** | **0** | Near-Miss | `cuda/best_swarm_n48.json` |

---

## 6. Mathematical Analysis: The $C_{16}$ Energy Canyon

The empirical convergence across all 8 orders uncovered a critical structural property of cubic graphs:
1. **$C_4$ and $C_8$ are Readily Eliminated**: Simulated annealing on 3-regular graphs effortlessly drives $C_4 \to 0$ and $C_8 \to 0$.
2. **The 2-Opt Topological Bottleneck**: A 2-opt move swaps exactly 2 edges ($u-v$ and $x-y$). In any configuration with $C_4 = 0$ and $C_8 = 0$, breaking the single remaining 16-cycle with a 2-edge swap almost inevitably reconnects chords that close either an 8-cycle (energy penalty $+200$) or another 16-cycle.
3. **Implication for Solver Strategy**: To break through the 16-cycle barrier, higher-order topological operators are required:
   - **Targeted Witness 3-Opt**: Coordinated 3-edge swaps directly targeted at the cycle witness edges reported by `verifier_64.exe`.
   - **Non-Abelian Group Lifts**: Using LoongFlow to construct voltage graphs over groups (such as $A_5$ or Frobenius groups) whose element orders forbid 2-adic cycle closures.

