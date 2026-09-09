# Erdős Problem #64: The Erdős–Gyárfás Conjecture Pipeline

A search pipeline for Erdős Problem #64, combining a compiled 64-bit Rust cycle verifier, a
CUDA swarm annealer (RTX 4070 Super), a Z3 SAT/SMT encoding, an LLM Plan-Execute-Summary loop
driven by the local `agy` CLI, and a Lean 4 formalization. No external API keys are required.

The conjecture is **open**. Nothing in this repository is a counterexample, and no part of it
constitutes a proof.

---

## 1. Mathematical Problem Formulation

### The Conjecture
> **Erdős–Gyárfás Conjecture**:
> Every finite graph with minimum degree $\delta(G) \ge 3$ contains a simple cycle whose
> length is a power of two ($4, 8, 16, 32, 64, \dots$).

- **The Bounty**: **\$1000** ([erdosproblems.com/64](https://www.erdosproblems.com/64)).
- **The single most important known result** — Liu and Montgomery [LiMo20] proved the
  conjecture **true whenever the minimum degree exceeds an absolute constant**. The same work
  disproved the stronger conjecture of Erdős and Gyárfás. This is the reason a search
  restricts itself to graphs of very small minimum degree: only there can a counterexample
  still live.
- **Known computational bounds**:
  - Markström [Ma04] showed that a **cubic counterexample must have at least 30 vertices**.
    (This is not a Royle result; earlier versions of this file misattributed it and also
    misstated it as "no cubic counterexample exists on $n \le 30$".)
  - Nowbandegani and Esfandiari [NoEs11] showed that a **bipartite counterexample must have at
    least 32 vertices**.
  - Forum user `sallerk` (31 Aug 2026) reports an exhaustive search over **cubic bipartite**
    graphs for every even $n$ from 4 to 62 with no survivor — in that whole range no graph
    even avoided $C_4$, $C_8$ and $C_{16}$ simultaneously, so the $C_{32}$ test was never
    reached. The same author reports that their general (non-bipartite) cubic search reached
    only $n \le 34$. Code: <https://github.com/sallerk/erdos-notes/tree/main/p64>
  - **Therefore the open corridor for general cubic graphs starts at $n = 36$.** The default
    orders of `campaign_solver.py` and `engine/loongflow_main.py` begin there, and both warn
    when asked for $n \le 34$.
- **Families where the conjecture is confirmed** (so no construction inside them can work):
  3-connected cubic planar graphs (Heckman–Krakovski), graphs of diameter 2 (Carr), $P_8$-free
  graphs (Gao–Shan), $P_{10}$-free graphs (Hu–Shen), claw-free cubic graphs below 114
  vertices, and several Cayley families.

### Why cubic, and the limits of that choice
Restricting the search to cubic graphs is a **heuristic**, not a theorem. Andrew Bisch's Lean 4
formalization (sound and `sorry`-free) establishes structural facts about a *minimal*
counterexample: the vertices of degree $\ge 4$ form an independent set, every vertex has a
cubic neighbour, and at least $2/3$ of the vertices are cubic. That does **not** prove a
minimal counterexample is cubic, so it does not license the restriction — it only makes it
plausible.

A second forum claim, Guillem Duran-Ballester's 250-page argument, is incomplete: a reviewer
produced an arithmetic counterexample to its Lemma 7.37(a), the author conceded, and the
author's own status log (`EG_LEAN_COMPLIANCE_REMAINING.md`, 2026-08-30) states that the
selected root is not a proof of the target theorem.

---

## 2. Architecture & File Structure

```
erdos-64/
├── Cargo.toml                    # Rust workspace configuration
├── Makefile                      # build-verifier, build-cuda, test, search-*, report
├── README.md                     # This file
├── campaign_solver.py            # Multi-order search campaign orchestrator
├── candidates_report.json        # Written by tools/recount_candidates.py
├── lessons_learned.json          # Persistent notes fed back into the LLM planner
├── results.db                    # SQLite run log (created on first run; not in git)
├── verifier/                     # Rust cycle verifier (ground truth)
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs                # Bitmask DFS, C4 popcount filter, graph invariants
│       └── main.rs               # CLI (stdin or --json, --full, --cap, --k4,
│                                 #      --petersen, --markstrom)
├── cuda/                         # CUDA swarm annealer
│   ├── swarm_64.cu               # Lexicographic-energy 2-opt/3-opt annealing kernel
│   ├── swarm_64.exe              # Built binary
│   ├── build.bat                 # Locates MSVC, then runs nvcc (override CUDA_ARCH)
│   └── best_swarm_n*.json        # Best graph per order, each with a `verified` block
├── tools/
│   ├── recount_candidates.py     # Regenerates section 5's table from the verifier
│   └── verify_graph.py           # Verifies a single graph file
├── sat/                          # Z3-based SAT/SMT encoding of the constraints
│   ├── cnf_encoder.py
│   └── run_sat.py
├── engine/                       # LLM search loop (`agy -p`) and supporting archives
│   ├── loongflow_main.py         # Plan-Execute-Summary orchestrator
│   ├── planner.py                # Stage 1: blueprint before code
│   ├── executor.py               # Stage 2: code synthesis, verification, GPU polish
│   ├── summarizer.py             # Stage 3: reflection, memory update
│   ├── pes_memory.py             # MAP-Elites archive + episodic lesson store
│   ├── map_elites.py             # Quality-diversity archive
│   ├── baseline_graphs.py        # Markström, generalized Petersen, ring generators
│   ├── evaluator.py              # Subprocess bridge to verifier_64
│   ├── agy_client.py             # Local `agy` CLI wrapper
│   ├── main.py, island.py,       # Island-model evolutionary loop
│   │   mutator.py, seeding.py
│   └── report.py                 # Progress reporter
├── tests/test_pipeline.py        # Python unit tests
└── formalization/                # Lean 4 (Lake) project — builds, Lean core only
    ├── lean-toolchain
    ├── lakefile.toml
    ├── Problem64.lean
    └── Problem64/
        ├── Basic.lean            # Cycle predicate and conjecture statement
        └── Certificate.lean      # Kernel-checked (`by decide`) self-tests
```

---

## 3. The Attack Vectors

### I. CUDA swarm search (`cuda/swarm_64.exe`)
- Thousands of independent annealing threads (default 10,240, set with `--threads N`), each
  holding a graph as a `uint64_t[64]` adjacency bitmask in registers.
- Strict 3-regularity is preserved by construction: a Möbius ladder $C_n(1, n/2)$ base plus
  double-edge (2-opt) swaps and occasional 3-opt swaps, which rewire edges without changing
  any degree.
- **Lexicographic energy.** `compute_energy` walks the tiers in order and returns as soon as
  one is violated, with a tier stride of $S = 10^6$:

  $$E(G) = \begin{cases}
    4S + \min(|C_4|,\ \mathrm{cap}) & |C_4| > 0\\
    3S + |C_8| & |C_4| = 0,\ |C_8| > 0\\
    2S + |C_{16}| & |C_4| = |C_8| = 0,\ |C_{16}| > 0\\
    S + |C_{32}| & |C_4| = |C_8| = |C_{16}| = 0,\ |C_{32}| > 0,\ n \ge 32\\
    0 & \text{all four absent}
  \end{cases}$$

  Because the stride dominates any within-tier count, the search can never buy a shallow
  violation with a deep one. The weighted sum printed in earlier versions of this file,
  $1000|C_4| + 200|C_8| + 50|C_{16}| + 10|C_{32}|$, did exactly that: one $C_8$ scored 300
  while 424 $C_{16}$ scored 21220, so the annealer preferred creating an 8-cycle.
- Counts are capped by `--count-cap N` (default $10^6$, clamped to $S - 1$). Deeper tiers are
  counted only once the shallower ones are zero, and the tiers that were not reached are
  reported as $-1$ rather than $0$, so "not evaluated" is never mistaken for "absent".
- **Measured throughput**: about **8.2 million evaluated moves/sec** on an RTX 4070 Super with
  uncapped counting. That figure counts only the moves whose energy was actually computed. The
  numbers previously published in this repository (68.2M here, 27M in the root README) were
  `threads × iterations`, which counted loop turns that bailed out before ever proposing a
  valid swap.
- Each thread keeps its own best energy and adjacency matrix; the host copies all of them back
  and reduces to the global best. There is no atomic global best inside the kernel.
- **Refuses $n > 62$.** At $n = 64$ the length 64 is itself a power of two and the kernel has
  no $C_{64}$ tier, so energy 0 would not mean counterexample. The Rust verifier does check
  $C_{64}$ at $n = 64$.
- Seeded finisher mode: `--seed-file PATH` (preferred, no argv length limit) or
  `--seed-json JSON` puts the seed in thread 0 and perturbs the other threads around it.

### II. Rust verifier (`target/release/verifier_64.exe`) — ground truth
- Tests **every** power-of-two length $\le n$, unconditionally. With `--full --cap N` it
  reports an exact count per length plus a `capped` flag when the counter hit `N`.
- Also reports edge count, min/max degree, cubicity, girth, diameter, connectivity, component
  count, bipartiteness, and a `cycle_witness` path for the first violation found.
- Earlier versions short-circuited: they tested $C_8$ only when $C_4$ was absent and
  serialized the untested tiers as `false`. That reads as "absent" but meant "not checked",
  which is how the false table in section 5 came about.

### III. Plan-Execute-Summary loop (`engine/loongflow_main.py`)
The Plan-Execute-Summary (PES) rhythm is a pattern **borrowed** from Baidu's LoongFlow agent
framework (<https://github.com/baidu-baige/LoongFlow>). **LoongFlow is not a dependency of
this repository**: there is no import of it, no entry for it in `pyproject.toml`, and no
vendored code. `planner.py`, `executor.py` and `summarizer.py` are local modules that shell
out to the `agy` CLI.

1. **Planner** — reads MAP-Elites coverage and `lessons_learned.json`, then writes an explicit
   mathematical blueprint (ring lifts, Cayley graphs, snark covers) before any code exists.
2. **Executor** — synthesizes the generator, verifies candidates with `verifier_64`, and hands
   promising graphs to the GPU swarm as a seed.
3. **Summarizer** — reflects on the reported cycle witness and appends a distilled rule to
   `lessons_learned.json`.

### IV. SAT / SMT pipeline (`sat/`)
`sat/cnf_encoder.py` encodes the structural constraints — 3-regularity plus forbidden
power-of-two cycle lengths — into propositional clauses with symmetry breaking, and
`sat/run_sat.py` drives Z3 over that encoding to settle small orders exactly. Both files are
under concurrent revision; read them directly for the current flags and encoding.

---

## 4. Quickstart Commands

```bash
cd erdos-64

# 1. Build the Rust verifier and the CUDA kernel
make build-verifier                  # cargo build --release
make build-cuda                      # or: cuda\build.bat  (set CUDA_ARCH to override sm_89)

# 2. Tests (cargo test + python unittest)
make test

# 3. Multi-order campaign. Defaults: --orders 36,38,40,42,44,48 --iters 50000
#    --rounds 3 --threads 10240 --count-cap 1000. --no-pes skips the LLM cycles.
uv run python campaign_solver.py --orders 36,38,40,42,44 --rounds 3

# 4. Standalone GPU swarm. Defaults: n = 32, 2000 iterations, --threads 10240,
#    --temp 4, --count-cap 1000000, --stagnation 2000. n > 62 is refused.
./cuda/swarm_64.exe 36 50000 --seed-file cuda/best_swarm_n36.json

# 5. Plan-Execute-Summary loop. Defaults: --iterations 5 --test-ns 36,38,40
#    --timeout 90 --count-cap 1000.
uv run python -m engine.loongflow_main --iterations 5 --test-ns 36,38,40

# 6. Verify one candidate (never trust the kernel's own energy)
uv run python tools/verify_graph.py cuda/best_swarm_n36.json --cap 100000
./target/release/verifier_64.exe --full --cap 100000 < cuda/best_swarm_n36.json
./target/release/verifier_64.exe --markstrom     # built-in fixtures: --k4, --petersen

# 7. Regenerate the table in section 5
uv run python tools/recount_candidates.py --cap 100000
```

---

## 5. Candidate Graphs ($n = 32 \dots 60$)

**This table is generated by `tools/recount_candidates.py --cap 100000` — do not hand-edit
it.** Every count comes from `verifier_64 --full`, which tests every power-of-two length
$\le n$. A count printed as `N+` means the counter hit its cap, so `N` is only a lower bound.
`n/a` means the length exceeds $n$.

| Order $n$ | $\lvert E \rvert$ | Regularity | Connected | Girth | Diam | $C_4$ | $C_8$ | $C_{16}$ | $C_{32}$ | $C_{64}$ | Counterexample | Candidate File |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **32** | 48 | Cubic ($d=3$) | yes | 3 | 7 | 0 | 0 | 219 | 5 | n/a | no | `cuda/best_swarm_n32.json` |
| **34** | 51 | Cubic ($d=3$) | yes | 3 | 6 | 0 | 0 | 545 | 822 | n/a | no | `cuda/best_swarm_n34.json` |
| **36** | 54 | Cubic ($d=3$) | yes | 3 | 8 | 0 | 0 | 173 | 1788 | n/a | no | `cuda/best_swarm_n36.json` |
| **38** | 57 | Cubic ($d=3$) | yes | 3 | 6 | 0 | 0 | 768 | 28154 | n/a | no | `cuda/best_swarm_n38.json` |
| **40** | 60 | Cubic ($d=3$) | yes | 3 | 6 | 0 | 0 | 889 | 73888 | n/a | no | `cuda/best_swarm_n40.json` |
| **42** | 63 | Cubic ($d=3$) | yes | 3 | 7 | 0 | 0 | 820 | 100000+ | n/a | no | `cuda/best_swarm_n42.json` |
| **44** | 66 | Cubic ($d=3$) | yes | 3 | 6 | 0 | 0 | 1018 | 100000+ | n/a | no | `cuda/best_swarm_n44.json` |
| **48** | 72 | Cubic ($d=3$) | yes | 3 | 7 | 0 | 0 | 1076 | 100000+ | n/a | no | `cuda/best_swarm_n48.json` |
| **50** | 75 | Cubic ($d=3$) | yes | 3 | 7 | 0 | 0 | 1252 | 100000+ | n/a | no | `cuda/best_swarm_n50.json` |
| **52** | 78 | Cubic ($d=3$) | yes | 3 | 7 | 0 | 0 | 1183 | 100000+ | n/a | no | `cuda/best_swarm_n52.json` |
| **54** | 81 | Cubic ($d=3$) | yes | 3 | 7 | 0 | 0 | 1307 | 100000+ | n/a | no | `cuda/best_swarm_n54.json` |
| **56** | 84 | Cubic ($d=3$) | yes | 3 | 7 | 0 | 0 | 1270 | 100000+ | n/a | no | `cuda/best_swarm_n56.json` |
| **60** | 90 | Cubic ($d=3$) | yes | 3 | 8 | 0 | 0 | 1360 | 100000+ | n/a | no | `cuda/best_swarm_n60.json` |

What the table says: the swarm reliably drives $C_4$ and $C_8$ to zero, and nothing beyond
that. The 16-cycle count runs from 219 to 1360 and the 32-cycle count from 5 into six figures.
Each `cuda/best_swarm_n*.json` carries these numbers in a `verified` block. The orders
$n \le 34$ sit below the exhaustive-search frontier of section 1 and are kept only as
regression fixtures.

---

## 6. Post-Mortem: the "$C_{16}$ Energy Canyon" That Never Existed

Earlier versions of this file reported a table with $C_{16} = 1$ and $C_{32} = 0$ at every
order and built a section of topological analysis on top of it — a "$C_{16}$ energy canyon" in
which 2-opt moves supposedly could not break the last 16-cycle without recreating an 8-cycle.
None of that was real. The correct account:

1. **The table printed a boolean as a count.** The verifier short-circuited its tiers and
   emitted `false` for the ones it never reached; the report rendered that as `1` in the
   $C_{16}$ column and `0` in the $C_{32}$ column. $C_{32}$ was never computed at all. The
   real counts are in section 5: hundreds to over a thousand 16-cycles, and up to six figures
   of 32-cycles.
2. **There was no gradient to get stuck in.** The CUDA cycle counter early-returned once it
   had found 5 cycles, so the energy saturated at 270 for essentially every graph the swarm
   touched. The search was not trapped in a canyon; it was optimizing a constant.
3. **The weighted sum pushed the wrong way.** With
   $1000|C_4| + 200|C_8| + 50|C_{16}| + 10|C_{32}|$, a single 8-cycle scored 300 while 424
   16-cycles scored 21220, so any move trading many deep violations for one shallow violation
   looked like an enormous win. That is backwards: a counterexample needs *every* tier at
   zero.

Both bugs are fixed. The counter is uncapped inside the active tier by default, and the energy
is the lexicographic tier key of section 3. With those in place, a 30,000-step seeded run on
$n = 32$ cut the 16-cycle count from 424 to 219 — a real improvement on a real gradient, and
still nowhere near a counterexample.

The lesson worth keeping: **confirm that an objective function actually varies before
attributing a search failure to the shape of the landscape**, and cross-check every counter
against an independent implementation.

---

## 7. What the Lean 4 Formalization Does and Does Not Establish

`formalization/` is a Lake project that builds (Lean core only, no Mathlib) and contains **no
`sorry`**.

- `Problem64/Basic.lean` defines a genuine cycle predicate: pairwise-distinct vertices,
  adjacency between consecutive vertices, and a closing edge. The previous statement asked
  only for a *list* of the right length, which `[v, v, v, v]` satisfies, so it certified
  nothing.
- `Problem64/Certificate.lean` holds kernel-checked `by decide` self-tests over $K_4$, the
  Petersen graph and Markström's graph.

**Checked by the Lean kernel**: well-formedness of the adjacency data, 3-regularity, minimum
degree, and the presence or absence of *short* power-of-two cycle lengths.

**Not checked by Lean**: absence of $C_{16}$ and $C_{32}$ on a graph of 36 or more vertices.
`hasCycleOfLength` enumerates simple paths, and at length 16 on a cubic graph there are on the
order of a million of them — the kernel will not evaluate that. Those lengths are checked by
the Rust verifier, which is therefore a **trusted** component, not a verified one. Closing
that gap requires either a Lean decision procedure with real pruning or an independent
reimplementation of the counter.
