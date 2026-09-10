# Krenn–Gu conjecture: the matching index of GHZ graphs

> **Statement.** Let $G$ be a multi-graph in which every edge carries a colour at each of
> its two *half-edges* (so an edge is monochromatic when both halves agree, and bichromatic
> otherwise) and a weight $w(e) \in \mathbb{C}$. A vertex colouring $vc$ *filters* $G$ to the
> subgraph of edges whose half-edge colours match the colours of their endpoints; the
> **weight of $vc$** is the sum, over the perfect matchings of that filtered subgraph, of the
> product of the edge weights. The graph is a **GHZ graph** when every feasible
> monochromatic vertex colouring has weight $1$ and every non-monochromatic vertex colouring
> has weight $0$, and its **dimension** is the number of feasible monochromatic colourings.
> The **matching index** $\mu(G)$ of a simple graph $G$ is the largest dimension attainable
> by any colouring and weighting of any multi-graph with skeleton $G$. Krenn and Gu conjecture
> that $|V(G)| > 4$ implies $\mu(G) \le 2$. Physically, $\mu(G) \ge d$ with $n$ vertices is a
> linear-optics experiment producing an $n$-photon GHZ state of local dimension $d$.

> **Status.** Open, and actively contested. $\mu(K_4) = 3$ is the only known instance of
> matching index $3$. In the unrestricted setting (multi-edges and bichromatic edges
> allowed, weights complex) the settled cases are $n = 4$ (Mantey 2023, Gröbner basis) and,
> since 24 July 2026, $n = 6$: a Lean 4 certificate by Alexis Gallagher proves
> `¬ ∃ W : WeightsN 6 3 ℂ, EqSystemN 6 3 W` against the Formal Conjectures definitions
> ([repository](https://github.com/algal/krenn-gu-6x3-certificate), pinned commit `c04696e`,
> [explainer](https://krenngufun.org/)). That result is machine-checked but not
> peer-reviewed, its axiom closure includes `Lean.ofReduceBool` and `Lean.trustCompiler`
> from `native_decide`, its status pull request to Formal Conjectures
> ([#4610](https://github.com/google-deepmind/formal-conjectures/pull/4610)) is still open,
> and Krenn's page does not list it. The first undecided unrestricted case is therefore
> $n = 8$. Mario Krenn and Dominik Leitner offer **3.000 EUR** for the first proof or
> counterexample published in a peer-reviewed journal, and a **1.000 EUR** best-paper award
> for work on inherited vertex colourings
> ([Krenn's problem page](https://mariokrenn.wordpress.com/graph-theory-question/)).

## 0. Intake

Answered before any search code was written. Rule 6 and Rule 12 both apply: read the
literature and check the instrument's reach before spending compute.

### 1. Can a compiled ground-truth checker be written in about a day?

> It defines what a solution *is*. Without it a search produces numbers nobody
> should trust, and every published figure here that turned out to be false came
> from trusting a search kernel's own counters.

**Answer.** Yes, and [`verifier/`](./verifier/) is it. The checker enumerates every perfect
matching of a coloured multi-graph once, buckets the matchings by the vertex colouring each
induces, and sums weights in exact arithmetic over $\mathbb{Q}(\zeta_m)$, so no floating point
anywhere, so a cancellation is decided rather than estimated. It reproduces the published
$\mu(K_4) = 3$ configuration (`instances/k4-d3.json`), and it is differential-tested against
an independently written reference that walks the $d^n$ colourings and evaluates a Hafnian
per colouring, on the instance corpus and on 51 random coloured multi-graphs
(1,437 matchings, 1,261 feasible colourings compared exactly).

The limit of the instrument is stated honestly in §3: it verifies **one weighting**. The
question the conjecture asks is over *all* weightings, and that is an algebraic decision
problem the checker does not answer. It answers the part that is a matching count.

### 2. Does the objective have a gradient, i.e. does a small perturbation move the score?

> Circle packing rewards the twelfth decimal place, so evolutionary search climbs.
> A lexicographic integer profile barely moves under an edge swap, so it does not.
> This single property predicts whether search or proof is the right instrument.

**Answer.** Split, and the split *is* the plan.

* **The support layer has a gradient.** Fix which colour slots are present, ignore weights,
  and count the non-monochromatic colourings carrying exactly one perfect matching. Each
  such colouring is fatal for every weighting of that support, since one non-zero product cannot
  cancel against nothing, so the count is a real objective, and flipping a single slot moves
  it. `support.unique_pm_nonmono` in the checker's report is that number.
* **The weight layer has an analytic gradient.** Minimising $\sum_{vc} |w(vc)|^2$ over complex
  weights is exactly what PyTheus does, **and that is the reason not to climb it.** The
  people who own the problem have run that landscape at scale for years, and a
  floating-point minimum at $10^{-9}$ is not distinguishable from an exact solution. Every
  weight question here is settled by exact algebra instead: rational and cyclotomic
  arithmetic in the checker, and the lattice/Gröbner layer described in the roadmap.

Rule 13 says a flat objective is a proof target. Half of this one is flat, so half of the
work is a proof, and the deliverable at $n = 6$ is a decision procedure rather than a hill
climb.

### 3. Is there a published open gap strictly easier than the headline conjecture?

> There usually is, and it is usually far more tractable. Keep it one flag away
> from the main objective, and never conflate a hit on it with the harder claim.

**Answer.** Yes, at two sizes, and the smaller one moved while this directory was being
written. Table 2 of [arXiv:2304.06407](https://arxiv.org/abs/2304.06407) lists the published
state of the art by regime; the row with both multi-edges and bichromatic edges allowed
stops at $n = 4$. The $n = 6$ and $n = 8$ SAT results assume no bichromatic edges, and the
$n/\sqrt{2}$ bound assumes a simple skeleton. On that basis the sharp gap was *decide $n = 6$
unrestricted*, and the first version of this README targeted it.

Gallagher's July 2026 certificate (see Status) closes exactly that gap, by exactly the
two-layer method this roadmap had proposed: a support sieve, exact Laurent and
ideal-membership obstructions, eight symmetry orbits of target-matching triples, and
CaDiCaL refutations replayed through Lean's verified LRAT checker. Its statement is the
Formal Conjectures entry `eqSystem6_no_solution_d3`, which is the $d = 3$ case, and by R2
below it settles every $d \ge 3$ at $n = 6$. So the published-open gaps are now:

* **Decide $n = 8$, $d = 3$ unrestricted**: Formal Conjectures entry
  `eqSystem8_no_solution_d3`, listed `research open` at the revision Gallagher pins
  (`e751934`). Nothing published or certified touches it.
* **The corollaries Formal Conjectures still lists as open.** At that revision
  `eqSystem6_no_solution_d4`, `_d5`, `_ge3`, and the $\mathbb{R}$, $\mathbb{Z}$ and
  $\{-1,0,1\}$ variants at $n = 6$ are all `research open`. Each follows from Gallagher's
  theorem in a few lines once R2 (colour restriction) is formalised against the same
  definitions, and a real or integer solution is a complex one. Small, concrete, and exactly
  the shape of contribution the Lean lane here is built for.
* **An independent audit of the $n = 6$ certificate.** The repository's own rule: a result
  is trusted here once its axiom closure has been reproduced by this repository's tooling,
  not because a website says so. See §3.

Two elementary reductions turn that gap into a single finite question, and both are recorded
here because they shape every line of code that follows.

* **(R1) One instance per $n$.** A zero weight is an absent edge, and by the reduction in
  §1.1 of [arXiv:2407.00303](https://arxiv.org/abs/2407.00303) at most one edge is needed per
  (vertex pair, ordered colour pair). So every $n$-vertex candidate is a sub-support of the
  fully loaded $K_n$, and the question "is there an $n$-vertex counterexample" is one system
  of polynomial equations in $\binom{n}{2} d^2$ complex unknowns.
* **(R2) Three colours suffice.** If $G_c^w$ is GHZ with dimension $\ge 3$, delete every edge
  having a half-edge coloured outside $\{1,2,3\}$. The filtered subgraph of any colouring
  with values in $\{1,2,3\}$ is untouched, so those weights are unchanged; a colouring using
  a deleted colour now filters to nothing at that vertex and has weight $0$. The result is a
  GHZ graph of dimension exactly $3$ on the same skeleton. So the conjecture is equivalent to
  the single statement *no GHZ graph has $n \ge 6$ vertices and $3$ colours*, presumably
  folklore, and one line to check.

R2 is the reason this problem directory targets $d = 3$ and nothing else, and the reason
one $n = 6$ certificate settles every dimension at $n = 6$. An upper bound of
the form $\mu \le f(n)$ settles the conjecture only where $f(n) < 3$, and every published
bound is $\ge 3$ for every $n > 4$. The results that actually bite are the ones that exclude
dimension 3 outright in a class: vertex connectivity $\le 2$, maximum degree $\le 3$,
$n = 4$, and the SAT results with bichromatic edges banned.

### 4. Is the reachable instance size inside the checker's hard limit?

> State the limit as a number and the target range as a number, in the same units,
> and compare them here.

**Answer.** For the matching enumeration, yes, with room. For the algebra, the target is at
the edge and that is the real risk on this problem.

| | $n = 4$ | $n = 6$ | $n = 8$ | $n = 10$ |
| :--- | ---: | ---: | ---: | ---: |
| colour slots at $d = 3$ (unknowns) | 54 | **135** | 252 | 405 |
| vertex colourings (equations) | 81 | **729** | 6,561 | 59,049 |
| matchings, fully loaded | 243 | **10,935** | 688,905 | 55,801,305 |
| checker wall time, fully loaded | 0.00 s | **0.01 s** | 0.31 s | 25.9 s |

Hard limits: $n \le 16$ (bitmask), $d \le 16$, weights in $\mathbb{Q}(\zeta_m)$ for
$m \le 64$, matchings capped at $2 \times 10^7$ by default and reported as `unknown` rather
than truncated when the cap is hit. The target $n = 8$ is comfortably inside. The
measurement command is in §3.

The comparison that matters is the algebraic one, and Gallagher's $n = 6$ certificate is
the first real data point on its scale. Deciding $n = 6$ took **726 cubic equations in 135
unknowns**, reduced by $S_6 \times S_3$ to 8 orbits of target-matching triples (out of
$15^3 = 3{,}375$), each a CNF of about 12,330 variables and 59,000 to 69,000 clauses, refuted
by CaDiCaL and replayed in Lean in 22 minutes on 8 cores. At $n = 8$ the same objects are
**6,558 equations in 252 unknowns**, $105^3 = 1{,}157{,}625$ target triples before
quotienting by $S_8 \times S_3$, and $6{,}561 \times 105 = 688{,}905$ matching variables per
branch before any symmetry. That is two to three orders of magnitude on every axis, and
whether the support-sieve plus Laurent-obstruction method still closes every branch there
is precisely the open engineering question. The gate is unchanged: a decision procedure that
reproduces Mantey's $n = 4$ answer in seconds, then Gallagher's $n = 6$ orbit table, before
any $n = 8$ compute is spent.

**Verdict.** Pursue, with two risks named. The checker exists and reproduces the one
published extremal graph; the reach of the enumeration is measured; the target is a specific
Formal Conjectures entry nobody has closed. The first risk is the algebra at $n = 8$, exposed
early by the gate above. The second is the field: an individual with a solver stack closed
$n = 6$ in the two days this directory was being planned, and the DeepMind and Krenn group
has a general no-go theorem in preparation. The cheap, certain deliverables (the Lean
corollaries and the independent audit) go first for that reason. See
[`ROADMAP.md`](./ROADMAP.md).

## 1. Known results

Everything below is in the graph-theoretic language of the statement. "Unrestricted" means
multi-edges and bichromatic edges allowed with arbitrary complex weights.

| Regime | Result | Source |
| :--- | :--- | :--- |
| Positive real weights (no destructive interference) | Three monochromatic matchings of distinct colours with $n > 4$ force a non-monochromatic matching, so $\mu \le 2$ | Bogdanov, MathOverflow, 2017; stated as Theorem 7 of [arXiv:2407.00303](https://arxiv.org/abs/2407.00303) |
| Unrestricted, $n = 4$ | $\mu(K_4) = 3$, attained by exactly one configuration up to isomorphism | Mantey, *Krenn-Gu conjecture is true for graphs with four vertices*, by Gröbner basis; cited as [18] in [arXiv:2407.00303](https://arxiv.org/abs/2407.00303) |
| No bichromatic edges, $n = 6$ | maximum dimension $2$ | Cervera-Lierta, Krenn, Aspuru-Guzik, [arXiv:2109.13273](https://arxiv.org/abs/2109.13273), by SAT |
| No bichromatic edges, $n = 8$ | maximum dimension $\le 3$ | same |
| Simple skeleton, bichromatic allowed | $\mu(G) < \frac{n}{\sqrt{2}}$ for $n > 4$ | Chandran, Gajjala, *Graph-theoretic insights on the constructability of complex entangled states*, [Quantum 8, 1396 (2024)](https://quantum-journal.org/papers/q-2024-07-03-1396/), [arXiv:2304.06407](https://arxiv.org/abs/2304.06407) |
| Unrestricted, $\kappa(G) \le 2$ | $\mu(G) \le 2$ | Chandran, Gajjala, Illickan, [LIPIcs.MFCS.2024.41](https://doi.org/10.4230/LIPIcs.MFCS.2024.41), [arXiv:2407.00303](https://arxiv.org/abs/2407.00303), Theorem 9 |
| Unrestricted, maximum degree $\le 3$ | conjecture true | same, Theorem 11 |
| Unrestricted, minimum degree $3$ | $\mu(G) \le 3$ | same, Theorem 12 |
| Unrestricted, minimal counterexample | must be $4$-connected | same, Theorem 10 |
| Unrestricted, $d \ge n$ ($n$ even) | no GHZ graph exists | AlphaProof Nexus with Krenn, §4 of [arXiv:2605.22763](https://arxiv.org/abs/2605.22763); Krenn, Firsching, Tsoukalas, Gajjala, Gu, Chaudhuri, *A Tensor-Algebraic No-Go Theorem for High-Dimensional Photonic GHZ States*, in preparation |
| Unrestricted, $n = 6$, $d = 3$ (hence every $d \ge 3$ by R2) | no GHZ graph exists | Gallagher, *Krenn-Gu 6×3 certificate*, Lean 4.27.0, [pinned commit c04696e](https://github.com/algal/krenn-gu-6x3-certificate/tree/c04696e515e0c02be140353fb52ea60c62e827b1), 24 July 2026. Machine-checked; axiom closure `propext, Classical.choice, Lean.ofReduceBool, Lean.trustCompiler, Quot.sound`; not peer-reviewed; [Formal Conjectures PR #4610](https://github.com/google-deepmind/formal-conjectures/pull/4610) open |
| Prize | 3.000 EUR for a proof or a counterexample in a peer-reviewed journal; 1.000 EUR best-paper award | [Krenn's problem page](https://mariokrenn.wordpress.com/graph-theory-question/) |

The dates on Krenn's page are the authoritative record of what is claimed when: the
$d \ge n$ entry is dated May 2026 and the Lean formalisation of the conjecture July 2026.
Gallagher's $n = 6$ certificate is not on that page as of 10 September 2026. The Formal
Conjectures file at the revision it pins states the benchmark family precisely: `EqSystemN N
D W` is `∀ ι, pmSumN N D W ι = if allEqual ι then 1 else 0` over `W : EdgeN N D → ℂ`, so zero
weights and every sub-support are covered, and the entries open there are `eqSystem6_*` for
$d \in \{3,4,5\}$ and $d \ge 3$, `eqSystem8_no_solution_d3`, `eqSystem10_*` for $d = 3..9$,
$n = 12, 14, 16$ at $d = 3$, the general `eqSystem_no_solution_ge6_ge3`, and the
$\mathbb{R}$, $\mathbb{Z}$ and $\{-1,0,1\}$ variants.

**What the open region actually is.** Combining R2 with the table: a counterexample has
$n \ge 8$ even (granting Gallagher's certificate), exactly 3 colours, a $4$-connected
skeleton, a vertex of degree $\ge 4$, at least one bichromatic edge, and at least one
non-monochromatic colouring whose matchings cancel. By R1 the whole $n = 8$ case is one
system: 252 unknowns, 6,561 equations.

## 2. What would count as progress

In descending order of value, and each one is a separate flag:

1. **A counterexample.** A coloured, weighted multi-graph on $n > 4$ vertices whose checker
   report has `"counterexample": true`. Exact weights, exit code 0. Worth 3.000 EUR and a new
   quantum interference effect.
2. **Deciding $n = 8$ unrestricted** (`eqSystem8_no_solution_d3`). Either a counterexample
   as above, or a machine-checked proof that the 6,558 cubic equations in 252 unknowns have
   no solution with the three monochromatic weights non-zero.
3. **The Lean corollaries at $n = 6$.** Formalise R2 against the Formal Conjectures
   definitions and derive `eqSystem6_no_solution_d4`, `_d5`, `_ge3` and the real, integer
   and $\{-1,0,1\}$ variants from Gallagher's theorem. Small, certain, and citable.
4. **An independent reproduction of Gallagher's axiom closure** with this repository's
   tooling, recorded in §3, so that the $n = 6$ row above is verified here rather than
   trusted.
5. **A reusable exact decision procedure** that reproduces Mantey's $n = 4$ result and
   Gallagher's eight-orbit $n = 6$ table in seconds. Nothing published does this as a tool.

Not progress: a numerical near-miss, an upper bound of the form $\mu \le f(n)$ with
$f(n) \ge 3$ (implied by the conjecture, see R2), or a search that establishes only that
PyTheus-style optimisation failed again.

## 3. Measured state

Every number here comes from the compiled checker. Reproduce with:

```bash
cd problems/krenn-gu/matching-index/verifier && cargo build --release && cargo test --release
cd .. && ./verifier/target/release/ghzcheck instances/k4-d3.json
uv run python tools/full_support.py 6 3 > /tmp/k6-d3.json
./verifier/target/release/ghzcheck /tmp/k6-d3.json --max-matchings 100000000
uv run python -m unittest discover -s tests
```

| Instance | matchings | feasible colourings | dimension | note |
| :--- | ---: | ---: | ---: | :--- |
| `k4-d3` | 3 | 3 | **3** | reproduces the published extremal graph, the gate |
| `c6-d2` | 2 | 2 | 2 | the standard 6-photon dimension-2 experiment |
| `k4-d2-interference` | 4 | 3 | 2 | one colouring cancels, $1 \cdot (-1) + 1 \cdot 1 = 0$ |
| `cyc3-cancellation` | 3 | 1 | 0 | $1 + z + z^2 = 0$ decided exactly in $\mathbb{Q}(\zeta_3)$ |
| `cyc3-no-cancellation` | 3 | 1 | 0 | one violation, exact weight $1 + 2z$ |
| `k6-d3-factorisation` | 4 | 4 | 0 | three 1-factors of $K_6$: one non-monochromatic colouring with a single matching, so no weighting of this support can work: Bogdanov's lemma, made concrete |
| $K_6$, all 135 slots | 10,935 | 729 | 0 | all-ones weights; 726 non-monochromatic colourings each carry $\ge 2$ matchings, so no support-level obstruction, so the algebra has to decide it |

| $K_8$, all 252 slots | 688,905 | 6,561 | 0 | all-ones weights, 0.31 s; the enumeration side of the $n = 8$ target |

**Independent audit of the $n = 6$ certificate.** Cloned
[`algal/krenn-gu-6x3-certificate`](https://github.com/algal/krenn-gu-6x3-certificate) at
`c04696e` into a clean container (4 cores, 15 GB), installed Lean 4.27.0 through `elan`, and
ran the author's `scripts/verify_release.sh`, which checks 50 artifact SHA-256 sums, builds
the certificate, and prints the axiom closure of `eqSystem6_no_solution_d3`. A source scan
of the pinned tree finds no `sorry` or `admit` token in any `.lean` file and `native_decide`
in 10 files. **Not finished in the session that started it.** The Mathlib cache fetch completed at
03:23 UTC; `lake build KrennGuCertificate` then ran on the 4-core box and had produced
186 compiled objects by 04:17 UTC, when the session had to stop for a credit reset.
No axiom closure was printed here, so the $n = 6$ row above is **trusted, not verified**.
Reproduce with `tools/audit_gallagher_certificate.sh` on a machine with 8 or more cores; the
author reports 22 minutes there.

Status of the search itself: **not started.** No claim is made here about $\mu(K_8)$, and the
claim about $\mu(K_6)$ is Gallagher's, trusted to exactly the extent the audit above says.

## 4. Layout

```
problems/krenn-gu/matching-index/
├── README.md               this file
├── ROADMAP.md              what is worth trying, what is closed, and why
├── verifier/               exact ground-truth checker (Rust, no floating point)
├── instances/              the corpus, including the published K4 extremal graph
├── sat/                    GF(2) parity relaxation encoders (direction G in the roadmap)
├── tools/                  full_support.py; the certificate audit script; the lemma-hunt workflow
└── tests/                  differential tests against an independent reference
```

`sat/` and `algebra/` arrive with the first milestone in the roadmap; `formalization/` only
if something turns out to be provable.
