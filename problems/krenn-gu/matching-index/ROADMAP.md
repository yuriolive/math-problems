# Krenn–Gu roadmap

The target is not the conjecture. It is **$n = 8$, three colours, multi-edges and
bichromatic edges allowed**, the smallest unrestricted case nobody has decided, reduced by R1
and R2 in the [README](./README.md) to a single system of 6,558 cubic equations in 252
complex unknowns.

The $n = 6$ case was the target when this directory was opened. It was closed on 24 July
2026 by Alexis Gallagher's Lean certificate, by the two-layer method sketched below, while
this directory was being written. The closed-directions section records what that changes;
the short version is that the method survives, the instance moved up one size, and two
cheap certain deliverables now come first.

## Live directions, in the order to do them

### E. The Lean corollaries at $n = 6$ (cheap, certain, first)

Formal Conjectures at the revision Gallagher pins (`e751934`) still lists
`eqSystem6_no_solution_d4`, `eqSystem6_no_solution_d5`, `eqSystem6_no_solution_ge3` and the
$\mathbb{R}$, $\mathbb{Z}$ and $\{-1,0,1\}$ variants at $n = 6$ as `research open`. All of
them follow from `eqSystem6_no_solution_d3` in a few lines once two things are formalised
against the official `WeightsN`, `pmSumN`, `EqSystemN` definitions:

* **R2 as a lemma.** From `W : WeightsN N D α` with `EqSystemN N D W` and $D \ge 3$, build
  `W' : WeightsN N 3 α` by keeping the edges whose endpoint indices are both below 3 and
  zeroing the rest, and prove `EqSystemN N 3 W'`. The proof is the one-paragraph argument in
  the README: colourings inside $\{0,1,2\}$ see the same matching sum, colourings outside it
  see zero because some vertex has no surviving edge.
* **Coefficient restriction.** A real or integer solution is a complex one under the
  canonical embedding, so the $\mathbb{R}$, $\mathbb{Z}$ and $\{-1,0,1\}$ entries are
  immediate.

Deliverable: a Lean project here whose axiom audit passes
(`uv run python tools/lean/audit.py`), then a Formal Conjectures pull request marking those
entries solved with commit-pinned links. Trust note: the corollaries inherit Gallagher's
`Lean.ofReduceBool` and `Lean.trustCompiler`; the audit tool reports that separately, as it
should.

### F. Independent audit of the $n = 6$ certificate (started, not finished)

[`tools/audit_gallagher_certificate.sh`](./tools/audit_gallagher_certificate.sh) does it from
a clean machine: clone at `c04696e`, `elan` toolchain 4.27.0, `lake exe cache get`, then the
author's `scripts/verify_release.sh` (50 checksums, `lake build KrennGuCertificate`,
`#print axioms`). README §3 records how far the first run got. Also run `tools/lean/audit.py`
over the tree so the trusted-evaluator flag is recorded in this repository's own words. A
result trusted here is one whose axiom closure was printed here; until then the $n = 6$ row
in the README is trusted, not verified.

### A. Decide $n = 8$ exactly

Gallagher's $n = 6$ proof is the design document. Its shape:

1. **Support layer.** Boolean variables for which of the slots are non-zero and which
   matching monomials are supported; every colour class has a supported monochromatic
   matching; no non-monochromatic colouring has exactly one supported matching; plus three
   "universal" support theorems (star-anchor, pair-pencil dichotomy, full-column) proved
   once and imposed as clauses.
2. **Orbit split.** Choose one supported monochromatic matching per colour; the triple lies
   in one of finitely many orbits under vertex and colour symmetry (8 at $n = 6$ out of
   3,375). Each orbit is a branch with its nine target slots fixed.
3. **Exact no-goods.** For a candidate support, look for a coefficient-independent
   contradiction over the support torus: a target monomial equal to a forced-zero one, a
   binomial transported into a trinomial, a signed-Laurent exponent identity, or an exact
   $\mathbb{Q}$ ideal-membership certificate showing the product of the three target sums
   lies in the ideal of the zero equations. Record each as a local clause valid under every
   symmetry transport.
