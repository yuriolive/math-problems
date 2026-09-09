# Candidate problems

A scouting pass over four families — open Erdős problems, discrete-geometry optimisation
with tracked records, extremal combinatorics, and unverified proof claims formalizable in
Lean — screened against the four questions in [`tools/intake`](../tools/intake/).

**Method.** Twenty candidates were scouted, then each was handed to a separate screener
whose instructions were to *disqualify* it: verify the problem is genuinely open, that the
record is not a proven optimum, that no AI or automated project has already taken it, and
that the objective really has a gradient rather than only appearing to. Fourteen were
screened before the pass was stopped. Five more were screened afterwards through the
Antigravity CLI (`agy --print`, `gemini-3.1-pro-high`, sandboxed), leaving four still
unscreened for the reason recorded at the bottom.

**Result: two candidates survived out of nineteen screened.** That ratio is the useful part
of this document. Most plausible-looking targets fail on a specific, checkable ground, and
the failures cluster into six repeatable patterns — recorded at the bottom, because they are
what the intake filter should be extended to catch.

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

### Erdős #857 — sunflower-free capacity $\mu_3$

A family is 3-sunflower-free if no three distinct sets $A, B, C$ satisfy
$A \cap B = A \cap C = B \cap C = A \cap B \cap C$. The capacity
$\mu_3 = \lim \max|\mathcal{F}|^{1/n}$ over 3-sunflower-free families on $[n]$ is open;
Erdős conjectured $\mu_3 < 2$.

| | |
| :--- | :--- |
| **Best known** | $1.551 < \mu_3 < 1.8899$ |
| **Lower bound** | Deuber, Erdős, Gunderson, Kostochka, Meyer, [doi:10.1006/jcta.1997.2778](https://doi.org/10.1006/jcta.1997.2778) — peer-reviewed |
| **Better lower bound** | $1.554$, Naslund, unpublished, cited in Naslund–Sawin, [doi:10.1017/fms.2017.12](https://doi.org/10.1017/fms.2017.12) |
| **Upper bound** | Naslund–Sawin, same paper |
| **Problem page** | [erdosproblems.com/857](https://www.erdosproblems.com/857), tracked as optimization constant C49 |

**Why it passes.** The checker is three bitwise ANDs and two comparisons per triple —
`u64` masks for $n \le 64$, $O(m^3)$ for a full audit and $O(m^2)$ incrementally, the same
shape as the Erdős #64 verifier. The gradient is the good part: fix a target size $m$ and
minimise the number of sunflower triples, and a single set swap moves the score by $O(m^2)$.
That is a dense min-conflicts landscape, not a max-over-pairs plateau — the failure mode
that killed most of the rejected candidates. To beat $1.554$ needs $m > 1.554^n$; over the
working window $n = 12 \ldots 24$ that is $m \approx 177$ to $40{,}600$, inside both the
64-vertex mask limit and the $O(m^3)$ audit limit of $m \approx 5\times10^4$.

**Not taken.** FunSearch attacked the closely related cap set problem; sunflower-free
capacity is distinct and untouched by FunSearch, AlphaEvolve, OpenEvolve or LoongFlow.

**The trap, and it is a sharp one.** The tensor-power argument requires the seed family to
be strictly **uniform**. Let the search evaluate non-uniform families and it will
immediately find a false record — $f(7) = 28$ gives $28^{1/7} \approx 1.609 > 1.554$ — which
yields no asymptotic bound at all, because non-uniform families lose sunflower-freeness
under the direct sum. **The checker must enforce uniformity rigidly**, or the first
"record" it reports will be worthless. This is precisely the class of error this repository
has already published once.

**First step, as a go/no-go gate.** Before any Rust or CUDA: extract the explicit base
construction from Deuber et al. (1997) with a throwaway script and verify it really yields
$1.551$. If it does not reproduce, the objective is not understood.

**Unconfirmed.** The screener could not verify the `SproutSeeds/sunflower-lean` repository
named in a forum claim, the unpublished Naslund manuscript itself (only its citation), or
arXiv preprint 2609.06175.

---

## Still unscreened — remaining work

Four candidates were never screened. All four halted on the same cause: the Antigravity
CLI needs a `read_url` (and for one, `command`) permission that **headless mode cannot
prompt for, so it is auto-denied**:

```
jetski: no output produced - a tool required the "read_url" permission that headless
mode cannot prompt for, so it was auto-denied.
```

These are **unfiltered** — scouted only. Screening killed 15 of the 19 candidates it
reached, so do not act on any of these without running it.

| Remaining candidate | Instrument | Blocked on |
| :--- | :--- | :--- |
| Weak Schur numbers $WS(6)$, $WS(7)$, Schur number $S(6)$ — lower bounds | sat | `read_url` |
| Erdős #864 — largest Sidon set in $\{1,\ldots,N\}$ with one exceptional sum | cuda-search | `read_url` |
| Erdős #1091 — the $K_4$-free 4-critical construction its own paper's Lean pipeline skipped | lean-proof | `read_url` |
| Erdős #960 — the $n^2/12$ ordinary-lines lower bound, the other unformalized sibling | lean-proof | `command` |

The two Lean candidates are the most interesting of the four: they need no search at all
and play to the layer no competing project has.

### How to finish them

The screening prompt is saved at
[`tools/intake/screening-prompt.txt`](../tools/intake/screening-prompt.txt) — it encodes the
four intake questions plus the failure patterns below. Append the candidate's section from
[`candidates-raw-notes.md`](./candidates-raw-notes.md) and pipe the whole thing in:

```bash
cat tools/intake/screening-prompt.txt candidate.txt > p.txt
agy --print="$(cat p.txt)" --model gemini-3.1-pro-high --sandbox --disable-slash-commands
```

To unblock the four above, add a narrow allow-rule to the Antigravity CLI settings —
**`read_url` only**, not a blanket approval:

```jsonc
// permissions.allow in the agy settings.json
"read_url(*)"
```

`--dangerously-skip-permissions` would also unblock it and should not be used here: it
auto-approves every tool including file writes and shell commands, for an agent doing
open-ended web research. The narrow rule is read-only.

---

## Rejected, and the pattern

Seventeen candidates were disqualified. The reasons collapse into four patterns, each worth
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
*Three-colour Ramsey $R(4,4,4)$* — simulated annealing over structured cyclic colourings is
exactly what Exoo and Wesley have applied to this for decades without moving
$R_3(4) \ge 129$; a GPU constant-factor speedup does not overcome a $3^{64}$ search space.

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

**5. The scout's own statement of the objective was mathematically wrong.** Both surviving
candidates exhibit this, so it is the rule and not the exception. *Ramsey multiplicity* —
supremum read as infimum, wrong denominator. *Erdős #840* (quasi-Sidon) — the penalty was
written as $\max(0, \rho - 1 - \varepsilon)$ instead of
$\max(0, 1 - \varepsilon - \rho)$, so it is identically zero and the search collapses to a
trivial $|A|$ maximiser that never enforces the property at all. *Erdős #857* — the
uniformity requirement was missing, which would have produced a false record on the first
run. **Every number in a candidate needs re-derivation from the source's own definitions
before any code is written.**

**6. A verification target with a flat objective and no theorem to redirect to.**
*Erdős #834* — a flat-objective verification of an already-resolved problem. For Erdős #64
the flat objective redirected usefully to the proof side because a real theorem was waiting
there. That redirection is not automatic, and without it "formalize the claim" is not a
contribution to an open question.
