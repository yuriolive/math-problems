# Candidate problems

A scouting pass over four families — open Erdős problems, discrete-geometry optimisation
with tracked records, extremal combinatorics, and unverified proof claims formalizable in
Lean — screened against the four questions in [`tools/intake`](../tools/intake/).

**Method.** Twenty candidates were scouted, then each was handed to a separate screener
whose instructions were to *disqualify* it: verify the problem is genuinely open, that the
record is not a proven optimum, that no AI or automated project has already taken it, and
that the objective really has a gradient rather than only appearing to. Fourteen were
screened before the pass was stopped; six were not reached and are unfiltered.

**Result: one candidate survived.** That ratio is the useful part of this document. Most
plausible-looking targets fail on a specific, checkable ground, and the failures cluster
into four repeatable patterns — recorded at the bottom, because they are what the intake
filter should be extended to catch.

---

## Pursue

### Ramsey multiplicity constant of $c_4$ (and $c_5$)

Let $k_t(G)$ count $t$-cliques and $k_t(n) = \min\{k_t(G) + k_t(\overline{G}) : |G| = n\}$.
The Ramsey multiplicity constant is $c_t = \lim_{n \to \infty} k_t(n)/\binom{n}{t}$. Erdős
conjectured $c_t = 2^{1 - \binom{t}{2}}$; Thomason disproved this for every $t \ge 4$.
Determining $c_4$ is open.