4. **SAT with certificates.** CaDiCaL refutes each branch; the LRAT trace is replayed by
   Lean's verified checker; Lean also proves each clause follows from `EqSystemN`.

Milestones, each a gate:

* **M0, Mantey at $n = 4$.** Rebuild the 54-unknown decision exactly (gauge fixing by the
  $(\mathbb{C}^*)^{12}$ torus, saturation by the three target sums). Seconds, or stop.
* **M1, Gallagher at $n = 6$ re-derived.** Reproduce the eight-orbit table and at least one
  branch refutation with this repository's own encoder, cross-checked against `ghzcheck` on
  every support the sieve rejects (rule 1). This is where the tool gets built; it is not new
  mathematics.
* **M2, the $n = 8$ orbit table and sizing.** Count orbits of target triples under
  $S_8 \times S_3$ ($105^3$ triples before quotienting), size one branch CNF, and measure
  whether the universal support theorems still prune. This number decides whether A
  continues.
* **M3, branch closure at $n = 8$**, then the assembly theorem, then the write-up. The
  3.000 EUR needs peer review, so the paper is the deliverable.

### G. The GF(2) parity route to the integer versions, for all $n$

For integer weights, $A(\iota) \bmod 2$ is the number of perfect matchings of the odd-weight
support, mod 2. So an integer-weight GHZ graph forces a coloured support in which every
constant colouring has an odd matching count and every other colouring an even one, and
over $\mathrm{GF}(2)$ a Hafnian is a Pfaffian whose square is a determinant: the $3^n$ induced
adjacency matrices must be nonsingular exactly for the constant colourings. Rank arguments
over $\mathrm{GF}(2)$ are the kind that generalise to all $n$, and a general-$n$ parity theorem
would settle the Formal Conjectures entries `eqSystem_no_solution_ge6_ge3_int` and
`_trinary_int` (not the complex conjecture, and not the prize).

