---
name: neuro-symbolic-math
description: Searches for counterexamples and extremal constructions in combinatorics, graph theory, and number theory using a hybrid neuro-symbolic architecture — an LLM Plan-Execute-Summary loop, compiled bit-parallel Rust verifiers, massive CUDA swarm simulated annealing, MAP-Elites quality-diversity archives, SAT/SMT constraint solving, and Lean 4 certificates — with explicit rules for honest measurement and reporting.
---

# Neuro-Symbolic Mathematical Discovery Skill

A methodology and reusable software template for searching for mathematical counterexamples,
probing extremal bounds, and mechanizing verification.

Read section 6 (Honest Measurement and Reporting) before writing any results down. Most of the
failures this template has actually produced were not search failures — they were measurement
and reporting failures that made a broken search look like a discovery.

---

## 1. The 5-Tier Neuro-Symbolic Stack

When attacking an open conjecture (Erdős problems, Ramsey bounds, distinct subset sums,
girth/cycle problems), do not rely on a single approach. Combine top-down reasoning with
bottom-up GPU search:

```
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 1: Cognitive Macro-Architect (LLM PES loop via a local CLI)      │
│  • Formulates algebraic blueprints (Cayley graphs, covers, snarks)     │
│  • Plan -> Execute -> Summarize rhythm                                 │
│  • Distills failure modes into a persistent lessons_learned.json       │
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
│  Tier 3: GPU Micro-Finisher (CUDA swarm annealing)                     │
│  • 10,000+ parallel threads running invariant-preserving local moves   │
│  • Lexicographic tier energy; deeper tiers evaluated only when the     │
│    shallower ones are exactly zero, and never with a capped counter    │
│    inside the active tier (see the warning below)                      │
│  • Finisher Mode: seeds from Tier 1's near-optimal macro-graph         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 4: Ground Truth Verifier (Compiled Rust, no short-circuiting)    │
│  • 64-bit integer bitmasks, word-aligned shifts, dynamic popcount      │
│  • Tests every constraint unconditionally and reports exact counts     │
│  • Outputs machine-readable diagnostics and a witness for each failure │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 5: Formal Proof & Constraint Solving (Lean 4 + Z3 / Kissat)      │
│  • SAT: exhausts small bounds and infills exact subgraphs              │
│  • Lean 4: kernel-checks a certificate that states a real proposition  │
└────────────────────────────────────────────────────────────────────────┘
```

> **Tier 3 warning.** Skipping deep constraints while a shallow one is violated is a sound
> throughput optimization *only* if two things hold: the count inside the currently active
> tier is exact (not capped), and every unevaluated tier is reported as "unknown" rather than
> as "satisfied". Violate either and the objective flattens into a constant while still
> looking like a fitness function. This has happened in practice; see section 5, part III.

---

## 2. Standard Problem Scaffolding Runbook

When attacking a new open problem (e.g. `erdos-X/`):

