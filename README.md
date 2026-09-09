# Math Problems: Neuro-Symbolic Discovery Pipelines

Two search pipelines aimed at open Erdős problems, built from compiled Rust verifiers, NVIDIA
CUDA kernels (RTX 4070 Super), LLM-driven code mutation through the local `agy` CLI, Z3
SAT/SMT solving, and Lean 4 formalizations.

Both problems are open. Neither pipeline has produced a counterexample or a new bound, and
neither Lean project proves the target theorem.

---

## Projects

### 1. [`erdos-search/`](./erdos-search/) — Erdős Problem #1 (Distinct Subset Sums)
* **Goal**: find $n$-element sets of positive integers with distinct subset sums that minimize
  the ratio $R = \max(A) / 2^n$.
* **Benchmark**: Bohman's bound, $R < 0.22002$ (hard-coded as `BOHMAN_CONSTANT` in
  `engine/evaluator.py`).
* **What is actually wired up**:
  * A bit-parallel Rust verifier over dynamic `u64` word sets, driven from Python through
    `engine/evaluator.py`.
  * A 5-island evolutionary loop (`engine/main.py`) with ring migration, seeded from
    Conway–Guy and Bohman baselines, mutating candidates via `agy -p` with no external API
    keys. Runs are logged to SQLite.
  * `cuda/verifier_cuda.cu` is a standalone CUDA source file. It is compiled only by the
    `build-cuda` Makefile target and is **not called by the Python pipeline** — nothing in
    `engine/` references it.
  * `formalization/` is a Lean 4 Lake scaffold. `Problem1/Verification.lean` still ends in a
    `sorry`, so it certifies nothing yet.
* See [`erdos-search/README.md`](./erdos-search/README.md) for details.

### 2. [`erdos-64/`](./erdos-64/) — Erdős Problem #64 (Erdős–Gyárfás Conjecture)
* **Goal**: search for a counterexample — a graph with minimum degree $\ge 3$ containing no
  cycle whose length is a power of two. Bounty: **\$1000**
  ([erdosproblems.com/64](https://www.erdosproblems.com/64)).
* **Context that shapes the search**: Liu and Montgomery proved the conjecture true once the
  minimum degree exceeds an absolute constant, so only very small minimum degree can host a
  counterexample. Markström showed a cubic counterexample needs at least 30 vertices, and an
  exhaustive search reported on the problem forum settles general cubic graphs up to
  $n \le 34$ — so the open corridor starts at $n = 36$.
* **Pipeline**:
  * Rust cycle verifier over 64-bit adjacency bitmasks. It tests every power-of-two length
    $\le n$ unconditionally and, with `--full --cap N`, reports exact per-length counts.
    Validated against $K_4$, the Petersen graph, and Markström's 24-vertex graph.
  * CUDA swarm annealer, 10,240 threads by default, using a lexicographic tier energy and
    degree-preserving 2-opt/3-opt swaps. Measured at about **8.2 million evaluated
    moves/sec** on an RTX 4070 Super — counting only moves whose energy was actually
    computed.
  * Z3 SAT/SMT encoding with symmetry-breaking clauses.
  * A Plan-Execute-Summary LLM loop plus an island-model evolutionary engine.
  * A Lean 4 project that builds with no `sorry`, checking well-formedness, 3-regularity and
    short cycle lengths; the long cycle lengths are checked by the Rust verifier, which is a
    trusted rather than a verified component.
* See [`erdos-64/README.md`](./erdos-64/README.md) for the measured candidate table.

---

## Technology Stack

* **Verification**: Rust 2021 (64-bit bitmasks), Lean 4 with Lake.
* **GPU**: NVIDIA CUDA, Ada Lovelace `sm_89` (RTX 4070 Super) by default.
* **Search and synthesis**: Python 3.12+, island-model evolution, Antigravity CLI (`agy -p`),
  no external API keys.
* **Constraint solving**: Z3 (`z3-solver`), the only third-party Python dependency.