Go/no-go is the $n = 6$ instance: a parity support there means parity alone cannot prove the
integer conjecture; none means the route is live. Encoders are in [`sat/`](./sat/):
`parity_cadical.py` (python-sat, plain CDCL with XOR chains) decides $n = 4$ instantly and
stalled for 16 minutes at $n = 6$; `parity_cryptominisat.py` (XOR-native, optional
`pycryptosat` dependency, symmetry-breaking fix of one colour-0 matching) is the one to use.
**Measured on 10 September 2026:** $n = 4$ satisfiable in 0.0 s with both encoders (the $K_4$
graph); $n = 6$: **undecided.** CryptoMiniSat ran from 04:13 UTC to 04:36 UTC without an answer and was stopped
for a credit reset. The go/no-go for this route is still open; the next run should add
colour-symmetry breaking (fix a second target matching up to the stabiliser of the first,
Gallagher's eight-orbit table) and Gaussian elimination on the XOR layer.

### H. The induction lemma hunt (started, not finished)

With the $n = 6$ base case in hand, the conjecture is equivalent to an inductive step, and
the missing step is exactly the case the MFCS 2024 reduction does not cover: a GHZ graph of
dimension 3 on $n \ge 8$ vertices with a 4-connected skeleton must yield one on $n - 2$
vertices. [`tools/lemma_hunt_workflow.js`](./tools/lemma_hunt_workflow.js) is a Claude Code
workflow that attacks this with six independent lenses (vertex-pair contraction through a
first derivative of the Hafnian, colour-specific cuts, the Hamming hierarchy of near-constant
colourings, GF(2) and Pfaffians, tensor flattenings, transversal Fourier transform), each
required to state a precise lemma and ship an exact-arithmetic test against `ghzcheck`, then
three skeptics per proposal and a judge. It was launched at 04:10 UTC on 10 September 2026
on a 4-core container (so two agents at a time) and stopped at 04:36 UTC for a credit reset. Two of the six proposers (contraction, colour cuts) had
started and were still reading the sources; none returned a proposal, no skeptic ran, and no
files were written. There are no results from this run.

Nothing from the hunt is in the live directions above until it has survived the skeptic
pass; the record of what was proposed is here so the next run does not start from zero.

### B. Counterexample hunt in the cyclotomic regime, now at $n = 8$

Same instrument as before: weights in $\mathbb{Z}[\zeta_k]$, exact arithmetic, certified
hits only. Gallagher's no-good taxonomy says where cancellation can and cannot live, so seed
the search with supports his universal theorems allow. Prior: lower than before, since the
$n = 6$ answer went the way the conjecture says. Cost: still low.

### C. The Hafnian reformulation: read, do not race

Unchanged. With $A_{uv} = x_u^{\mathsf{T}} W_{uv} x_v$ the GHZ conditions say
$\operatorname{Haf}(A(x)) = \sum_i \prod_v x_{v,i}$ with each $W_{uv}$ shared across every
matching through $uv$; tensor-rank obstruction technology is the route to the full
conjecture. Krenn, Firsching, Tsoukalas, Gajjala, Gu and Chaudhuri have *A Tensor-Algebraic
No-Go Theorem for High-Dimensional Photonic GHZ States* in preparation
([arXiv:2605.22763](https://arxiv.org/abs/2605.22763), §4 and reference 38). Read it when it
appears; do not race it.

## Closed directions

* **Deciding $n = 6$.** Closed by Gallagher (24 July 2026): `eqSystem6_no_solution_d3`,
  Lean 4.27.0, axiom closure `propext, Classical.choice, Lean.ofReduceBool,
  Lean.trustCompiler, Quot.sound`, no `sorry`. Trusted here to the extent direction F
  confirms. Not peer-reviewed, not yet merged into Formal Conjectures (PR #4610 open since
  24 July, labels `paper` and `solution found`, one maintainer question about prior work
  unanswered), not on Krenn's page. What this repository loses is a first result; what it
  keeps is the whole toolchain plan, because his proof is the method this roadmap proposed,
  executed. The lesson for `CANDIDATES.md`: the two-day window between "identify the gap"
  and "someone closes it" is real when the gap is a single finite instance and the
  instruments are commodity.
* **Positive real weights.** Closed by Bogdanov (2017). Demonstrated concretely by
  `instances/k6-d3-factorisation.json`.
* **Enumerating skeletons.** Collapsed by R1: one system per $n$.
* **Raising the upper bound on $d$.** By R2 a bound $\mu \le f(n)$ decides the conjecture
  only where $f(n) < 3$; every published bound is $\ge 3$ for every $n > 4$.
* **Vertex connectivity $\le 2$, maximum degree $\le 3$.** Settled unrestricted by
  [arXiv:2407.00303](https://arxiv.org/abs/2407.00303).
* **Gradient descent on complex weights (PyTheus-style).** Closed for this repository: a
  float is not a certificate, and Gallagher's result shows what the alternative looks like.

## Prize logistics

The 3.000 EUR from Mario Krenn and Dominik Leitner requires the proof or counterexample to
appear in a respected peer-reviewed journal, and it is for the conjecture, not for a slice
of it; the $n = 6$ certificate does not claim it and could not. The 1.000 EUR best-paper
award is for work on inherited vertex colourings; its listed nomination deadline (end of
August 2024) is stale, so confirm the current cycle before planning around it, and expect
the $n = 6$ certificate to be a strong nominee. Contact and terms are on
[the problem page](https://mariokrenn.wordpress.com/graph-theory-question/).

## Rules

The repository's working rules apply. The three that bite first here:

* Ground truth is a separate program from the search: SAT and algebra results are re-checked
  by `ghzcheck` before they are written down.
* "Absent" must never mean "not evaluated": a colouring with no matchings has weight exactly
  zero because the enumeration covered it, and the checker says which.
* Say which components are trusted and which are verified: the checker is verified code over
  exact arithmetic; a Lean theorem that rests on `native_decide` trusts the Lean compiler,
  and the audit tool says so in those words.
