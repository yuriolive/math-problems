# Erdős 857 — sunflower-free capacity

> **Statement.** A family $\mathcal{F}$ of subsets of $[n]$ is **3-sunflower-free** if no
> three distinct members $A, B, C$ satisfy
> $A \cap B = A \cap C = B \cap C = A \cap B \cap C$. (Such a triple is a *sunflower with
> three petals*: all pairwise intersections coincide with the common core.) The
> **sunflower-free capacity** is
> $\mu_3 = \lim_{n \to \infty} \max\{|\mathcal{F}|^{1/n}\}$ over 3-sunflower-free families
> on $[n]$. Erdős conjectured $\mu_3 < 2$; determining $\mu_3$ is open.

> **Status.** Open. $1.551 < \mu_3 < 1.8899$. Problem page:
> [erdosproblems.com/857](https://www.erdosproblems.com/857), also tracked as optimization
> constant C49.

## 0. Intake

Answered before any code was written. Rule 6 and Rule 12 both apply here: read the
literature and check the instrument's reach before spending compute.

### 1. Can a compiled ground-truth checker be written in about a day?

> It defines what a solution *is*. Without it a search produces numbers nobody
> should trust, and every published figure here that turned out to be false came
> from trusting a search kernel's own counters.

**Answer.** Yes. With each set held as a `u64` bitmask ($n \le 64$), testing one triple is
three ANDs and two comparisons: $A \cap B = A \cap C = B \cap C$ suffices, since equality of
the three pairwise intersections forces each to equal $A \cap B \cap C$. A full audit of a
family of size $m$ is $O(m^3)$ word operations; an incremental check when one set changes is
$O(m^2)$. This is the same shape as `problems/erdos/64/verifier`, which is the strongest
part of that problem's stack.

### 2. Does the objective have a gradient — does a small perturbation move the score?

> Circle packing rewards the twelfth decimal place, so evolutionary search climbs.
> A lexicographic integer profile barely moves under an edge swap, so it does not.
> This single property predicts whether search or proof is the right instrument.

**Answer.** Yes, and this is why the candidate was chosen. The headline quantity
$|\mathcal{F}|$ is a flat integer — but the search does not optimise it. Fix a target size
$m$ and **minimise the number of violating triples** — write $T(\mathcal{F})$ for the
count of triples that form a sunflower. Swapping one set changes $T$ by
$O(m^2)$, so nearly every move moves the score: a dense min-conflicts landscape rather
than a plateau. This is the standard reformulation that made the SAT and annealing layers
work for Erdős #64, and it is the opposite of the max-over-pairs objectives that killed
most of the rejected candidates in [`../../CANDIDATES.md`](../../CANDIDATES.md).

### 3. Is there a published open gap strictly easier than the headline conjecture?

> There usually is, and it is usually far more tractable. Keep it one flag away
> from the main objective, and never conflate a hit on it with the harder claim.

**Answer.** Yes. Erdős's conjecture is $\mu_3 < 2$; the strictly easier target is to
**improve the lower bound past $1.551$** (or past $1.554$, see §1). That needs one explicit
uniform family, not an asymptotic argument, and each improvement is a self-contained
increment.

### 4. Is the reachable instance size inside the checker's hard limit?

> State the limit as a number and the target range as a number, in the same units,
> and compare them here.

**Answer.** Yes, with room. To beat $1.554$ requires a family of size $m > 1.554^n$:

| $n$ | required $m > 1.554^n$ |
| ---: | ---: |
| 12 | 199 |
| 16 | 1,157 |
| 20 | 6,746 |
| 24 | 39,340 |

The `u64` mask limit is $n \le 64$; the $O(m^3)$ full audit stays practical to
$m \approx 5 \times 10^4$. The working window $n = 12 \ldots 24$ sits inside both. Compare
Erdős #64, where the verifier stopped at 64 vertices while the live target ran to 78 —
this is the check that problem failed.

**Verdict.** A search target with a compiled checker, a real gradient, and a reachable
window. All four questions pass.

## 1. Known results

| Result | Value | Source |
| :--- | :--- | :--- |
| Lower bound | $1.551 < \mu_3$ | Deuber, Erdős, Gunderson, Kostochka, Meyer, *A rainbow Ramsey-type problem…*, [doi:10.1006/jcta.1997.2778](https://doi.org/10.1006/jcta.1997.2778) — peer-reviewed |
| Better lower bound | $1.554$ | Naslund, **unpublished**; cited in Naslund–Sawin, [doi:10.1017/fms.2017.12](https://doi.org/10.1017/fms.2017.12) |
| Upper bound | $\mu_3 < 1.8899$ | Naslund–Sawin, *Upper bounds for sunflower-free sets*, same DOI |
| Conjecture | $\mu_3 < 2$ | Erdős |

The $1.554$ figure is a manuscript that could not be located directly — only its citation
inside the peer-reviewed Naslund–Sawin paper. Treat $1.551$ as the citable record and
$1.554$ as the real bar to clear.

## 2. What would count as progress

An explicit **uniform** 3-sunflower-free family on $[n]$ with $|\mathcal{F}|^{1/n} > 1.554$,
verified by the compiled checker, together with the tensor-power argument giving the
asymptotic bound.

**The trap, and it is sharp.** The tensor-power (direct sum) argument requires the seed
family to be **strictly uniform** — every set of the same size. A search allowed to range
over non-uniform families will find a false record almost immediately: $f(7) = 28$ gives
$28^{1/7} \approx 1.609 > 1.554$, which yields **no** asymptotic bound, because
non-uniform families lose sunflower-freeness under the direct sum. The checker must enforce
uniformity as a hard invariant, not as a scoring term. This is precisely the class of error
this repository has published once already.

## 2b. Prior art, and what it settles

`SproutSeeds/sunflower-lean` (verified to exist: pushed 2026-06-14, 1 star, GitHub detects
no license despite the README claiming Apache-2.0) is a Lean 4 + SAT/LRAT development of
the **weak sunflower numbers** $M(n,3)$, announced on the erdosproblems forum. The screening
pass for this repository could not confirm that repository existed; it does, and this
section corrects the record.

Their certified exact values, and their $n$-th roots:

| $n$ | $M(n,3)$ | $M(n,3)^{1/n}$ |
| ---: | ---: | ---: |
| 1 | 2 | 2.0000 |
| 2 | 3 | 1.7321 |
| 3 | 5 | 1.7100 |
| 4 | 8 | 1.6818 |
| 5 | 12 | 1.6438 |
| 6 | 19 | 1.6335 |
| 7 | 29 | 1.6178 |

$M(1..4,3)$ via `native_decide`; $M(5,3)$, $M(6,3)$, $M(7,3)$ via SAT with independently
re-checkable LRAT certificates, sorry-free.

**What this settles.** Every one of those roots exceeds the $1.554$ bar, and
$M(7,3)^{1/7} = 1.6178$ exceeds the citable record $1.551$ by a wide margin. If exact small
values transferred to a lower bound on $\mu_3$, the record would already be $1.6178$. It is
not. So this is direct, numerical confirmation of the uniformity trap in §2: **non-uniform
families do not tensorize**, and a search that reports $|\mathcal{F}|^{1/n}$ for small $n$
is reporting nothing about $\mu_3$.

**An open question their data raises.** That sequence is *decreasing*. For capacity
quantities satisfying $M(n+m) \le M(n) \cdot M(m)$, Fekete's lemma gives
$\mu_3 = \inf_n M(n)^{1/n}$, making every term an **upper** bound — and $1.6178$ would then
sharply improve Naslund–Sawin's $\mu_3 < 1.8899$. Three possibilities, not yet
distinguished:

1. the submultiplicativity assumption fails for this quantity;
2. $M(n,3)$ is a different object — "weak" sunflower, with an empty core counted as a
   sunflower, which changes the admissible family class;
3. it holds, and is an unclaimed consequence of their own verified numbers.

Resolving which is worth an hour before any construction search starts, because under (3)
the contribution is a reading of existing certified data rather than a new construction.
Settle it against the definitions in Naslund–Sawin ([doi:10.1017/fms.2017.12](https://doi.org/10.1017/fms.2017.12))
and their `M3/` development, and record the answer here either way.

**Territory.** Their work is exact finite values and the intersection-capped variant
$M_3(l,t)$. Erdős #857 asks for the asymptotic capacity $\mu_3$ — adjacent, not the same.
Credit them wherever this problem builds on their numbers.

## 3. Measured state

Every number below is the compiled checker's, never a search kernel's. A trailing `+` means
the solver's budget ran out before the maximum was settled, so the value is a lower bound
and the cell is **not** an exact value.

$M_{\text{unif}}(n,k)$, largest $k$-uniform 3-sunflower-free family on $[n]$:

| $n$ | best $k$ | $M_{\text{unif}}$ | $M^{1/n}$ | exact? |
| ---: | ---: | ---: | ---: | :--- |
| 6 | 3 | 10 | 1.467799 | exact |
| 7 | 4 | 15 | 1.472357 | exact |
| 8 | 4 | 24 | 1.487738 | exact |
| 9 | 5 | 42+ | 1.514820 | lower bound |
| 10 | 6 | 70+ | **1.529360** | lower bound |

Complete exact rows for $n \le 8$ and the full $(n,k)$ grid to $n = 12$ are in the sweep's
JSON output; the peak $k$ tracks roughly $0.6n$.

**Best verified lower bound: $\mu_3 \ge 1.529360$**, from 70 sets at $n = 10$, $k = 6$.
That is **below** the citable record of 1.551, so it is not an improvement on anything
published — it is where this repository's search currently reaches.

### What produced these, and how they are cross-checked

* `verifier/` — the checker. Two independent implementations inside it, a bitmask counter
  and a reference over sorted element vectors sharing no code, agree on every cell to
  $n = 7$.
* `verifier/src/bin/brute.rs` — exhaustive branch and bound, a different algorithm from
  "encode and ask a solver". Agrees with SAT on every exact cell to $n = 6$.
* `sat/sweep.py` — CaDiCaL 1.9.5 via python-sat, cells across processes. Every satisfiable
  model is re-derived by the checker before it counts.
* `cuda/swarm_857.cu` — annealer, one family per block. Its own energy counter was
  differentially tested against the checker on six cases and agrees exactly.

### Where each instrument stops

| Instrument | Best at $n{=}10,k{=}6$ | Note |
| :--- | ---: | :--- |
| CaDiCaL | **70** | 18+ minutes could not settle whether 71 exists |
| annealer, per block | 60 | stalls at energy 40 for $m = 70$ |
| annealer, per thread | 44 | superseded |

The annealer underperforms SAT where both can run, which is the opposite of the reasoning
that motivated building it. Its case is that it reaches $n \ge 14$ where SAT cannot, and
that case is not yet demonstrated.

The $m = 70$ stall sits at energy exactly 40 across three seeds and two structurally
different kernels. The checker confirms 40 is the true count each time, so it is a genuine
local minimum rather than a counting bug — the move set is getting trapped, and a move that
retargets two members at once is the obvious thing to try next.

## 4. Go/no-go gate

Before any Rust or CUDA is written: extract the explicit base construction from Deuber et
al. (1997) and verify by direct computation that it yields $1.551$. If it does not
reproduce, the objective is not understood and this problem is rejected after all.

Rationale: in three of the twenty candidates screened for this repository — including both
that survived — the scout's own statement of the objective was mathematically wrong. See
[`../../CANDIDATES.md`](../../CANDIDATES.md).

## 5. Layout

```
problems/erdos/857/
├── README.md               this file
├── ROADMAP.md              what is worth trying, what is closed, and why
├── verifier/               compiled ground-truth checker
└── tests/                  differential tests against a slow reference
```

`cuda/`, `sat/` and `paper/` come later, once the gate passes. The shared paper build needs
no configuration: `uv run python tools/paper/build.py problems/erdos/857/paper`.
