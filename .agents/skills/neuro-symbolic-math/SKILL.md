---
name: neuro-symbolic-math
description: Solves open mathematical problems, extremal combinatorics, and discrete optimization problems using a hybrid neuro-symbolic architecture combining LoongFlow Cognitive PES (Plan-Execute-Summarize), compiled bit-parallel Rust verifiers, massive CUDA Swarm simulated annealing (RTX GPU micro-finishing), MAP-Elites quality-diversity archives, SAT/SMT constraint solving, and Lean 4 formal proof certification.
---

# Neuro-Symbolic Mathematical Discovery Skill

A methodology and reusable software template for discovering mathematical counterexamples, establishing new extremal bounds, and automating formal verification across combinatorics, graph theory, and number theory.

---

## 1. The 5-Tier Neuro-Symbolic Stack

When attacking an open mathematical conjecture (e.g. Erdős problems, Ramsey bounds, distinct subset sums, girth/cycle problems), never rely on a single approach. Combine top-down cognitive reasoning with bottom-up GPU brute force:

```
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 1: Cognitive Macro-Architect (LoongFlow PES via agy -p)         │
│  • Formulates algebraic blueprints (Cayley graphs, covers, snarks)     │
│  • Plan -> Execute -> Summarize cognitive rhythm                       │
│  • Distills failure modes into persistent lessons_learned.json         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 2: Quality-Diversity Archive (MAP-Elites)                        │
│  • Multi-dimensional behavioral feature grid (e.g. Girth x Diameter)   │
│  • Prevents premature convergence by preserving structural diversity   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 3: GPU Micro-Finisher (CUDA Swarm on RTX GPUs @ 60-70M moves/s)   │
│  • 10,000+ parallel threads running structure-preserving 2-opt swaps   │
│  • Multi-tier conditional energy: computes deep cycles only when C4=0   │
│  • Finisher Mode: seeds from LoongFlow's near-optimal macro-graph      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 4: Sub-Millisecond Ground Truth Verifier (Compiled Rust)         │
│  • 64-bit integer bitmasks, word-aligned shifts, dynamic popcount      │
│  • Outputs machine-readable diagnostic traces and cycle witnesses      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 5: Formal Proof & Constraint Solving (Lean 4 + Z3 / Kissat)      │
│  • SAT: Exhausts small bounds and infills exact subgraphs              │
│  • Lean 4: Deterministic certificate checking to verify proof theorem  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Standard Problem Scaffolding Runbook

When attacking a new open problem (e.g. `erdos-X/`):

### Step 1: Establish Problem Invariants & Active Frontier
1. Formulate the conjecture mathematically.
2. Determine known computational lower bounds (e.g. Royle's bound: $n > 30$).
3. Identify minimal counterexample structural constraints (e.g. 3-regularity, bipartiteness, symmetry).

### Step 2: High-Performance Rust Verifier (`verifier/`)
1. Implement a bit-parallel 64-bit integer bitmask representation (`[u64; 64]` for graphs $\le 64$ vertices; `Vec<u64>` dynamic wordsets for subset sums).
2. Implement fast $O(1)$ or $O(n^2)$ necessary filters:
   - For graphs: common neighbor popcount `__popcll(adj[u] & adj[w]) >= 2` for $C_4$.
   - For subset sums: pair-difference collisions $a_j - a_i = a_l - a_k$.
3. Implement depth-bounded DFS with visited bitmasks returning an exact **witness path** (e.g. vertices of collision).
4. CLI interface with `--json` output:
   ```json
   {"counterexample": false, "fitness": 850.0, "cycle_witness": [0, 5, 12, 18], "diagnostic_trace": "Collision on C8..."}
   ```
5. Exit code `0` if counterexample, `1` if collision/violation.

### Step 3: Massive CUDA Swarm Searcher (`cuda/swarm.cu`)
1. **Preserve Invariants by Construction**:
   - For cubic graphs: use double-edge swaps (2-opt) that rewire $(u, v)$ and $(x, y)$ to $(u, x)$ and $(v, y)$, preserving degrees identically.
   - Warmup scramble: start from a guaranteed valid structure (e.g. Möbius ladder) and scramble with 100 swaps.
2. **Conditional Multi-Tier Energy**:
   - Evaluate expensive higher-order constraints ($C_{16}, C_{32}$) **only when lower-order violations are zero** ($C_4 = 0 \to C_8 = 0$).
   - This ensures 99.9% of iterations execute in sub-microseconds, maintaining 60M+ moves/second.
3. **Seeded Finisher Mode**:
   - Support `--seed-json '<json>'` to initialize thread 0 with a macro-candidate and perturb other threads by $k = \text{tid} \% 8$ swaps.
   - Track `d_best_adj` globally with `atomicMin(d_best_energy, energy)` and return clean JSON via `--json-only`.

### Step 4: LoongFlow Cognitive PES Engine (`engine/`)
Decompose LLM discovery into three specialized roles rather than blind code mutation:

1. **Planner (`planner.py`)**:
   - Prompts local LLM (`agy -p` with zero external API keys).
   - Injects: (a) parent code, (b) MAP-Elites coverage, (c) recent lessons from `lessons_learned.json`.
   - Produces an explicit **Mathematical Blueprint** specifying algebraic group structures (Cayley graphs, voltage lifts, affine matchings).
2. **Executor (`executor.py`)**:
   - Synthesizes Python generator code conforming strictly to the blueprint.
   - Verifies across target sizes $n$ using `verifier.exe`.
   - **Automated GPU Polish**: If the candidate is valid and promising, pipes it to `cuda/swarm.exe --seed-json` for 5,000 parallel 2-opt iterations in VRAM.
3. **Summarizer (`summarizer.py`)**:
   - Performs **abductive reflection** on the cycle witness trace.
   - Answers: *"Why did this algebraic construction produce a cycle of length L? What general rule prevents this in future blueprints?"*
   - Appends distilled rule to `lessons_learned.json` and inserts into `MapElitesArchive`.

### Step 5: Lean 4 Formal Certificate (`formalization/`)
1. Scaffold a Lake project with `lean-toolchain` and `lakefile.toml`.
2. Define the decidable predicate checking the adjacency matrix or subset sum certificate.
3. Auto-export the winning candidate directly into `Certificate.lean` for kernel verification.

---

## 3. Best Practices & Critical Rules

### Avoiding KaTeX Errors in Markdown Artifacts
- Never write `#C_k` in math mode. The `#` character is TeX's macro parameter token and triggers `You can't use 'macro parameter character #' in math mode`.
- Always use standard set-cardinality notation:
  $$E(G) = 1000 \cdot |C_4| + 200 \cdot |C_8| + 50 \cdot |C_{16}| + 10 \cdot |C_{32}|$$

