# Erdős Problem #1: Neuro-Symbolic Search Pipeline
### Bohman's Bound on Sets with Distinct Subset Sums

A high-performance neuro-symbolic search pipeline combining **compiled Rust verification**, **FunSearch island evolution**, **local Antigravity LLM code mutation**, and **Lean 4 formal certification** to tackle Erdős Problem #1 without external API keys.

---

## 1. Mathematical Problem Formulation

### Erdős Problem #1
Find an $n$-element set of positive integers:
$$A = \{a_1 < a_2 < \dots < a_n\}$$
such that all $2^n$ subset sums:
$$\sum_{x \in X} x \quad (X \subseteq A)$$
are strictly distinct, while minimizing the ratio:
$$R = \frac{\max(A)}{2^n}$$

### Human Benchmark: Bohman's Bound
- **Trivial Bound (Powers of 2)**: $A = \{1, 2, 4, \dots, 2^{n-1}\} \implies \max(A) = 2^{n-1} \implies R = 0.5$.
- **Conway-Guy Sequence (1968)**: Improved the upper bound using the recurrence $u_{k+1} = 2u_k - u_{k - \lfloor\sqrt{2k} + 0.5\rfloor}$, yielding $R \approx 0.23 \sim 0.25$.
- **Tom Bohman (1998)**: Established the current world-record human construction with:
  $$R < 0.22002 \quad \text{for sufficiently large } n$$
- **The Challenge**: Discover algorithmic constructions that produce strictly distinct subset sums with $R < 0.22002$.

---

## 2. Project Architecture

```
erdos-search/
├── Cargo.toml                    # Root workspace configuration
├── Makefile                      # Orchestrates build, test, search, and report
├── README.md                     # Comprehensive system documentation
├── results.db                    # SQLite persistent experiment database
├── verifier/                     # High-performance Rust verifier
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs                # Bit-parallel shift verifier & meet-in-the-middle
│       └── main.rs               # CLI interface (--set, stdin JSON, exit codes)
├── engine/                       # FunSearch Evolutionary Island Engine
│   ├── __init__.py
│   ├── baseline.py               # Conway-Guy & Bohman randomized seeds
│   ├── island.py                 # 5-island population manager with ring migration
│   ├── evaluator.py              # Subprocess sandbox + Rust verifier bridge
│   ├── mutator.py                # Zero-key Antigravity CLI (`agy -p`) mutator
│   └── main.py                   # Orchestrator & SQLite experiment logger
└── formalization/                # Lean 4 Formal Verification Setup (Lake)
    ├── lean-toolchain            # Lean 4 version specification
    ├── lakefile.toml             # Lake project configuration
    ├── lake-manifest.json        # Lake dependency manifest
    ├── Problem1.lean             # Main library entry point
    └── Problem1/
        ├── Basic.lean            # Formal definition of Distinct Subset Sums
        ├── Verification.lean     # Decidable checker & soundness theorem
        └── Certificate.lean      # Auto-generated Lean proofs for winning sets
```

---

## 3. Core Subsystems

### I. High-Throughput Rust Verifier (`verifier/`)
- **Bit-Parallel Dynamic Shifts ($n \le 24$)**:
  - Dynamically sized `Vec<u64>` bitset. Sum 0 starts at bit 0.
  - For each element $x \in A$, tests overlap `bitset & (bitset << x)` in $O(\text{sum}(A) / 64)$ time with AVX2 vectorization.
  - Immediately halts and reports the exact colliding subset masks on the first collision.
- **Pair-Difference Filter & Meet-in-the-Middle ($n > 24$)**:
  - $O(n^2)$ necessary check on pair differences $a_j - a_i$. Any duplicate difference with disjoint indices yields an immediate 2-element collision ($a_j + a_k = a_l + a_i$).
  - Meet-in-the-middle splits $A$ into halves of size $\lfloor n/2 \rfloor$ and $\lceil n/2 \rceil$.
- **Strict JSON I/O**:
  - `{"valid": bool, "n": int, "max_val": int, "ratio": float, "beats_bohman": bool, "collision": [int, int] | null}`
  - Exit code `0` on success, `1` on collision.

### II. FunSearch Island Evolutionary Engine (`engine/`)
- **Baseline Seeds (`baseline.py`)**:
  - `conway_guy_sequence(n)`: Conway-Guy recurrence (OEIS A005318).
  - `bohman_randomized(n, seed)`: Stochastic Bohman offset exploration.
- **5-Island Model (`island.py`)**:
  - 5 isolated populations ranked by best ratio $R$ and fitness.
  - Ring migration: top programs migrate between adjacent islands every $M$ generations to avoid local minima.
- **Sandboxed Subprocess Evaluator (`evaluator.py`)**:
  - 5-second timeout execution in isolated subprocess.
  - Evaluates candidates across benchmark dimensions $n \in [15, 20, 22, 24]$.
  - Pipes candidate sets into the compiled Rust binary.
- **Zero-API-Key Antigravity Mutator (`mutator.py`)**:
  - Executes `agy -p "<prompt>"` using the local authenticated Antigravity CLI session.
  - Zero third-party API dependencies or keys.
  - Robust regex extraction of mutated Python generator functions.

---

## 4. Progress Tracking & Database (`results.db`)

All experiments, candidate programs, evaluations, and elite discoveries are persistently stored in SQLite (`results.db`):

- **`runs`**: Execution sessions, test dimensions, island count, timestamps.
- **`programs`**: Candidate generator code, lineage (parent ID), fitness, best ratio $R$, Bohman status.
- **`evaluations`**: Per-dimension ($n$) test results, max element, ratio, collision pairs, errors.
- **`discoveries`**: Milestones that achieve new global best ratios or beat Bohman's constant.

### Querying Progress
```bash
make report
```
Or with SQLite directly:
```sql
SELECT id, generation, island_id, best_ratio, beats_bohman, created_at
FROM programs
WHERE all_valid = 1
ORDER BY best_ratio ASC
LIMIT 10;
```

---

## 5. Quickstart & Commands

### Build the Verifier
```bash
make build-verifier
```

### Run Tests
```bash
make test
```

### Launch the Search Pipeline
```bash
make run
```
Or customize parameters:
```bash
python engine/main.py --n-eval 20 --islands 5 --iterations 20 --migrate-interval 5
```

### Inspect Results
```bash
make report
```

---

## 6. Lean 4 Formal Verification Workflow

When a candidate program discovers an integer set beating Bohman's bound ($R < 0.22002$):
1. `engine/main.py` automatically writes `formalization/Problem1/Certificate.lean`.
2. Run Lake inside `formalization/`:
   ```bash
   cd formalization
   lake build
   ```
3. The certificate evaluates inside Lean's kernel, providing a machine-checked mathematical proof of the construction.
