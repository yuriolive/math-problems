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

### 1. Finish the strict two-thirds bound in Lean — *closest to a real contribution*

`formalization-egc/` contains a `sorry`-free, kernel-checked development of the equality
analysis behind the strict bound $|V_3| > \tfrac{2}{3}|V|$ for a minimal counterexample.
Published state: Carr's $4/7$ ([arXiv:2605.22844](https://arxiv.org/abs/2605.22844)) is the
literature bound; Bisch's $\ge 2/3$ is on Zenodo with a Lean formalization but unpublished;
the strict $> 2/3$ exists only as an unverified forum comment by `jul059` (26 July 2026).

Proved here, depending only on `propext`, `Classical.choice`, `Quot.sound`:

* `card_cubic_ge` — the double count $4|V_4| \le e(V_4,V_3) \le 2|V_3|$, so $|V_3| \ge 2|V_4|$.
* `degree_eq_four_of_equality`, `card_big_nbrs_eq_two_of_equality` — in the equality case
  every $V_4$ vertex has degree exactly 4 and every cubic vertex has exactly two $V_4$
  neighbours.
* `contract`, `contract_degree_ge` — the contraction of $V_3$ is a 4-regular graph on
  $V_4$. The degree argument is where the absence of 4-cycles is used: two cubic
  neighbours of `u` leading to the same $V_4$ vertex would close `u–x–w–y–u`.
* `card_cubic_ge_succ`, `strict_two_thirds`, `strict_two_thirds_rat` — the strict bound.

**The one remaining obligation** is the hypothesis `LiftsCycles`: a power-of-two cycle in
the contraction lifts to a cycle of twice the length in `G`, by re-inserting the cubic
vertex between consecutive $V_4$ vertices. Mathematically routine — the inserted vertices
are distinct because a cubic vertex determines the unordered pair of its two $V_4$
neighbours, and distinct edges of a cycle are distinct pairs — but it is a genuine piece of
`Mathlib` `Walk`/`IsCycle` engineering. It is stated as an explicit hypothesis, never a
`sorry`, so nothing in the file overstates what is proved.

Effort: hours, not days. Discharging `LiftsCycles` completes a formalization of a result
that currently exists only as an unverified forum sketch. That is a publishable object.

### 2. Close $f(4) \in [54, 78]$ — the live computational gap

Any cubic graph on 54–77 vertices with no $C_4$, $C_8$ or $C_{16}$ improves Exoo's upper
bound. This target **allows 32-cycles**, so it is strictly easier than refuting the
conjecture and must never be reported as a counterexample.

Run it with `tools/f4_sweep.py` (the kernel takes `--max-length 16` for this objective).
Best verified counts so far are in README section 5; the search gets $C_{16}$ into the
tens but not to zero.

Two things limit it today:

* **Reach.** `verifier/` is a 64-vertex bitmask engine (`[u64; 64]`), so only $54 \le n \le 64$
  of the window is testable. Widening to 128 vertices opens the rest and would also let
  Exoo's 78-vertex graph be re-verified independently — worth doing on its own, since
  Garcia has just found a real error (spurious 8- and 32-cycles) in the sibling $f(5)$
  construction.
* **Method.** Local search buys a factor of roughly 20 below the random-cubic baseline
  (about 1300 sixteen-cycles at $n = 60$, measured, against $2^{16}/32 = 2048$ in theory)
  and then stalls. The record at 78 was set by an algebraic construction, not by annealing.
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
