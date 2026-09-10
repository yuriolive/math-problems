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
> allowed, weights complex), nothing is settled beyond $n = 4$ except by graph class.
> Mario Krenn and Dominik Leitner offer **3.000 EUR** for the first proof or counterexample
> published in a peer-reviewed journal, and a **1.000 EUR** best-paper award for work on
> inherited vertex colourings ([Krenn's problem page](https://mariokrenn.wordpress.com/graph-theory-question/)).

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

**Answer.** Yes, and it is unusually sharp: **decide $n = 6$ in the unrestricted setting.**
Table 2 of [arXiv:2304.06407](https://arxiv.org/abs/2304.06407) lists the state of the art by
regime, and the row with both multi-edges and bichromatic edges allowed stops at $n = 4$
(Mantey, by Gröbner basis). The $n = 6$ and $n = 8$ SAT results assume no bichromatic edges;
the $n/\sqrt{2}$ bound assumes a simple skeleton. Nothing published decides whether a
6-vertex GHZ graph of dimension 3 exists when multi-edges *and* bichromatic edges are both
allowed.

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

R2 is the reason this problem directory targets $d = 3$ and nothing else. An upper bound of
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
than truncated when the cap is hit. The target window is $n \in \{6, 8\}$, comfortably
inside. The measurement command is in §3.

The comparison that matters, though, is the algebraic one: deciding $n = 6$ means deciding
whether **726 cubic equations in 135 complex unknowns** have a common solution with three
prescribed non-vanishing values, modulo a $(\mathbb{C}^*)^{18}$ gauge group and an
$S_6 \times S_3$ symmetry. Mantey's $n = 4$ instance, 78 equations in 54 unknowns, already
needed a Gröbner computation. Ours is a factor of ten larger in both directions, and no
published computation has done it. That is the gate: the roadmap's first milestone is a
decision procedure that reproduces Mantey's $n = 4$ answer, and if it cannot do $n = 4$
cheaply it will not do $n = 6$ at all.

**Verdict.** Pursue, with the risk named. The checker exists and reproduces the one published
extremal graph; the target is a specific published gap; the reach is measured. The failure
mode is not compute but the algebra layer, and the first milestone is designed to expose it
in days rather than months. See [`ROADMAP.md`](./ROADMAP.md) for the incumbent-race risk,
which is the second reason to keep the scope at $n = 6$.

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
| Prize | 3.000 EUR for a proof or a counterexample in a peer-reviewed journal; 1.000 EUR best-paper award | [Krenn's problem page](https://mariokrenn.wordpress.com/graph-theory-question/) |

The dates on Krenn's page are the authoritative record of what is claimed when: the
$d \ge n$ entry is dated May 2026 and the Lean formalisation of the conjecture July 2026.

**What the open region actually is.** Combining R2 with the table: a counterexample has
$n \ge 6$ even, exactly 3 colours, a $4$-connected skeleton, a vertex of degree $\ge 4$, at
least one bichromatic edge, and at least one non-monochromatic colouring whose matchings
cancel. At $n = 6$, a $4$-connected skeleton on 6 vertices is $K_6$ minus a matching, and by
R1 all four of those live inside the fully loaded $K_6$. So the whole $n = 6$ case is one
system of equations.

## 2. What would count as progress

In descending order of value, and each one is a separate flag:

1. **A counterexample.** A coloured, weighted multi-graph on $n > 4$ vertices whose checker
   report has `"counterexample": true`. Exact weights, exit code 0. Worth 3.000 EUR and a new
   quantum interference effect.
2. **Deciding $n = 6$ unrestricted.** Either a counterexample as above, or a machine-checked
   proof that the 726 cubic equations in 135 unknowns have no solution with the three
   monochromatic weights non-zero. This is the first unrestricted result past $n = 4$ in the
   literature.
3. **Deciding $n = 6$ for a named sub-regime**, with the regime stated as a theorem rather
   than as a search bound, for example all supports whose non-monochromatic colourings carry
   at most two matchings, where the system is binomial and decidable by integer linear
   algebra rather than by Gröbner basis.
4. **A reusable exact decision procedure** for these systems that reproduces Mantey's $n = 4$
   result in seconds. Nothing published does this; Mantey's own computation is a one-off.

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

Status of the search itself: **not started.** No claim is made here about $\mu(K_6)$.

## 4. Layout

```
problems/krenn-gu/matching-index/
├── README.md               this file
├── ROADMAP.md              what is worth trying, what is closed, and why
├── verifier/               exact ground-truth checker (Rust, no floating point)
├── instances/              the corpus, including the published K4 extremal graph
├── tools/                  full_support.py, the largest instance for a given (n, d)
└── tests/                  differential tests against an independent reference
```

`sat/` and `algebra/` arrive with the first milestone in the roadmap; `formalization/` only
if something turns out to be provable.
