# Math Problems: Neuro-Symbolic Discovery Pipelines

A collection of high-performance neuro-symbolic research pipelines attacking open mathematical conjectures and Erdős problems using **compiled Rust verifiers**, **NVIDIA CUDA GPU acceleration (RTX 4070 Super)**, **Evolutionary LLM code mutation (FunSearch / AlphaEvolve via Antigravity CLI)**, **SAT/SMT constraint solving (Z3)**, and **Lean 4 formal certification**.

---

## Projects

### 1. [`erdos-search/`](./erdos-search/) — Erdős Problem #1 (Distinct Subset Sums & Bohman's Bound)
* **Mathematical Goal**: Find $n$-element sets of positive integers with distinct subset sums minimizing the ratio $R = \frac{\max(A)}{2^n}$.
* **Benchmark to Beat**: Tom Bohman's 1998 bound ($R < 0.22002$).
* **Pipeline**:
  * Ultra-fast bit-parallel dynamic shift verifier in Rust ($n \le 24$).
  * CUDA GPU verifier on RTX 4070 Super processing 268M subset sums in 214 ms ($n \ge 25$).
  * 5-island evolutionary model with ring migration and zero-key `agy -p` mutations.
  * Lean 4 Lake formalization ready for certificate generation.

### 2. [`erdos-64/`](./erdos-64/) — Erdős Problem #64 (The Erdős–Gyárfás Conjecture)
* **Mathematical Goal**: Find a counterexample (a 3-regular graph with no cycles of length $2^k$: no $C_4, C_8, C_{16}, C_{32}$).
* **Active Frontier**: Cubic graphs on $n \ge 32$ vertices (Gordon Royle proved $n \le 30$ has no counterexamples).
* **Pipeline**:
  * 64-bit integer bitmask Rust cycle checker (verified against $K_4$, Petersen, and Markström 24-vertex graph).
  * CUDA Swarm Searcher running 10,240 parallel threads on RTX 4070 Super performing 27 million 2-opt edge-swaps per second.
  * Z3 SAT constraint pipeline with symmetry-breaking clauses.
  * FunSearch evolutionary island engine and Lean 4 certificate module.

---

## Technology Stack

* **Verification**: Rust 2021 (AVX2 / 64-bit bitmasks), Lean 4 (`v4.16.0`).
* **GPU Acceleration**: NVIDIA CUDA 13.0, Ada Lovelace `sm_89` (RTX 4070 Super), Thrust.
* **Evolution & Synthesis**: Python 3.13, Google DeepMind FunSearch / AlphaEvolve island models, Antigravity CLI (`agy -p`).
* **Constraint Solving**: Z3 SMT/SAT Solver 5.1.
