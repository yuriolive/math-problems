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
**improve the lower bound past $1.551$** (see §1; the $1.554$ figure is withdrawn). That needs one explicit
uniform family, not an asymptotic argument, and each improvement is a self-contained
increment.

### 4. Is the reachable instance size inside the checker's hard limit?

> State the limit as a number and the target range as a number, in the same units,
> and compare them here.

**Answer.** Yes, with room. To beat $1.551$ requires a family of size $m > 1.551^n$:

| $n$ | required $m > 1.551^n$ |
| ---: | ---: |
| 12 | 194 |
| 16 | 1,122 |
| 20 | 6,490 |
| 24 | 37,557 |

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
| ~~Better lower bound~~ | ~~$1.554$~~ | **Withdrawn — see below.** |
| Upper bound | $\mu_3 < 1.8899$ | Naslund–Sawin, *Upper bounds for sunflower-free sets*, same DOI |
| Conjecture | $\mu_3 < 2$ | Erdős |

**The $1.554$ figure does not stand, and the target is $1.551$.** It appears only in
[arXiv:1606.09575v1](https://arxiv.org/abs/1606.09575) (30 Jun 2016), citing "Eric Naslund.
*Lower bounds for capsets and sunflower-free sets.* Unpublished." The published Forum of
Mathematics Sigma version **removed both the sentence and the reference**: the string "554"
occurs zero times in it and its bibliography has no Naslund entry. The manuscript does not
appear to exist publicly in any form — not as a preprint, thesis, or slides — and later
papers (Tang–Zhang [arXiv:2512.20055](https://arxiv.org/abs/2512.20055), Frankl–Pach–Pálvölgyi
[arXiv:2310.16701](https://arxiv.org/html/2310.16701)) quote 1.551, not 1.554.

### The record is for NON-uniform families, and that may put it out of reach here

This is the finding that matters most, and it was not checked before the search was built.

Deuber–Erdős–Gunderson–Kostochka–Meyer's $1.551$ bounds $F(n,3)$, the largest family of
**arbitrary** subsets of $[n]$ with no 3-sunflower. Their construction is Sperner but
explicitly **not uniform**: a 388-set block on $n = 14$ whose members have sizes
$10, 8, 7, 7, 9, 9, 9, 9$, combined by a product lemma that beats plain direct sums, giving
73,388 sets on $n = 26$, then 2,837,219,400 on $n = 50$, and $1.551^{n-2}$ for every
$n \equiv 2 \pmod{48}$. Author's copy:
[jcta97degm.pdf](https://kostochk.web.illinois.edu/docs/old/jcta97degm.pdf). The paper
tabulates no small exact values.

A uniform family is a special case of an arbitrary one, so $M_{\text{unif}}$ still gives a
valid lower bound on $\mu_3$ — but the *uniform* capacity may be strictly smaller than
$1.551$, in which case **no uniform family will ever reach the record** and the route taken
here cannot succeed however far it is pushed. Nothing found settles this. Peebles' Sperner
data (below) caps the Sperner capacity near $1.5874$, and uniform implies Sperner, so the
uniform capacity lies somewhere in $[1.529, 1.5874]$ — possibly above 1.551, possibly not.

**Deciding that is the gate now.** Either find a uniform family beating 1.551, or determine
that the uniform capacity is below it, in which case the honest move is to switch to
non-uniform families and adopt DEGKM's product lemma rather than the direct sum.

## 2. What would count as progress

An explicit **uniform** 3-sunflower-free family on $[n]$ with $|\mathcal{F}|^{1/n} > 1.551$,
verified by the compiled checker, together with the tensor-power argument giving the
asymptotic bound.

**The trap, and it is sharp.** The tensor-power (direct sum) argument requires the seed
family to be **strictly uniform** — every set of the same size. A search allowed to range
over non-uniform families will find a false record almost immediately: $f(7) = 28$ gives
$28^{1/7} \approx 1.609 > 1.551$, which yields **no** asymptotic bound, because
non-uniform families lose sunflower-freeness under the direct sum. The checker must enforce
uniformity as a hard invariant, not as a scoring term. This is precisely the class of error
this repository has published once already.

## 1b. Where this quantity sits in the literature

$M_{\text{unif}}(n,k)$ — uniform **and** ground set fixed — is not a function the field
tracks. Kostochka's survey
([PDF](https://kostochk.web.illinois.edu/docs/2000/survey3.pdf), *Extremal problems on
Δ-systems*, Kluwer 2000) enumerates the four that are:

| | uniform | ground set fixed |
| :--- | :--- | :--- |
| $f(k,r)$ | yes | no |
| $g(k,r)$ (weak) | yes | no |
| $F(n,r)$ | no | yes |
| $G(n,r)$ (weak) | no | yes |

Ours is the missing fifth cell and has no standard name. The survey states verbatim that
"Abbott and B. Gardner proved in 1969 that $f(3,3) = 20$, and since then no other exact
value of $f(k,r)$ for $k \ge 3$ and $r \ge 3$ became known." An exhaustive OEIS search
(full-text for sunflower, Δ-system, and the value sequences) found no match.

### Three diagonals are known quantities, and they validate the checker

By complementation, $(A \cap B)^c = A^c \cup B^c$, so $M_{\text{unif}}(n,k)$ equals the
largest $(n-k)$-uniform family on $[n]$ with no three members having equal pairwise
**unions**. Counting which configurations can occur:

| diagonal | equals | our values | status |
| :--- | :--- | :--- | :--- |
| $k = n-1$ | $n$ | 4, 5, …, 12 | trivial, agrees |
| $k = n-2$ | $\mathrm{ex}(n, K_3) = \lfloor n^2/4 \rfloor$, **Mantel 1907** | 6, 9, 12, 16, 20, 25, 30, 36 | exactly [A002620](https://oeis.org/A002620) — agrees on all eight |
| $k = n-3$ | $\mathrm{ex}(n, K_4^-)$, the **Frankl–Füredi** problem | 5, 10, 15, 22 | $\mathrm{ex}(6,\cdot)=10$ classical; 15 and 22 not found published |
| column limit | $\sup_n M_{\text{unif}}(n,k) = f(k,3)$ | $k{=}2$ plateaus at 6 | $f(2,3)=6$, Abbott–Hanson–Sauer 1972 — agrees |

The Mantel agreement across eight values, and $f(2,3) = 6$, are independent confirmations
of the checker against published theorems rather than against our own second implementation.

$M_{\text{unif}}(6,3) = 10$ also matches a published explicit witness: Kostochka's survey
Construction 2 lists the ten triples, and the same object is Frankl–Füredi's $H_6$, whose
iterated blow-up gives the $2/7$ lower bound for $\pi(K_4^-)$.

**The $k = n-3$ diagonal is the interesting one.** It is the $\pi(K_4^-) = 2/7$ conjecture,
where the best upper bound is $\approx 0.2871$ by flag algebras (Baber–Talbot). Whether
$\mathrm{ex}(7, K_4^-) = 15$ and $\mathrm{ex}(8, K_4^-) = 22$ are published could not be
determined, so **novelty there is unconfirmed, not established** — check the hypergraph
Turán small-case literature (Keevash's survey, de Caen, flag-algebra papers) before
claiming it.

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

**What this settles.** Every one of those roots exceeds the $1.551$ record by a wide margin, $M(7,3)^{1/7} = 1.6178$ most of all. If exact small
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

### Another group already uses this exact stack

[arXiv:2609.06175](https://arxiv.org/abs/2609.06175), *Sunflower-Free Uniform Families:
Recursive Constructions and Explicit Bounds* (Axante, Budala, Chitic, Dumitru, Nacu,
5 Sep 2026, **preprint, not peer-reviewed**), code at
[bogdan27182/sunflower-paper](https://github.com/bogdan27182/sunflower-paper): CaDiCaL plus
drat-trim UNSAT certificates plus Lean 4 / Mathlib formalization of witnesses. That is the
combination this repository treats as its differentiator.

Their quantity is $f(w,k)$, with **no ground-set parameter**, so the tables do not overlap
with ours: they report $39 \le f(3,4) \le 49$, $f(3,5) \le 146$, $153 \le f(3,6) \le 255$,
$259 \le f(3,7) \le 474$, $54 \le f(4,3) \le 83$, and prove that an intersecting 4-uniform
family with no 3-sunflower has at most 27 members. The screening pass for this repository
could not confirm this preprint existed; it does.

Also relevant, and older: **Abbott & Exoo**, *On set systems not containing delta systems*,
Graphs and Combinatorics 8 (1992) 1–9, [doi:10.1007/BF01271703](https://doi.org/10.1007/BF01271703)
— the classical computational paper on this problem, **paywalled and unread**. Its tables,
if it has any, are the largest remaining gap in this literature check.

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

The $k = n-2$ row of the full grid reproduces $\lfloor n^2/4 \rfloor$ exactly, which is Mantel's theorem — see §1b.

Complete exact rows for $n \le 8$ and the full $(n,k)$ grid to $n = 12$ are in the sweep's
JSON output; the peak $k$ tracks roughly $0.6n$.

**Best verified lower bound: $\mu_3 \ge 1.529360$**, from 70 sets at $n = 10$, $k = 6$.
That is **below** the record of 1.551, so it is not an improvement on anything published —
it is where this repository's search currently reaches. And see §1: that record is for
non-uniform families, so it is not yet known whether a uniform family can reach it at all.

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