| | |
| :--- | :--- |
| **Best known** | $0.0296 < c_4 \le 4551721 \cdot 2^{-24} \cdot 3^{-2} < 0.030145$ — a gap of about 1.8% |
| **Upper bound** | Parczyk, Pokutta, Spiegel, Szabó, *New Ramsey Multiplicity Bounds and Search Heuristics*, FoCM 2024, [arXiv:2206.04036](https://arxiv.org/abs/2206.04036), [doi:10.1007/s10208-024-09675-6](https://doi.org/10.1007/s10208-024-09675-6) — peer-reviewed |
| **Lower bound** | Grzesik, Lee, Lidický, Volec, via flag algebras |
| **Prior chain** | Thomason 1989 $< 0.030304$; Thomason 1997 $< 0.030291$; Even-Zohar–Linial $< 0.030285$ |
| **Data** | the paper's core graphs, Zenodo [10.5281/zenodo.6602512](https://doi.org/10.5281/zenodo.6602512) |

**Why it passes all four questions.**

1. *Checker* — adjacency as $n$ rows of $\lceil n/64 \rceil$ `u64` words; exact 4-clique
   count in $O(n^3/64)$ word operations, about $7.1 \times 10^6$ at $n = 768$, well under a
   millisecond. Vertex-transitivity of a Cayley graph drops it to $O(n^2/64)$ by counting
   only cliques through vertex 0. Differential-test against a naive $O(n^4)$ loop at
   $n \le 60$. Exact integer arithmetic throughout — the record is a rational.
2. *Gradient* — **yes**, and this is the point. The entire 37-year improvement history
   moves in the 4th and 5th decimal place. Flipping one element of a Cayley generating set
   moves the score by $\sim 10^{-4}$; one edge of a general graph by $\sim 10^{-6}$. Same
   objective shape as the circle-packing results, in extremal combinatorics rather than
   geometry.
3. *Open gap* — $c_5$ is the softer target. The authors state verbatim that "due to the
   fact that we need to consider cliques of size 5, we were unable to go up Cayley graphs
   of order 384 or 768 as we did for $c_4$." That barrier is an artifact of their
   precomputed clique-index-table cost evaluation — $\binom{767}{3} \approx 7.5\times10^7$
   entries is tabulatable, $\binom{767}{4} \approx 1.4\times10^{10}$ is not — and **a
   bitmask kernel does not need the table at all.**
4. *Reach* — published constructions run 192 to 768 vertices; the bitmask checker's hard
   limit is about 4096 ($\approx 1.07\times10^9$ word ops, ~1 s per evaluation, 2 MB). Five
   times headroom, and the whole construction history (272, 288, 384, 768, 1024) fits
   inside it. **This is the comparison Erdős #64 failed and this one passes.**

**Two corrections the screener found, which must not be lost.**

*The objective is a supremum, not an infimum.* The source states that the sequence of
minimum proportions is **non-decreasing** in $n$, so $c_t$ is the supremum and
$(k_4(G) + k_4(\overline{G}))/\binom{n}{4}$ is a **lower** bound on $c_4$, not an upper
one. An upper bound needs the blow-up limit via the paper's Lemma 3.2,

$$c_t \le \frac{t!\,k_t(C) + \sum_{j=1}^{t} j!\,S(t,j)\,k_j(\overline{C})}{n^t}$$

over $n^t$, not $\binom{n}{4}$, and requiring $k_1 \ldots k_t$ of $C$ **and of its looped
complement**. That is why the record is an $n^t$-denominator rational
($768^4 = 2^{32} \cdot 3^4$).

*The glamorous instrument is the one with a published negative result.* Section 5.3 of the
same paper benchmarks cross-entropy and RL learned search in exactly this
Cayley-generating-set space and reports it inferior to tabu search and simulated annealing
on every instance — at order 192, CE reached only 0.03022, and order 768 was "a search
space where CE could not feasibly be run". So "nobody has run an LLM program search here"
is true but hollow: the nearest neighbour was run and lost. **The instrument with headroom
is the one this repository already has** — a bitmask cost kernel plus CUDA tabu/SA.

**First step, as a go/no-go gate.** Reproduce the two published rationals *before* writing
any search code: implement the Lemma 3.2 blow-up cost in exact integer arithmetic and
assert bit-exact equality with $4551721/(2^{24}\cdot3^2)$ for the $c_4$ graph and
$2320651/(2^{24}\cdot3^4)$ for the $c_5$ graph. If either fails to reproduce exactly, stop:
the objective is not understood. If both reproduce, target **$c_5$ first**, over GAP
`SmallGroups` of order 384 (20169 groups) and 768 (1090235 groups).

**Risks.** Every published gain came from raising the group order, and the authors warn the
true optimal construction "could be unexpectedly complex" and that whether *any* finite
blow-up attains $c_4$ is open. Race risk is real: AlphaEvolve has just done nine classical
Ramsey *number* lower bounds ([arXiv:2603.09172](https://arxiv.org/abs/2603.09172)), and
multiplicity is one step away for a team with far more compute.

---

## Not screened

The pass was stopped before these were checked. They are **unfiltered** — scouted only, and
the screening step is exactly what killed thirteen of their siblings. Do not act on any of
them without running the filter first.

| Candidate | Instrument |
| :--- | :--- |
| Putatively optimal coverings of $S^2$ by $n$ equal caps — Hardin–Sloane–Smith table, $n = 4\ldots130$, no published improvement in 32 years | cuda-search |
| Lower bound for the three-colour Ramsey number $R(4,4,4)$ | sat |
| Weak Schur numbers $WS(6)$, $WS(7)$, Schur number $S(6)$ — lower bounds | sat |
| Erdős #840 — largest quasi-Sidon subset of $\{1,\ldots,N\}$ | cuda-search |
| Erdős #857 — Erdős–Szemerédi 3-sunflower-free capacity | cuda-search |
| Erdős #864 — largest Sidon set in $\{1,\ldots,N\}$ with one exceptional sum | cuda-search |
| Erdős #834 — Ruiliang Li's resolution of the Erdős–Lovász 3-critical 3-graph problem, unrefereed preprint with a machine-checkable certificate half | lean-proof |
| Erdős #1091 — the $K_4$-free 4-critical construction its own paper's Lean pipeline skipped | lean-proof |
| Erdős #960 — the $n^2/12$ ordinary-lines lower bound, the other unformalized sibling from that paper | lean-proof |

The three Lean candidates are the most interesting of these, because they need no search at
all and play to the layer no competing project has.

---

## Rejected, and the pattern

Thirteen candidates were disqualified. The reasons collapse into four patterns, each worth
adding to the intake filter.

**1. The gradient was asserted, not measured.** *Grassmannian frames / Game of Sloanes* —
the score is a max over $\binom{n}{2}$ pairs, so at a generic configuration exactly one pair
is active and the gradient is zero in almost every direction. *Subspace codes* — the
screener built the instance (11811 planes of $PG(6,2)$, 2667 lines, conflict degree 210) and
measured the gradient dying far below the record. **A max-of-pairs objective is not
continuous just because its values are real.** Question 2 needs to be answered by
measurement on the actual instance, not by inspecting the formula.

**2. The wrong two numbers were compared for reach.** *$L_\infty$ star discrepancy* — for a
*search* target the binding limit is objective evaluations per second, not whether one exact
evaluation is feasible. This is the Erdős #64 failure in a new costume, which is precisely
what question 4 exists to catch, and it still slipped through at the scouting stage.

**3. The proposed instrument is the one that set the record, or is published as failing.**
*Football-pool / covering codes* — the tabulated bounds ($K_3(6,1) \le 73$,
$K_3(7,1) \le 186$, $K_3(8,1) \le 486$) were produced by the very method proposed. *Shannon
capacity of $C_7$* — the record holders state in the record-taking paper
([arXiv:2607.21517](https://arxiv.org/abs/2607.21517)) that simulated annealing and local
search do not work on it. **Check whether the record holder already tried your instrument
and said so in print.**

**4. Openness was cited for one thing and the deliverable was another.** *Erdős #1019* —
the mathematics is proved (Simonovits, thesis Chapter 9); only the exposition is missing.
*5-chromatic unit-distance graph* and the *Earth–Moon problem* — the deliverable is a
construction with a flat integer objective, and unlike Erdős #64 there is no theorem
waiting on the proof side to redirect to. *Audit of the 298 Lean-verified Erdős solutions* —
a compliance audit of other people's repositories; the "graded objective" is a progress bar,
not a gradient. **Also: the La Jolla Covering Repository has been retired — check the
score-keeper is alive before targeting its table.**

A fifth pattern, which the surviving candidate also exhibits: **the scout's own statement of
the objective was mathematically wrong** (supremum for infimum, wrong denominator). Every
number in a candidate needs re-derivation from the source's own definitions before any code
is written.