### Preserving Windows Console Encoding
Windows default `cp1252` encoding crashes on emojis and unicode math symbols. Always initialize Python CLI scripts with:
```python
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
```

### Zero External API Keys Requirement
- Always invoke the local authenticated Antigravity CLI session via:
  ```python
  import subprocess
  res = subprocess.run(["agy", "-p", prompt], capture_output=True, text=True, check=True)
  output = res.stdout.strip()
  ```
- This ensures completely autonomous operation without third-party API quotas or keys.

### CUDA Compilation on Windows
When `cl.exe` is not in the global PATH, compile CUDA kernels by activating Visual Studio Developer environment in subshell:
```bash
cmd /c 'call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && nvcc -O3 -std=c++17 -arch=sm_89 cuda/kernel.cu -o cuda/kernel.exe'
```

---

## 4. Reusable Reference Directory Layout

```
problem-name/
├── Makefile                      # Targets: build-verifier, build-cuda, test, search-gpu, search-pes, report
├── campaign_solver.py            # Multi-order autonomous campaign orchestrator
├── lessons_learned.json          # Persistent knowledge base
├── results.db                    # SQLite run & evaluation log
├── verifier/                     # Rust 64-bit bitmask verifier
│   ├── Cargo.toml
│   └── src/{lib.rs, main.rs}
├── cuda/                         # RTX GPU Swarm Searcher
│   ├── swarm.cu                  # CUDA kernel with ILS, spectral tempering, and finisher mode
│   └── swarm.exe
├── sat/                          # SMT / SAT pipeline (Z3 / Kissat)
│   └── run_sat.py
├── engine/                       # LoongFlow PES Loop
│   ├── loongflow_main.py         # Orchestrator
│   ├── planner.py                # Hypothesis blueprinting
│   ├── executor.py               # Code synthesis + GPU Swarm polish
│   ├── summarizer.py             # Abductive reflection
│   ├── pes_memory.py             # MAP-Elites + Lessons
│   ├── map_elites.py             # Quality-Diversity archive
│   └── evaluator.py              # Sandbox & verifier bridge
└── formalization/                # Lean 4 proof verification
    ├── lakefile.toml
    └── Problem/Certificate.lean
```

---

## 5. Advanced Swarm Search Patterns

### I. Iterated Local Search (ILS) & Reheating Pulses
Pure simulated annealing freezes at $T \to 0$ into greedy hill climbing, trapping the swarm in local basins.
- Track `local_best_energy` and `local_best_adj` in each GPU thread.
- If a thread fails to improve for $K$ steps (e.g. 2,000 steps), revert to `local_best_adj` and apply a thermal reheat pulse ($T \leftarrow T_{\text{initial}} \times 0.7$).
- This implements **Basin Hopping** directly in GPU registers.

### II. Spectral Temperature Diversity
Never use uniform temperature across GPU threads. Distribute initial temperatures geometrically or linearly across threads:
```cpp
float temp_mult = 0.05f + 2.5f * ((float)(tid % 128) / 127.0f);
float thread_initial_temp = initial_temp * temp_mult;
```
This enables simultaneous greedy micro-polishing ($T = 0.4$) and wide basin jumping ($T = 20.0$) in a single kernel call.

### III. Overcoming Topological Energy Canyons
When local search (e.g. 2-opt) consistently eliminates lower-order penalties ($C_4 = 0, C_8 = 0$) but stalls at a higher-order cycle ($C_{16} = 1$), 2-edge swaps cannot cross the energy barrier without violating lower penalties.
1. **Targeted Witness $k$-Opt**: Extract the exact vertex collision path from the Rust verifier and execute coordinated $k$-edge swaps exclusively on those witness edges.
2. **Algebraic Lift Constraints**: Pass the collision witness back into the LoongFlow Planner to synthesize non-abelian voltage assignments (e.g. over $A_5$ or Frobenius groups) whose element orders forbid cycle formation algebraically.

