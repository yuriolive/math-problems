# Krenn–Gu roadmap

The target is not the conjecture. It is **$n = 6$, three colours, multi-edges and
bichromatic edges allowed**, the smallest case no published result decides, reduced by R1
and R2 in the [README](./README.md) to a single system of 726 cubic equations in 135 complex
unknowns.

## Live directions

### A. Decide $n = 6$ exactly

Four milestones, each with a gate that kills the direction early if it is going to die.

**M0, reproduce Mantey at $n = 4$ (the gate).** Mantey decided the 78-equation,
54-unknown system at $n = 4$ with a Gröbner basis and found that $\mu(K_4) = 3$ with a unique
extremal configuration. Rebuild that decision from scratch: fix the
$(\mathbb{C}^*)^{12}$ gauge (the torus $w(e) \mapsto \lambda_{u,c(e_u)} \lambda_{v,c(e_v)} w(e)$,
which is the scaling lemma of [arXiv:2407.00303](https://arxiv.org/abs/2407.00303) read as a
group action), saturate by the three monochromatic weights, and ask whether the ideal is the
unit ideal. If this does not run in seconds, the $n = 6$ system, ten times larger in both
directions, is out of reach and direction A stops here. Verify the answer against
`instances/k4-d3.json`, which the checker already certifies.

**M1, the support layer.** A support is a subset of the 135 colour slots. Two conditions
are necessary for *any* weighting and cost nothing to test:

* every colour class has a monochromatic perfect matching (else that colour is infeasible);
* no non-monochromatic colouring carries exactly one perfect matching (a lone non-zero
  product cannot cancel). This is `support.unique_pm_nonmono` in the checker's report.

Bogdanov's lemma adds a third: at least one non-monochromatic colouring must carry two or
more matchings, so pure-support arguments alone cannot finish the case, but they can cut
the space hard before the algebra runs. Encode as CNF over the 135 slot variables with
matching constraints in the style of Vardi and Zhang's Tutte-theorem encodings
([arXiv:2209.13063](https://arxiv.org/abs/2209.13063)), break the
$S_6 \times S_3$ symmetry, and enumerate surviving supports up to isomorphism. **Every SAT
claim is re-checked by the compiled checker before it is believed** (rule 1).

**M2, the binomial class, decided by integer linear algebra.** Call a support *binomial*
when every feasible non-monochromatic colouring carries exactly two matchings and every
monochromatic colouring exactly one. Then the equations are
$\prod_{e \in P} w_e = -\prod_{e \in Q} w_e$ and $\prod_{e \in M_i} w_e = 1$: a system in the
abelian group $\mathbb{C}^*$ with exponent vectors $\mathbb{1}_P - \mathbb{1}_Q \in \mathbb{Z}^E$
and constants $\pm 1$. Such a system is solvable in $(\mathbb{C}^*)^E$ **iff** every integer
relation among the exponent vectors is matched by the corresponding product of constants
being $1$: a Smith-normal-form computation, exact, no Gröbner basis, and the solutions it
produces are roots of unity times free scalars, hence exactly certifiable by the checker.

This is the class a counterexample would most plausibly inhabit (minimal cancellation), it is
the cheapest thing on this roadmap to build, and "no binomial GHZ graph exists with $n > 4$"
is a publishable theorem in its own right if it comes out that way.

**M3, the general case, as a certificate.** For supports that survive M1 and are not
binomial, decide the saturated ideal
$I : (W_1 W_2 W_3)^\infty$ over $\mathbb{Q}$. The deliverable is **not** a solver's verdict but
an ideal-membership certificate: an explicit identity
$1 = \sum_i g_i f_i + h \cdot (t \cdot W_1 W_2 W_3 - 1)$ whose expansion is checkable by
polynomial arithmetic, by a script here, and in principle in Lean. Modular Gröbner bases are
a screen for choosing case splits, never the published answer.

**M4, write-up.** The 3.000 EUR requires peer-reviewed publication, so the output is a
paper with the certificates as supplementary data, built through `tools/paper`.

### B. Counterexample hunt in the cyclotomic regime

Cheap and worth doing in parallel with M1. Restrict weights to $\mathbb{Z}[\zeta_k]$ for small
$k$ (the binomial analysis in M2 is the reason to expect roots of unity rather than generic
complex numbers) and search supports at $n = 6$ and $n = 8$ with exact arithmetic. Every hit
is certified by `ghzcheck` (exit code 0, exact weights) rather than by a loss value, which is
the whole difference from a PyTheus-style run. Prior: low. Cost: low. Payoff: the prize and a
new interference effect.

### C. The Hafnian reformulation: read, do not race

The GHZ conditions say exactly this: with a vector $x_v \in \mathbb{C}^d$ per vertex and
$A_{uv} = x_u^{\mathsf{T}} W_{uv} x_v$,

$$\operatorname{Haf}\big(A(x)\big) = \sum_{i=1}^{d} \prod_{v \in V} x_{v,i} .$$

The GHZ tensor must be a Hafnian of bilinear forms in which the same matrix $W_{uv}$ is shared
by every perfect matching through $uv$. That sharing is the rigidity, and it puts the problem
in range of tensor-rank lower-bound technology (substitution, flattenings) for general $n$,
which is the natural route to the full conjecture.

It is also where the incumbents are. Krenn, Firsching, Tsoukalas, Gajjala, Gu and Chaudhuri
have *A Tensor-Algebraic No-Go Theorem for High-Dimensional Photonic GHZ States* in
preparation ([arXiv:2605.22763](https://arxiv.org/abs/2605.22763), §4 and reference 38), backed
by AlphaProof and by the authors of every partial result in the table. Racing that with this
stack is the mistake `CANDIDATES.md` records twice. Read the direction, use it to frame the
$n = 6$ decision, and expect to be scooped on the general theorem.

### D. Lean, for the certificate only

Krenn's group formalised the conjecture in Lean in July 2026. If M2 or M3 produces a
certificate, checking *that* in Lean is small and credible: a polynomial identity plus
`#print axioms`. Formalising the matching enumeration is not worth it: the compiled checker
is the ground truth and the roadmap says so out loud (rule 5).

## Closed directions

* **Positive real weights.** Closed by Bogdanov (2017): with $n > 4$ and three monochromatic
  matchings of distinct colours there is always a non-monochromatic matching. Demonstrated
  concretely by `instances/k6-d3-factorisation.json`, where three 1-factors of $K_6$ leave a
  non-monochromatic colouring with exactly one matching. **Any counterexample needs
  destructive interference**, so any search restricted to positive weights is empty by
  theorem.
* **Enumerating skeletons at $n = 6$.** Collapsed by R1: every candidate is a sub-support of
  the fully loaded $K_6$, so there is one system to decide, not a family of graphs to sweep.
  (The 4-connectivity theorem independently restricts $n = 6$ skeletons to $K_6$ minus a
  matching, which R1 already contains.)
* **Raising the upper bound on $d$.** By R2 a GHZ graph of dimension $\ge 3$ yields one of
  dimension exactly $3$, so a bound $\mu \le f(n)$ decides the conjecture only where
  $f(n) < 3$. Every published bound ($n - 3$, $n/\sqrt{2}$, $d \ge n$) is at least $3$ for
  every $n > 4$. Real theorems, wrong direction for this objective.
* **Vertex connectivity $\le 2$, maximum degree $\le 3$.** Settled unrestricted by
  [arXiv:2407.00303](https://arxiv.org/abs/2407.00303). A counterexample skeleton is
  4-connected with a vertex of degree at least 4.
* **Gradient descent on complex weights (PyTheus-style).** Not closed as mathematics; closed
  as a direction *for this repository*. It is the incumbent's own instrument, run at a scale
  this stack will not match, and its output is a float, not a certificate. Rule 11 applies
  before the layer is built rather than after.

## Prize logistics

The 3.000 EUR from Mario Krenn and Dominik Leitner requires the proof or counterexample to
appear in a respected peer-reviewed journal; the 1.000 EUR best-paper award is for work on
inherited vertex colourings and its listed nomination deadline (end of August 2024) is stale,
so confirm the current cycle before planning around it. Contact and terms are on
[the problem page](https://mariokrenn.wordpress.com/graph-theory-question/).

## Rules

The repository's working rules apply. The three that bite first here:

* Ground truth is a separate program from the search: SAT and algebra results are re-checked
  by `ghzcheck` before they are written down.
* "Absent" must never mean "not evaluated": a colouring with no matchings has weight exactly
  zero because the enumeration covered it, and the checker says which.
* Say which components are trusted and which are verified: the checker is verified code over
  exact arithmetic; a Gröbner basis from an external solver is trusted until its certificate
  is expanded and checked here.
