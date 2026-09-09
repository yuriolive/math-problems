/-
# Bridge: Bisch's `IsMinCex` supplies `MinCexHyps`

`EGCStrict`/`EGCLift` prove the strict two-thirds bound from `MinCexHyps`, a bundle of
four facts about a minimal counterexample due to Carr and formalized by Andrew Bisch.
This file derives that bundle from Bisch's own `EGC.IsMinCex`, which makes

  `EGCStrict.strict_two_thirds` : MinCexHyps G → 2 * |V| < 3 * |V₃|

into an unconditional statement about minimal counterexamples.

## Bisch's file is a separate work and is not redistributed here

Source: <https://github.com/AJBisch/AJBisch.github.io/blob/main/EGC.lean>
Paper:  <https://doi.org/10.5281/zenodo.21574476>

That repository carries no license, so `EGC.lean` is **not** vendored into this one. Fetch
it yourself before building this module:

```bash
cd problems/erdos/64/formalization-egc
curl -sSfL https://raw.githubusercontent.com/AJBisch/AJBisch.github.io/main/EGC.lean \
  -o EGC.lean
lake build EGCBridge
```

`vendor/` is gitignored. Without it, `EGCStrict` and `EGCLift` still build and still prove
everything they claim — they are simply conditional on `MinCexHyps`.

## What is whose

Bisch's, used here as given: `V₄` is an independent set, every vertex has a cubic
neighbour, no 4-cycles, minimality in the order, and the absence of power-of-two cycles.
Carr proved the first two mathematically (arXiv:2605.22844); Bisch formalized them and
improved the density bound to `≥ 2/3`.

`jul059`'s, the mathematical argument for strictness: the equality analysis, the
contraction, and the observation that a cycle upstairs lifts to one of twice the length.
Posted as unverified on 26 July 2026, <https://www.erdosproblems.com/forum/thread/64#post-8130>.

Ours: only the Lean formalization of that argument, and this bridge. No step of the
mathematics below originates here.
-/

import EGCStrict
import EGCLift
import EGC

namespace EGCStrict

universe u

variable {V : Type u} [Fintype V] [DecidableEq V]
variable {G : SimpleGraph V} [DecidableRel G.Adj]

/-- Bisch's minimal-counterexample hypotheses are exactly the bundle this development
consumes. Each field is one of his lemmas, applied verbatim. -/
theorem minCexHyps_of_isMinCex (hG : EGC.IsMinCex G) : MinCexHyps G where
  nonempty := hG.nonempty
  degree_ge := hG.degree_ge
  indep := fun _ _ hu hw => hG.not_adj_of_four_le_degree hu hw
  dom := hG.exists_cubic_neighbor
  no_c4 := fun _ _ _ _ hab hbc hcd hda hac hbd => hG.no_c4 hab hbc hcd hda hac hbd
  min_order := fun W _ K _ hne hcard hdeg => hG.min_order W K hne hcard hdeg
  no_pow2 := fun v c hc k hk => hG.no_pow2 ⟨v, c, hc, k, hk⟩

/-! ### The bound, with no hypotheses left -/

/-- **Strictly more than two thirds of a minimal counterexample is cubic.**

`|V₃| ≥ 2|V₄| + 1`, so `3|V₃| > 2|V|`. Carr's published bound is `4/7`; Bisch's
unpublished improvement is `≥ 2/3`; this is the strict form. -/
theorem strict_two_thirds_of_isMinCex (hG : EGC.IsMinCex G) :
    2 * Fintype.card V < 3 * (cubic G).card :=
  strict_two_thirds (minCexHyps_of_isMinCex hG)

/-- The same over `ℚ`: `|V₃| > (2/3)|V|`. -/
theorem strict_two_thirds_rat_of_isMinCex (hG : EGC.IsMinCex G) :
    (2 / 3 : ℚ) * Fintype.card V < ((cubic G).card : ℚ) :=
  strict_two_thirds_rat (minCexHyps_of_isMinCex hG)

/-- The underlying counting statement: `|V₃| ≥ 2|V₄| + 1`. -/
theorem card_cubic_ge_succ_of_isMinCex (hG : EGC.IsMinCex G) :
    2 * (big G).card + 1 ≤ (cubic G).card :=
  card_cubic_ge_succ (minCexHyps_of_isMinCex hG)

end EGCStrict