### Step 1: Establish Problem Invariants & Active Frontier
1. Formulate the conjecture mathematically, and find the official problem page.
2. **Read the literature before writing code, and record who proved what.** Two questions
   decide whether the search is worth running at all:
   - *Is there a theorem that confines a counterexample to a narrow regime?* For the
     Erdős–Gyárfás conjecture, Liu and Montgomery proved the conjecture true once the minimum
     degree exceeds an absolute constant, so only very small minimum degree can host a
     counterexample. A result like that is the whole justification for the search space.
   - *Where does exhaustive enumeration already reach?* For cubic Erdős–Gyárfás, Markström
     showed a cubic counterexample needs at least 30 vertices, and a published exhaustive
     search settles general cubic graphs to $n \le 34$, so the open corridor begins at
     $n = 36$. (An early version of this skill credited that bound to Royle; it is
     Markström's. Attribute bounds to the paper you actually read.)
3. Distinguish **theorems** from **heuristics** in the search restriction. "A minimal
   counterexample has at least $2/3$ cubic vertices" is a theorem; "so search only cubic
   graphs" is a heuristic. Write down which is which, or the write-up will overclaim.
4. Enumerate the families where the conjecture is already confirmed — any construction landing
   inside one of them is dead on arrival.

### Step 2: High-Performance Rust Verifier (`verifier/`)
1. Implement a bit-parallel 64-bit integer bitmask representation (`[u64; 64]` for graphs
   $\le 64$ vertices; `Vec<u64>` dynamic word sets for subset sums).
2. Implement fast necessary filters:
   - For graphs: common-neighbour popcount `(adj[u] & adj[w]).count_ones() >= 2` for $C_4$.
   - For subset sums: pair-difference collisions $a_j - a_i = a_l - a_k$.
3. Implement depth-bounded DFS with visited bitmasks returning an exact **witness**
   (e.g. the vertices of the offending cycle).
4. **The verifier must not short-circuit.** It is the ground truth, so it tests every
   constraint every time, even the ones a cheaper tier already ruled the graph out on. Offer
   counting mode behind a flag (`--full --cap N`) and mark any count that reached the cap as a
   lower bound.
5. Report the invariants that make a candidate auditable, not just the target constraint:
   edges, min/max degree, girth, diameter, connectivity, component count, bipartiteness. A
   "counterexample" that turns out to be disconnected or non-regular is caught here.
6. CLI interface with JSON output that distinguishes absent from unchecked:
   ```json
   {"counterexample": false,
    "checked_lengths": [4, 8, 16, 32],
    "counts": [{"length": 16, "count": 219, "capped": false}],
    "cycle_witness": [0, 5, 12, 18],
    "diagnostic_trace": "Collision: cycle of length 16 on vertices [...]"}
   ```
7. Exit code `0` if counterexample, `1` if a violation was found, `2` on bad input.

### Step 3: Massive CUDA Swarm Searcher (`cuda/swarm.cu`)
1. **Preserve Invariants by Construction**:
   - For cubic graphs: use double-edge swaps (2-opt) that rewire $(u, v)$ and $(x, y)$ to
     $(u, x)$ and $(v, y)$, preserving every degree exactly.
   - Warmup scramble: start from a guaranteed valid structure (e.g. a Möbius ladder) and
     scramble with a few dozen swaps.
2. **Lexicographic Tier Energy — not a weighted sum.** Rank the constraints from shallow to
   deep, give each a stride $S$ larger than any count that can occur inside a tier, and let
   the energy be the tier index times $S$ plus the count in that tier:

   $$E = (\text{tiers left to clear}) \cdot S + (\text{count in the active tier}), \qquad S = 10^6$$

   A weighted sum such as $1000|C_4| + 200|C_8| + 50|C_{16}| + 10|C_{32}|$ is actively wrong
   here: it scores one 8-cycle at 300 and 424 16-cycles at 21220, so the annealer happily
   trades many deep violations for one shallow violation — the opposite of progress, since a
   counterexample needs *every* tier at zero. With a lexicographic key, regressing a tier
   costs $S$ and is effectively never accepted.
3. **Count exactly inside the active tier.** Evaluating an expensive deep constraint only when
   every shallower one is zero is fine and keeps throughput high. Capping the counter in the
   tier you are currently optimizing is not: if the counter early-returns at, say, 5, the
   energy saturates and the search has no gradient whatsoever. Cap only as an overflow guard
   (default the cap high, clamp it to $S - 1$), and expose it as a flag so it can be raised.
4. **Never encode "not evaluated" as zero.** Initialize the unreached tiers to $-1$ and keep
   that value in the output JSON. A downstream report that prints a boolean or a sentinel in a
   count column is how a false table gets published.
5. **Refuse inputs the energy cannot score.** If the kernel has tiers up to $C_{32}$ only,
   refuse $n \ge 64$, where length 64 is itself a power of two — otherwise energy 0 does not
   mean counterexample. Encode that refusal in the argument parser, not in a comment.
6. **Seeded Finisher Mode**:
   - Support `--seed-file PATH` (preferred: no argv length limit) and `--seed-json '<json>'`.
     Put the exact seed in thread 0 and perturb the others by $k = \text{tid} \bmod 8$ swaps.
   - Keep the best energy and adjacency **per thread** in `d_all_best_energy[tid]` and
     `d_all_best_adj + tid * n`, copy both arrays back, and reduce to the global best on the
     host. Do not use `atomicMin` on a single global energy word: the winning energy and the
     graph that achieved it would be written by different threads at different times, so the
     pair can be inconsistent. A single `d_found_flag` for early exit is fine, since it
     carries no payload.
7. **Report throughput as evaluated moves.** Accumulate a per-thread counter incremented only
   where the energy was actually computed, and divide the sum by the wall time.
   `threads × iterations` is not a move count — it counts loop turns that bailed out before
   proposing a valid move, and overstated one real kernel by roughly 8x.

### Step 4: LLM Plan-Execute-Summary Engine (`engine/`)
The Plan-Execute-Summary (PES) rhythm is a pattern borrowed from Baidu's LoongFlow agent
framework (<https://github.com/baidu-baige/LoongFlow>). Borrow the pattern; do not claim the
framework as a dependency unless you actually import it. Decompose LLM-driven discovery into
three specialized roles rather than blind code mutation:

1. **Planner (`planner.py`)**:
   - Prompts a local LLM CLI (no external API keys).
   - Injects: (a) parent code, (b) MAP-Elites coverage, (c) recent lessons from
     `lessons_learned.json`.
   - Produces an explicit **mathematical blueprint** specifying algebraic structures (Cayley
     graphs, voltage lifts, affine matchings) before any code is written.
2. **Executor (`executor.py`)**:
   - Synthesizes generator code conforming strictly to the blueprint.
   - Verifies across target sizes with the compiled verifier — never with the GPU's own
     energy, which is capped and tier-limited.
   - **Automated GPU polish**: if a candidate is valid and promising, pipe it to the swarm's
     seeded finisher mode.
3. **Summarizer (`summarizer.py`)**:
   - Performs **abductive reflection** on the witness trace: *why did this construction
     produce a cycle of length L, and what general rule prevents it next time?*
   - Appends the distilled rule to `lessons_learned.json` and inserts the candidate into the
     MAP-Elites archive.

### Step 5: Lean 4 Formal Certificate (`formalization/`)
1. Scaffold a Lake project with `lean-toolchain` and `lakefile.toml`. Depending only on Lean
   core (no Mathlib) keeps the certificate standalone and fast to build.
2. **State a proposition that is actually checkable, and check that it is not vacuous.** A
   certificate is worthless if the predicate can be satisfied by junk. A real case from this
   template: the conjecture was stated as "there exists a list of vertices whose length is a
   power of two", which `[v, v, v, v]` satisfies for any nonempty graph. The fix is a genuine
   cycle predicate — pairwise-distinct vertices, adjacency between consecutive vertices, and a
   closing edge. Add negative self-tests (`example : IsCycleOf g [0,0,0,0] = false := by
   decide`) so the vacuity cannot come back.
3. Auto-export the winning candidate into `Certificate.lean` and let `by decide` put the
   kernel behind every claim that fits.
4. **Never write `sorry`.** If an obligation is out of reach — for instance, absence of a
   16-cycle in a 36-vertex cubic graph, where path enumeration runs to millions of paths the
   kernel will not evaluate — do not paper over it with `sorry`, which reads as a proof to
   anyone skimming. Name it in a comment at the top of the file: what is kernel-checked, what
   is delegated, and to which trusted component. Then say the same thing in the README.
5. Keep the self-tests in the default build target so the machinery cannot silently rot.

---

## 3. Best Practices & Critical Rules

### Avoiding KaTeX Errors in Markdown Artifacts
- Never write `#C_k` in math mode. The `#` character is TeX's macro parameter token and
  triggers `You can't use 'macro parameter character #' in math mode`.
- Use standard set-cardinality notation instead: $|C_4|$, $|C_8|$, $|C_{16}|$.

### Preserving Windows Console Encoding
Windows default `cp1252` encoding crashes on emoji and unicode math symbols. Initialize Python
CLI scripts with:
```python
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
```
Read and write every data file with an explicit `encoding="utf-8"` for the same reason.

### Zero External API Keys Requirement
- Invoke the local authenticated CLI session:
  ```python
  import subprocess
  res = subprocess.run(["agy", "-p", prompt], capture_output=True, text=True, check=True)
  output = res.stdout.strip()
  ```
- This keeps the pipeline autonomous without third-party quotas or keys.

### Declare Only the Dependencies You Import
Before adding a package to `pyproject.toml`, grep for the import. Before a write-up claims a
framework, grep for it too. Aspirational dependencies bloat the lock file and turn into false
architecture claims in the README.

### CUDA Compilation on Windows
When `cl.exe` is not on the global `PATH`, activate the Visual Studio developer environment in
a subshell:
```bash
cmd /c 'call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && nvcc -O3 -std=c++17 -arch=sm_89 cuda/kernel.cu -o cuda/kernel.exe'
```
Better: commit a `build.bat` that probes the usual Build Tools / Community / Professional /
Enterprise locations, honours an already-set `VCINSTALLDIR`, and takes the architecture from an
overridable `CUDA_ARCH` variable, so the build is not pinned to one machine.

---

## 4. Reusable Reference Directory Layout

```
problem-name/
├── Makefile                      # Targets: build-verifier, build-cuda, test, search-*, report
├── campaign_solver.py            # Multi-order autonomous campaign orchestrator
├── lessons_learned.json          # Persistent knowledge base
├── results.db                    # SQLite run & evaluation log
├── verifier/                     # Rust bitmask verifier (ground truth, no short-circuiting)
│   ├── Cargo.toml
│   └── src/{lib.rs, main.rs}
├── cuda/                         # GPU swarm searcher
│   ├── swarm.cu                  # Lexicographic energy, ILS, temperature spread, finisher
│   ├── build.bat                 # Portable MSVC + nvcc build
│   └── best_swarm_n*.json        # Candidates, each with a verifier-produced block
├── tools/
│   ├── recount_candidates.py     # Regenerates the README results table from the verifier
│   └── verify_graph.py           # Verifies one candidate file
├── sat/                          # SMT / SAT pipeline (Z3 / Kissat)
│   └── run_sat.py
├── engine/                       # LLM PES loop
│   ├── loongflow_main.py         # Orchestrator
│   ├── planner.py                # Hypothesis blueprinting
│   ├── executor.py               # Code synthesis + GPU polish
│   ├── summarizer.py             # Abductive reflection
│   ├── pes_memory.py             # MAP-Elites + lessons
│   ├── map_elites.py             # Quality-diversity archive
│   └── evaluator.py              # Sandbox & verifier bridge
└── formalization/                # Lean 4 certificate (no `sorry`)
    ├── lakefile.toml
    └── Problem/Certificate.lean
```

Generate every results table in the README with a script in `tools/`, and say so in the README
next to the table. A hand-maintained table drifts from the verifier within days, and nobody can
tell afterwards which numbers were measured.

---

## 5. Advanced Swarm Search Patterns

### I. Iterated Local Search (ILS) & Reheating Pulses
Pure simulated annealing freezes at $T \to 0$ into greedy hill climbing, trapping the swarm in
local basins.
- Track `local_best_energy` and `local_best_adj` in each GPU thread.
- If a thread fails to improve for $K$ steps (e.g. 2,000), revert to `local_best_adj` and apply
  a reheat pulse ($T \leftarrow T_{\text{initial}} \times 0.7$).
- Put the cooling step and the stagnation check at the **top** of the loop. Below several
  `continue` statements they are skipped on exactly the iterations that bailed out early, so
  the effective cooling schedule silently differs from the intended one.
- This implements **basin hopping** directly in GPU registers.

### II. Spectral Temperature Diversity
Never use a uniform temperature across GPU threads. Spread the initial temperatures across
threads:
```cpp
float temp_mult = 0.02f + 2.98f * ((float)(tid % 128) / 127.0f);
float thread_initial_temp = initial_temp * temp_mult;
```
This gives greedy micro-polishing and wide basin jumping in a single kernel call. Scale the
band to the actual energy deltas: with a lexicographic key, a single violation inside a tier is
worth 1, so the useful temperature band is small and a tier regression is never accepted at any
temperature in it.

### III. Before Blaming the Landscape, Verify the Objective Has a Gradient
An earlier version of this skill described an "energy canyon": a search that reliably reached
$C_4 = 0$, $C_8 = 0$ and then stalled forever at $C_{16} = 1$, supposedly because no 2-edge
swap could break the last 16-cycle without recreating an 8-cycle. **That phenomenon did not
exist.** Two bugs manufactured it:
- The verifier short-circuited its tiers and serialized the tiers it never reached as `false`.
  The report printed that boolean in a count column as `1`, and printed a never-computed tier
  as `0`. Re-measured with an unconditional counter, those graphs had hundreds to over a
  thousand 16-cycles and up to six figures of 32-cycles.
- The kernel's cycle counter early-returned at 5, so the energy saturated at a constant for
  essentially every graph. The search was not stuck in a canyon; it was optimizing a constant.

The reusable lesson:
1. **Instrument the objective before theorizing about it.** Log the distribution of energies
   actually observed. If the histogram is a spike, the bug is in the objective, not in the move
   set. A search that "converges instantly to the same value at every problem size" is a
   saturated counter, not a structural law.
2. **Cross-check every counter against an independent implementation.** Count the same quantity
   with a slow, obvious brute force on small instances and compare. The GPU counter and the
   ground-truth verifier must agree exactly wherever both are uncapped.
3. **Suspect any invariant that is too clean.** Identical values across a dozen unrelated
   problem sizes are far more often a stuck code path than a theorem.

Only after the objective is confirmed to vary is it worth reaching for stronger moves:
- **Targeted witness $k$-opt**: extract the exact vertex path from the verifier's witness and
  execute coordinated $k$-edge swaps on those edges.
- **Algebraic lift constraints**: feed the witness back into the planner to synthesize
  non-abelian voltage assignments whose element orders forbid the offending cycle length
  algebraically.

---

## 6. Honest Measurement and Reporting

These rules exist because every one of them was broken in a real run of this template, and each
break produced a confident, false claim in a README.

1. **Never publish a boolean as a count.** If a field can be "present/absent", give it a name
   that says so (`has_c16`) and keep counts in a separate, explicitly counted field. A results
   table showing `1` in a count column, uniformly, across every problem size, is a type error
   rendered as mathematics.
2. **"Absent" must never mean "not evaluated".** Carry three states — satisfied, violated,
   unknown — all the way from the kernel through the JSON into the table. Print `?` or `n/a`
   for unknown; never `0`.
3. **Mark lower bounds as lower bounds.** A count that hit its cap prints as `N+`, and the text
   must state what the cap was.
4. **Distinguish measured from derived throughput.** Report only quantities you counted at the
   point of work (evaluated moves, verified graphs) divided by measured wall time, and name the
   hardware and the settings. `threads × iterations`, `steps × swarm size`, and any figure
   arrived at by multiplication are not measurements. If the number came from a run, say which
   run; if it is an estimate, call it one.
5. **State which components are trusted and which are verified.** A pipeline whose Lean layer
   checks 3-regularity and short cycles, while a Rust binary checks the long cycles, has
   exactly one verified layer and one trusted layer. Write that sentence in the README. Never
   let a `sorry` or a delegated obligation be described as "formally certified".
6. **Keep the frontier honest.** Cite the exhaustive-search bound and start the search above
   it. Results below a settled frontier are regression fixtures, not discoveries — label them
   that way.
   Before spending GPU time, find the field's **scale function** and read the bound off it.
   For Erdős #64 it is $f(k)$, the order of the smallest cubic graph with no cycle of length
   $2^m$ for any $m \le k$: $f(3) = 24$ exactly and $54 \le f(4) \le 78$. Because any
   counterexample on $n \ge 16$ vertices is $\{C_4, C_8, C_{16}\}$-free, $f(4) \ge 54$ makes
   every order below 54 **provably empty** — a fact that retroactively explained months of
   fruitless search at $n = 32 \dots 52$ and that no amount of tuning could have overcome.
   A literature search costs minutes; a mis-aimed campaign costs days.
7. **Prefer the open published gap over the headline problem.** A scale function usually has a
   gap in it that is a real, citable, and far easier target than the conjecture itself — here,
   any cubic graph on 54–77 vertices with no $C_4$, $C_8$ or $C_{16}$ improves $f(4)$, and
   32-cycles are *allowed*. Make the objective configurable so the easier target is one flag
   away (`--max-length 16` versus `32`), and never let a hit on the easier target be reported
   as a solution to the harder one.
8. **Replace a falsified claim, do not annotate it.** When a published number turns out to be
   a bug, delete it and put the measured value in its place. Keep the account of what went
   wrong in the commit message, where it stays available without becoming part of the project
   guide — a reader wants the current state of the work, not a history of its corrections.
   The one thing that must survive into the docs is any consequence still in force: a
   component that is trusted rather than verified, or a bound that no longer holds.
9. **Every number in a write-up must come from a command you ran or a source you can cite.**
   If neither applies, leave it out. "Over 7.5 billion moves computed" and "51 million swaps in
   ~750 ms" are the shape of claims that get generated rather than measured.
