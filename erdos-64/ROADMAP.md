# Where this project can actually contribute to Erdős #64

Written 2026-09-08. Every claim here is either cited or measured by the tooling in this
repository. The point of the document is to be honest about which directions are live and
which are closed, so that compute and attention go somewhere useful.

## The state of the problem

The conjecture: every finite graph with minimum degree at least 3 contains a cycle whose
length is a power of two. Open, $1000 bounty, [erdosproblems.com/64](https://www.erdosproblems.com/64).

What is settled, and what it forecloses:

| Result | Consequence for a search |
| :--- | :--- |
| Liu–Montgomery [LiMo20]: true once the minimum degree exceeds an absolute constant | Only very small minimum degree can host a counterexample. Degree 3 is the target |
| $f(3) = 24$ exactly (Markström); Garcia [arXiv:2609.04686](https://arxiv.org/abs/2609.04686): min degree 3 needs $\ge 24$ vertices to avoid $C_4$ and $C_8$ | Nothing below 24 vertices is worth touching |
| $f(4) \ge 54$ (unpublished Markström computation, cited by Garcia) | **No cubic counterexample below 54 vertices.** Any counterexample on $n \ge 16$ is $\{C_4,C_8,C_{16}\}$-free |
| $f(4) \le 78$ (Exoo), and 78 is optimal among gadget designs on bases of $\le 12$ vertices (Garcia) | The $[54, 78]$ window is open but the obvious construction route is exhausted |
| $f(5) \le 450$ (Garcia, repairing an error in Exoo's construction) | Avoiding $\{C_4 \dots C_{32}\}$ is possible, at 450 vertices |
| Cubic bipartite needs $\ge 60$ (Tranquilli, [arXiv:2608.02675](https://arxiv.org/abs/2608.02675)); unpublished sweeps report $\ge 64$ | The bipartite class is a dead end and is nearly exhausted anyway |
| Confirmed families: 3-connected cubic planar, diameter 2, $P_8$-free, $P_{10}$-free, claw-free cubic below 114, several Cayley families | Constructions inside these cannot work |

Here $f(k)$ is the order of the smallest cubic graph with no cycle of length $2^m$ for any
$m \le k$.

## What this repository can do, ranked by value per unit effort

### 1. The strict two-thirds bound in Lean — **complete**

`formalization-egc/` proves, with no `sorry` and no hypotheses beyond `MinCexHyps`
(the Carr/Bisch facts about a minimal counterexample):

$$|V_3| \ge 2|V_{\ge 4}| + 1, \qquad	ext{hence}\qquad 3|V_3| > 2|V|.$$

Published state for comparison: Carr's $4/7$
([arXiv:2605.22844](https://arxiv.org/abs/2605.22844)) is the literature bound; Bisch's
$\ge 2/3$ is on Zenodo with a Lean formalization but unpublished; the strict $> 2/3$
existed only as a forum comment by [`jul059`](https://www.erdosproblems.com/forum/thread/64#post-8130) (26 July 2026), explicitly marked
unverified. **The argument is theirs**; this repository contributes the machine-checked
proof of it.

`EGCStrict.lean` — the counting and the equality analysis:

* `MinCexHyps.card_cubic_ge` — the double count $4|V_4| \le e(V_4,V_3) \le 2|V_3|$.
* `degree_eq_four_of_equality`, `card_big_nbrs_eq_two_of_equality` — under equality every
  $V_4$ vertex has degree exactly 4 and every cubic vertex exactly two $V_4$ neighbours.
* `contract`, `contract_degree_ge` — contracting $V_3$ yields a 4-regular graph on $V_4$.
  This is the step that consumes the absence of 4-cycles: two cubic neighbours of `u`
  leading to the same $V_4$ vertex would close `u–x–w–y–u`.
* `card_big_lt` — the contraction has strictly fewer vertices.

`EGCLift.lean` — the cycle lifting, which is what closes the argument:

* `mid` — the cubic vertex realizing a contraction edge, with `adj_mid_left/right`.
* `mid_determines_pair` — a cubic vertex determines the contraction edge it came from,
  because in the equality case it has exactly two $V_4$ neighbours. This is what makes the
  inserted vertices pairwise distinct along a trail.
* `lift`, `length_lift` — replace each contraction edge by its two-edge path; length
  doubles.
* `nodup_support_lift`, `exists_pow2_cycle_of_contract_cycle` — the lifted walk is a
  cycle, so a $2^k$ cycle upstairs becomes a $2^{k+1}$ cycle in $G$.
* `card_cubic_ge_succ`, `strict_two_thirds`, `strict_two_thirds_rat` — the bound.

Every theorem audits to `propext`, `Classical.choice`, `Quot.sound` only
(`AxiomCheck.lean`). Bisch's file is not vendored — his repository carries no license —
so the facts it proves are taken as the `MinCexHyps` bundle, with each field annotated
with the lemma of his that supplies it. The two developments compose.

**What would finish this as a contribution:** discharge `MinCexHyps` from Bisch's Lean
file (or reprove those four facts here) to get an unconditional theorem about minimal
counterexamples, then write it up. The mathematical content is done.

### 2. Close $f(4) \in [54, 78]$ — the live computational gap

Any cubic graph on 54–77 vertices with no $C_4$, $C_8$ or $C_{16}$ improves Exoo's upper
bound. This target **allows 32-cycles**, so it is strictly easier than refuting the
conjecture and must never be reported as a counterexample.

Run it with `tools/f4_sweep.py` (the kernel takes `--max-length 16`); record results with
`tools/f4_report.py`, which refreshes the table in `README.md`.
Best verified counts are in README section 5.

Two things limit it today:

* **Reach.** `verifier/` is a 64-vertex bitmask engine (`[u64; 64]`), so only $54 \le n \le 64$
  of the window is testable. Widening to 128 vertices opens the rest and would also let
  Exoo's 78-vertex graph be re-verified independently — worth doing on its own, since
  Garcia has just found a real error (spurious 8- and 32-cycles) in the sibling $f(5)$
  construction.
* **Method.** Local search buys a factor of roughly 35 below the random-cubic baseline
  (about 1300 sixteen-cycles at $n = 60$, measured over 25 samples, against
  $2^{16}/32 = 2048$ in theory for fixed length and large $n$); the best reached is
  $C_{16} = 37$ at $n = 58$, and then it stalls. The record at 78 was set by an algebraic construction, not by annealing.
  A gadget-substitution search over small base graphs — the family Garcia analyses — is the
  method with a track record here, and it is not implemented in this repository.

### 3. Independently reproduce an exhaustive bound

`sallerk` reports a cubic bipartite sweep to $n \le 62$ and states that the correctness of
their generator is *"the weakest point in the claim"*. An independent reimplementation
that confirms or refutes it is a real service and directly invited. Lower value now that
Tranquilli's $\ge 60$ is published, but cheap.

The general cubic exhaustive frontier is more interesting: the same author reports only
$n \le 34$, and $f(4) \ge 54$ already implies more than that, so the useful version of this
task is an independent, certificate-producing confirmation of $f(4) \ge 54$ itself — which
is currently an *unpublished* computation that everything else leans on.

### 4. Red-team the outstanding proof claim

The 250-page Hypostructure claim is incomplete by its author's own status log, and the
author has explicitly asked for help finding errors. Reviewer `mesa` found one real defect
in Lemma 7.37(a) and the author conceded it. This needs mathematical reading, not compute.

## What is closed, and why

* **Counterexample hunting below 54 vertices.** Provably empty by $f(4) \ge 54$. Every
  campaign in this repository before 2026-09-08 was searching such a region.
* **Counterexample hunting by annealing at any reachable $n$.** To refute the conjecture at
  $n \in [54, 63]$ a graph must avoid $\{4, 8, 16, 32\}$; $f(5) \le 450$ is the smallest
  known order where even that much is achievable, and no lower bound for $f(5)$ is
  published. Nothing in the 64-vertex window is a plausible counterexample.
* **The bipartite class.** Nearly exhausted and known hostile.
* **Any family in the confirmed-cases table.**

## Rules this repository follows

Learned the hard way; see `.agents/skills/neuro-symbolic-math/SKILL.md` for the general
form.

1. Every published number comes from `verifier_64`, never from the search kernel. The
   kernel's counts are capped and exist only to drive the search.
2. "Absent" is never allowed to mean "not evaluated". The verifier tests every
   power-of-two length $\le n$ unconditionally, and a capped count prints as `N+`.
3. The two objectives are distinct and separately flagged: `--max-length 32` is the
   counterexample target, `--max-length 16` is $f(4)$. A hit on the latter is not a
   solution to the former.
4. Throughput is counted in moves whose energy was actually evaluated.
5. Lean states checkable propositions. Unproved obligations appear as named hypotheses,
   never as `sorry`, and the trusted-versus-verified boundary is written down: Lean checks
   structure and short cycles, the Rust verifier checks the long ones.
