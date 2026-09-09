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

- Problem page: [erdosproblems.com/64](https://www.erdosproblems.com/64).
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
  - Garcia (Sept 2026, [arXiv:2609.04686](https://arxiv.org/abs/2609.04686)) proved by
    SAT-based exhaustive search with DRAT certificates that every graph of minimum degree
    $\ge 3$ on at most 23 vertices contains a $C_4$ or a $C_8$, so **any counterexample has at
    least 24 vertices** (the previously published bound was 16), and the smallest
    minimum-degree-3 graph with neither a $C_4$ nor a $C_8$ has exactly 24 vertices.
  - Tranquilli ([arXiv:2608.02675](https://arxiv.org/abs/2608.02675)) covered cubic bipartite
    graphs on $n \le 58$, giving a **60-vertex lower bound for that class**.
  - Forum user `sallerk` (31 Aug 2026) reports extending the cubic bipartite sweep to
    $n \le 62$, and reports that their general (non-bipartite) cubic search reached only
    $n \le 34$. Both are unpublished. Code:
    <https://github.com/sallerk/erdos-notes/tree/main/p64>

### The $f(k)$ scale, and where a counterexample can actually live

The literature tracks this problem through

$$f(k) = \text{order of the smallest cubic graph with no cycle of length } 2^m \text{ for any } m \le k.$$

| | value | status |
| :--- | :--- | :--- |
| $f(2)$ (avoid $C_4$) | $10$ | exact — the Petersen graph (Exoo) |
| $f(3)$ (avoid $C_4, C_8$) | $24$ | exact — Markström |
| $f(4)$ (avoid $C_4, C_8, C_{16}$) | $54 \le f(4) \le 78$ | **open gap.** Lower bound an unpublished Markström computation; upper bound Exoo's 78-vertex graph |
| $f(5)$ (avoid $C_4 \dots C_{32}$) | $\le 450$ | Garcia, correcting Exoo. No published lower bound |
| $f(6)$ | $\le 32640$ | Garcia — the first bound for $f(6)$ |

Two consequences that govern every search in this repository:

1. **A cubic counterexample needs at least 54 vertices.** Any counterexample on $n \ge 16$
   vertices is in particular $\{C_4, C_8, C_{16}\}$-free, and $f(4) \ge 54$ says no cubic graph
   below 54 vertices is. So the orders $n = 32 \dots 52$ are not a hard frontier — they are
   **provably empty** for this target. The candidates recorded in section 5 at those orders
   could never have succeeded, whatever the search quality. They are kept as verifier
   fixtures, nothing more.
2. **Closing $f(4) \in [54, 78]$ is the one open target this tooling fits.** A cubic graph on
   54–77 vertices with no $C_4$, $C_8$ or $C_{16}$ would improve Exoo's bound. Note the target
   is $\{4, 8, 16\}$-free — **not** counterexample-free: $C_{32}$ is explicitly allowed, which
   makes it strictly easier than the conjecture. Garcia shows 78 is optimal among gadget
   designs on bases of $\le 12$ vertices, which constrains that construction route but says
   nothing about the 54–77 window, and nobody has searched it exhaustively.

   Caveat on this repository's reach: `verifier/` is a 64-vertex bitmask engine, so it covers
   only $54 \le n \le 64$ of that window. Widening it to 128 vertices would open the rest and
   would also let Exoo's 78-vertex graph be re-verified independently — worth doing, given
   that Garcia has just found a genuine error (spurious 8- and 32-cycles) in the sibling
   $f(5)$ construction.
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

The published bound in this line is Carr's $4/7$
([arXiv:2605.22844](https://arxiv.org/abs/2605.22844), "Every Minimal Counterexample to the
Erdős–Gyárfás Conjecture is Predominantly Cubic"). Bisch's $\ge 2/3$ improvement is on Zenodo
with a Lean 4 formalization but is not published, and a forum argument by
[`jul059`](https://www.erdosproblems.com/forum/thread/64#post-8130) (26 Jul 2026) strengthens it to a strict $> 2/3$ via
$|V_3| \ge 2|V_{\ge 4}| + 1$, posted as unverified. **That argument is theirs; this
repository contributes its formalization** — see `formalization-egc/` and section 6 — with
no `sorry` and no hypotheses beyond Bisch's own `IsMinCex`.

A second forum claim, Guillem Duran-Ballester's 250-page argument, is incomplete: a reviewer
produced an arithmetic counterexample to its Lemma 7.37(a), the author conceded, and the
author's own status log (`EG_LEAN_COMPLIANCE_REMAINING.md`, 2026-08-30) states that the
selected root is not a proof of the target theorem.

---

## 2. Architecture & File Structure

```
problems/erdos/64/
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
├── formalization/                # Lean 4 (Lake) project — builds, Lean core only
│   ├── Problem64.lean
│   └── Problem64/
│       ├── Basic.lean            # Cycle predicate and conjecture statement
│       └── Certificate.lean      # Kernel-checked (`by decide`) self-tests
└── formalization-egc/            # Lean 4 + Mathlib — the strict 2/3 bound, proved
    ├── EGCStrict.lean            # Counting and the equality analysis
    ├── EGCLift.lean              # Cycle lifting and the final bound
    ├── EGCDensity.lean           # The reformulation; conditional 12/17 bound
    ├── EGCBridge.lean            # Bisch's IsMinCex supplies the hypotheses
    │                             #   (needs EGC.lean fetched by hand; gitignored)
    └── AxiomCheck.lean           # `#print axioms` audit of every theorem
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
cd problems/erdos/64

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

Read these rows as verifier fixtures, not as near misses. By $f(4) \ge 54$ (section 1) no
cubic graph below 54 vertices avoids $\{C_4, C_8, C_{16}\}$, so every row up to $n = 52$ was
searching a provably empty set. The rows at $n \ge 54$ sit inside the open $f(4)$ window, but
they were produced by a search aimed at the harder counterexample target (which also forbids
$C_{32}$) rather than at $\{4, 8, 16\}$-freeness.

### The $f(4)$ attempt

`tools/f4_sweep.py` runs the swarm with `--max-length 16`, so the objective scores only
$\{C_4, C_8, C_{16}\}$ and 32-cycles are allowed. The table is generated by
`tools/f4_report.py` from `cuda/f4_best_n*.json`; every count comes from `verifier_64`, and
`N+` marks a count that hit the counter's cap:

| Order $n$ | $C_4$ | $C_8$ | $C_{16}$ | $C_{32}$ (allowed) |
| :---: | :---: | :---: | :---: | :---: |
| 54 | 0 | 0 | **74** | 100000+ |
| 56 | 0 | 0 | **222** | 100000+ |
| 58 | 0 | 0 | **37** | 100000+ |
| 60 | 0 | 0 | **1323** | 100000+ |
| 62 | 0 | 0 | **1270** | 100000+ |
| 64 | 0 | 0 | **1357** | 100000+ |

**No $\{4, 8, 16\}$-free graph was found, so $f(4) \le 78$ stands.** Nothing follows from the
failure: this is a heuristic search, not an exhaustive one, and the region may simply be empty
— $f(4) \ge 54$ is only a lower bound, and if the true value is near 78 then no graph exists
at these orders to find.

Three things are worth recording.

**Scoring the right objective was worth about 35×.** The $n = 58$ candidate went from
$C_{16} = 1307$ under the counterexample objective to 37 under the $f(4)$ objective. That gap
measures the cost of having aimed at the wrong target, not any property of the problem.

**Determinism was the binding constraint, not compute.** The kernel seeded its RNG with a
hardcoded constant, so a second round with the same arguments re-ran the first one move for
move. That is why $n = 60$ and $n = 62$ sat unchanged across rounds while $n = 58$ improved
(its seed file had changed underneath it). With `--rng-seed` and a per-order population,
$n = 54$ dropped 107 → 74 immediately, on an order previously treated as converged.

**How far this is from 0.** A random cubic graph on 60 vertices has about 1300 16-cycles
(measured with this verifier, 25 samples), against the classical $2^{16}/32 = 2048$ for fixed
length and large $n$. So 37 is roughly a 35-fold suppression below random — and still
infinitely far from the 0 that $f(4)$ requires. The record at 78 vertices was set by an
algebraic construction, not by local search, and Garcia has since shown 78 is optimal among
gadget designs on bases of at most 12 vertices.

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

## 6. What the Lean 4 Formalization Does and Does Not Establish

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

### `formalization-egc/`: the strict two-thirds bound, proved

A second, separate Lake project (this one *does* depend on Mathlib) proves a real theorem
about minimal counterexamples rather than checking a candidate graph:

$$|V_3| \ge 2|V_{\ge 4}| + 1, \qquad \text{hence} \qquad 3|V_3| > 2|V|,$$

i.e. strictly more than two thirds of the vertices of a minimal counterexample are cubic.
Carr's published bound is $4/7$; Bisch's $\ge 2/3$ is unpublished; the strict version was
posted as an unverified forum comment by [`jul059`](https://www.erdosproblems.com/forum/thread/64#post-8130). **The argument is theirs.**
What is contributed here is the machine-checked proof of it.

The argument: the double count $4|V_4| \le e(V_4,V_3) \le 2|V_3|$ gives $|V_3| \ge 2|V_4|$,
and equality would force every $V_4$ vertex to have degree exactly 4 and every cubic vertex
to have exactly two $V_4$ neighbours. Contracting $V_3$ then yields a 4-regular graph on
strictly fewer vertices, so minimality supplies it with a power-of-two cycle — and
re-inserting the cubic vertices turns that into a cycle of twice the length in $G$, which
$G$ cannot have. `EGCLift.lean` builds that lift and proves it is a cycle; the inserted
vertices are distinct because, in the equality case, a cubic vertex determines the
contraction edge it came from.

`EGCStrict.lean` has the counting and the equality analysis, `EGCLift.lean` the lifting and
the final bound, and `EGCBridge.lean` derives the hypotheses from Bisch's `IsMinCex` so the
statement is unconditional.

`EGCDensity.lean` goes further and isolates *what controls the constant* in this whole
family of bounds. Counting the $V_3$–$V_4$ edges from both ends gives

$$4|V_4| + S_3 \le 3|V_3|, \qquad S_3 = \sum_{v \in V_3} \operatorname{cd}(v),$$

so the constant is decided by $S_3$, i.e. by twice the number of edges *inside* $V_3$.
Carr's domination lemma gives $S_3 \ge |V_3|$, which reproduces Bisch's $2/3$ exactly —
so **$2/3$ is precisely the bound obtained when $G[V_3]$ is a perfect matching**, and a
$K_2$ component of $G[V_3]$ is the unique configuration attaining it. Assuming those away
yields a strictly better bound:

$$\text{no } K_2 \text{ component in } G[V_3] \;\Longrightarrow\; |V_3| \ge \tfrac{12}{17}|V| \approx 0.7059\,|V|.$$

That hypothesis is **not** removed, and section 1b of [ROADMAP.md](ROADMAP.md) records why
the obvious attacks fail: every local replacement that destroys a $K_2$ component shifts
cycle lengths by $\pm 1$ or $\pm 2$, so a $2^k$ cycle in the smaller graph lifts to
$2^k + 1$ or $2^k + 2$ and minimality yields nothing. It also records that the extremal
configuration is consistent with every known constraint, so no purely counting argument
built on these lemmas can beat $2/3$. **No `sorry`**, and every theorem audits to `propext`,
`Classical.choice`, `Quot.sound` only — run `lake env lean AxiomCheck.lean` to see it.

What it assumes: the four Carr/Bisch facts about a minimal counterexample, bundled as
`MinCexHyps` (minimum degree 3, $V_{\ge 4}$ independent, every vertex has a cubic
neighbour, minimality in the order, and no power-of-two cycle). Bisch's Lean file proves
all of them but carries no license, so it is not vendored; each field records which of his
lemmas supplies it. Discharging `MinCexHyps` from his file would make the theorem
unconditional.
