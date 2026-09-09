/-
# The density bound, reformulated through the cubic subgraph

Carr's bound is `4/7`, Bisch's is `≥ 2/3`, and `jul059`'s strictness argument (formalized
in `EGCLift`) gives `> 2/3`. This file isolates *what controls the constant*, and proves a
conditional improvement to `12/17`.

## The reformulation

`V₄` is independent, so every edge at a `V₄` vertex lands in `V₃`. Counting the
`V₃`–`V₄` edges from both ends gives

  `4|V₄| + S₃ ≤ 3|V₃|`,   where   `S₃ = ∑_{v ∈ V₃} (number of cubic neighbours of v)`.

`S₃` is twice the number of edges inside `V₃`, so the whole family of density bounds is
governed by how many edges the cubic set spans among itself:

* Carr's domination lemma gives every cubic vertex a cubic neighbour, so `S₃ ≥ |V₃|`, and
  the reformulation immediately yields `4|V₄| ≤ 2|V₃|` — this is Bisch's `2/3`
  (`card_big_le_of_domination` below).
* `2/3` is therefore exactly the bound obtained when `G[V₃]` is a **perfect matching**.
  A `K₂` component of `G[V₃]` — two adjacent cubic vertices whose four other edges all
  leave to `V₄` — is the unique configuration achieving the ratio `S₃ = |V₃|`.

## The conditional improvement

If no cubic vertex is trapped in such a `K₂` component, then `3 S₃ ≥ 4|V₃|` and the
reformulation gives

  `12|V| ≤ 17|V₃|`,  i.e.  `|V₃| ≥ (12/17)|V| ≈ 0.7059 |V|`.

The proof is a fibre count, not a connectivity argument: split `V₃` into `T` (exactly one
cubic neighbour) and `S` (at least two). The hypothesis sends each `v ∈ T` to a cubic
neighbour lying in `S`, and each `s ∈ S` can receive at most `cubicDeg s` of them, so
`|T| ≤ ∑_{s ∈ S} cubicDeg s`. Two cases on whether `|T| ≥ 2|S|` finish it.

## Why the hypothesis is not (yet) removable

Eliminating `K₂` components unconditionally would give `12/17` outright. It is not proved
here, and the obvious attacks fail for a structural reason worth recording. Bisch's
Proposition 4 pins the configuration down tightly — an adjacent cubic pair whose other
neighbours are all in `V₄` has a *unique* common neighbour, of degree exactly 4, forming a
triangle. But every local replacement that removes the pair (delete the pair and join its
`V₄` neighbours; delete the pair and the apex and join the apex's other two neighbours;
contract the triangle; delete the apex and rewire) changes cycle lengths by `±1` or `±2`.
A `2^k` cycle in the smaller graph then lifts to a cycle of length `2^k + 1` or `2^k + 2`,
which is not a power of two, so minimality yields no contradiction.

`jul059`'s argument escapes this only because in the perfect-matching case the operation
is *uniformly multiplicative*: `G` is a subdivision of the contraction, every cycle
doubles, and `2^k ↦ 2^(k+1)`. A single `V₃`–`V₃` edge destroys that uniformity.

Moreover the extremal configuration appears to be internally consistent with all of the
known structure (`V₄` independent, every vertex with a cubic neighbour, Proposition 4's
uniqueness, and no `C₄`): take `G[V₃]` a perfect matching with each degree-4 apex serving
two `K₂` components. So no counting argument resting on those lemmas alone can beat `2/3`
— an improvement has to use the cycle condition, which is exactly what the `±1` shift
blocks.
-/

import EGCStrict

open Finset SimpleGraph

namespace EGCStrict

universe u

variable {V : Type u} [Fintype V] [DecidableEq V]
variable {G : SimpleGraph V} [DecidableRel G.Adj]

/-! ### Cubic and big neighbourhoods -/

/-- The cubic neighbours of `v`. -/
def cubicNbrs (G : SimpleGraph V) [DecidableRel G.Adj] (v : V) : Finset V :=
  (cubic G).filter fun w => G.Adj v w

/-- The neighbours of `v` of degree at least 4. -/
def bigNbrs (G : SimpleGraph V) [DecidableRel G.Adj] (v : V) : Finset V :=
  (big G).filter fun w => G.Adj v w

/-- Number of cubic neighbours. -/
def cubicDeg (G : SimpleGraph V) [DecidableRel G.Adj] (v : V) : ℕ := (cubicNbrs G v).card

@[simp] lemma mem_cubicNbrs {v w : V} : w ∈ cubicNbrs G v ↔ G.degree w = 3 ∧ G.Adj v w := by
  simp [cubicNbrs]

@[simp] lemma mem_bigNbrs {v w : V} : w ∈ bigNbrs G v ↔ 4 ≤ G.degree w ∧ G.Adj v w := by
  simp [bigNbrs]

/-- With minimum degree at least 3, each neighbourhood splits into cubic and big parts. -/
lemma card_cubicNbrs_add_card_bigNbrs (hdeg : ∀ v : V, 3 ≤ G.degree v) (v : V) :
    (cubicNbrs G v).card + (bigNbrs G v).card = G.degree v := by
  classical
  have hunion : cubicNbrs G v ∪ bigNbrs G v = G.neighborFinset v := by
    ext w
    simp only [Finset.mem_union, mem_cubicNbrs, mem_bigNbrs, mem_neighborFinset]
    have := hdeg w
    constructor
    · rintro (⟨_, h⟩ | ⟨_, h⟩) <;> exact h
    · intro h
      rcases Nat.lt_or_ge (G.degree w) 4 with hlt | hge
      · exact Or.inl ⟨by omega, h⟩
      · exact Or.inr ⟨hge, h⟩
  have hdisj : Disjoint (cubicNbrs G v) (bigNbrs G v) := by
    rw [Finset.disjoint_left]
    intro w hw hw'
    rw [mem_cubicNbrs] at hw
    rw [mem_bigNbrs] at hw'
    omega
  have := Finset.card_union_of_disjoint hdisj
  rw [hunion, card_neighborFinset_eq_degree] at this
  omega

/-- For a cubic vertex the two counts add to 3. -/
lemma card_bigNbrs_eq (hdeg : ∀ v : V, 3 ≤ G.degree v) {v : V} (hv : G.degree v = 3) :
    (bigNbrs G v).card = 3 - cubicDeg G v := by
  have h := card_cubicNbrs_add_card_bigNbrs hdeg v
  rw [hv] at h
  simp only [cubicDeg]
  omega

/-- A cubic vertex has at most three cubic neighbours. -/
lemma cubicDeg_le_three (hdeg : ∀ v : V, 3 ≤ G.degree v) {v : V} (hv : G.degree v = 3) :
    cubicDeg G v ≤ 3 := by
  have h := card_cubicNbrs_add_card_bigNbrs hdeg v
  rw [hv] at h
  simp only [cubicDeg]
  omega

/-! ### The reformulation -/

/-- **The count that governs every density bound.**

`4|V₄| + S₃ ≤ 3|V₃|`, where `S₃` is the total number of cubic-to-cubic incidences. Since
`S₃` is twice the number of edges inside `V₃`, the constant in a density bound is decided
entirely by how many edges the cubic set spans among itself. -/
theorem four_card_big_add_sum_cubicDeg_le (H : MinCexHyps G) :
    4 * (big G).card + ∑ v ∈ cubic G, cubicDeg G v ≤ 3 * (cubic G).card := by
  classical
  -- Each `V₄` vertex sees only cubic vertices, so its degree counts cubic neighbours.
  have hleft : ∀ u ∈ big G, G.degree u = ((cubic G).filter fun v => G.Adj u v).card :=
    fun u hu => H.degree_eq_card_cubic_nbrs (mem_big.mp hu)
  -- Swap the double count to the `V₃` side.
  have hswap : ∑ u ∈ big G, ((cubic G).filter fun v => G.Adj u v).card
      = ∑ v ∈ cubic G, ((big G).filter fun u => G.Adj u v).card := by
    simp_rw [Finset.card_filter]
    exact Finset.sum_comm
  have hlow : 4 * (big G).card ≤ ∑ u ∈ big G, G.degree u := by
    have := Finset.card_nsmul_le_sum (big G) (fun u => G.degree u) 4 fun u hu => mem_big.mp hu
    simpa [mul_comm] using this
  -- On the `V₃` side each vertex contributes `3 - cubicDeg`.
  have hsym : ∀ v ∈ cubic G, ((big G).filter fun u => G.Adj u v).card = (bigNbrs G v).card := by
    intro v _
    congr 1
    ext u
    simp only [Finset.mem_filter, mem_big, mem_bigNbrs]
    exact ⟨fun h => ⟨h.1, h.2.symm⟩, fun h => ⟨h.1, h.2.symm⟩⟩
  have hpiece : ∀ v ∈ cubic G, (bigNbrs G v).card + cubicDeg G v = 3 := by
    intro v hv
    have h := card_cubicNbrs_add_card_bigNbrs H.degree_ge v
    rw [mem_cubic.mp hv] at h
    simp only [cubicDeg]
    omega
  have hsum : ∑ v ∈ cubic G, ((big G).filter fun u => G.Adj u v).card
      + ∑ v ∈ cubic G, cubicDeg G v = 3 * (cubic G).card := by
    rw [← Finset.sum_add_distrib]
    rw [Finset.sum_congr rfl (fun v hv => by rw [hsym v hv, hpiece v hv])]
    simp [mul_comm]
  calc 4 * (big G).card + ∑ v ∈ cubic G, cubicDeg G v
      ≤ (∑ u ∈ big G, G.degree u) + ∑ v ∈ cubic G, cubicDeg G v := by omega
    _ = ∑ v ∈ cubic G, ((big G).filter fun u => G.Adj u v).card
          + ∑ v ∈ cubic G, cubicDeg G v := by
        rw [Finset.sum_congr rfl hleft, hswap]
    _ = 3 * (cubic G).card := hsum

/-- **Bisch's bound, recovered.** Every cubic vertex has a cubic neighbour, so
`S₃ ≥ |V₃|` and the reformulation gives `4|V₄| ≤ 2|V₃|`. -/
theorem card_big_le_of_domination (H : MinCexHyps G) :
    4 * (big G).card ≤ 2 * (cubic G).card := by
  classical
  have hdom : ∀ v ∈ cubic G, 1 ≤ cubicDeg G v := by
    intro v hv
    obtain ⟨x, hvx, hx3⟩ := H.dom v
    have : x ∈ cubicNbrs G v := by rw [mem_cubicNbrs]; exact ⟨hx3, hvx⟩
    exact Finset.card_pos.mpr ⟨x, this⟩
  have hS : (cubic G).card ≤ ∑ v ∈ cubic G, cubicDeg G v := by
    have := Finset.card_nsmul_le_sum (cubic G) (fun v => cubicDeg G v) 1 hdom
    simpa using this
  have := four_card_big_add_sum_cubicDeg_le H
  omega

/-! ### The conditional improvement to `12/17`

`noK2Component` says no cubic vertex sits in a `K₂` component of `G[V₃]`: whenever a cubic
vertex has exactly one cubic neighbour, that neighbour has at least two. -/

/-- No `K₂` component in the graph induced on the cubic vertices. -/
def noK2Component (G : SimpleGraph V) [DecidableRel G.Adj] : Prop :=
  ∀ v : V, G.degree v = 3 → cubicDeg G v = 1 →
    ∃ w, G.Adj v w ∧ G.degree w = 3 ∧ 2 ≤ cubicDeg G w

/-- Under `noK2Component` the cubic set spans at least `(4/3)|V₃|` incidences. -/
theorem three_mul_sum_cubicDeg_ge (H : MinCexHyps G) (hno : noK2Component G) :
    4 * (cubic G).card ≤ 3 * ∑ v ∈ cubic G, cubicDeg G v := by
  classical
  set T := (cubic G).filter fun v => cubicDeg G v = 1 with hT
  set S := (cubic G).filter fun v => 2 ≤ cubicDeg G v with hS
  -- `T` and `S` partition `V₃`, because domination rules out `cubicDeg = 0`.
  have hdom : ∀ v ∈ cubic G, 1 ≤ cubicDeg G v := by
    intro v hv
    obtain ⟨x, hvx, hx3⟩ := H.dom v
    have : x ∈ cubicNbrs G v := by rw [mem_cubicNbrs]; exact ⟨hx3, hvx⟩
    exact Finset.card_pos.mpr ⟨x, this⟩
  have hpart : T.card + S.card = (cubic G).card := by
    rw [hT, hS]
    have h := Finset.card_filter_add_card_filter_not (s := cubic G)
      fun v => cubicDeg G v = 1
    have hcongr : ((cubic G).filter fun v => ¬ cubicDeg G v = 1)
        = (cubic G).filter fun v => 2 ≤ cubicDeg G v := by
      ext v
      simp only [Finset.mem_filter]
      constructor
      · rintro ⟨hv, h⟩
        have := hdom v hv
        exact ⟨hv, by omega⟩
      · rintro ⟨hv, h⟩
        exact ⟨hv, by omega⟩
    rw [hcongr] at h
    exact h
  -- The sum splits, `T` contributing exactly one each.
  have hsplit : ∑ v ∈ cubic G, cubicDeg G v = T.card + ∑ v ∈ S, cubicDeg G v := by
    rw [hT, hS, ← Finset.sum_filter_add_sum_filter_not (cubic G) (fun v => cubicDeg G v = 1)]
    congr 1
    · rw [Finset.sum_congr rfl (fun v hv => (Finset.mem_filter.mp hv).2)]
      simp
    · apply Finset.sum_congr _ (fun _ _ => rfl)
      ext v
      simp only [Finset.mem_filter]
      constructor
      · rintro ⟨hv, h⟩
        have := hdom v hv
        exact ⟨hv, by omega⟩
      · rintro ⟨hv, h⟩
        exact ⟨hv, by omega⟩
  -- Each `T` vertex points at an `S` vertex, and each `S` vertex absorbs at most
  -- `cubicDeg` of them: a fibre count, no connectivity needed.
  have hmapsto : ∀ v ∈ T, ∃ w, w ∈ S ∧ G.Adj v w := by
    intro v hv
    rw [hT, Finset.mem_filter, mem_cubic] at hv
    obtain ⟨w, hvw, hw3, hw2⟩ := hno v hv.1 hv.2
    exact ⟨w, by rw [hS, Finset.mem_filter, mem_cubic]; exact ⟨hw3, hw2⟩, hvw⟩
  choose! f hfS hfAdj using hmapsto
  have hTle : T.card ≤ ∑ s ∈ S, cubicDeg G s := by
    have hfib := Finset.card_eq_sum_card_fiberwise (f := f) (s := T) (t := S) hfS
    rw [hfib]
    refine Finset.sum_le_sum ?_
    intro s _
    -- the fibre over `s` consists of cubic neighbours of `s`
    have hsub : (T.filter fun v => f v = s) ⊆ cubicNbrs G s := by
      intro v hv
      rw [Finset.mem_filter] at hv
      obtain ⟨hvT, hvs⟩ := hv
      have hvcub : v ∈ cubic G := by
        have h' := hvT
        rw [hT, Finset.mem_filter] at h'
        exact h'.1
      rw [mem_cubicNbrs]
      refine ⟨mem_cubic.mp hvcub, ?_⟩
      have := hfAdj v hvT
      rw [hvs] at this
      exact this.symm
    exact Finset.card_le_card hsub
  have hS2 : 2 * S.card ≤ ∑ s ∈ S, cubicDeg G s := by
    have hmem : ∀ s ∈ S, 2 ≤ cubicDeg G s := by
      intro s hs
      rw [hS, Finset.mem_filter] at hs
      exact hs.2
    have := Finset.card_nsmul_le_sum S (fun s => cubicDeg G s) 2 hmem
    simpa [mul_comm] using this
  -- Two cases on whether `T` or `S` dominates.
  rcases Nat.lt_or_ge T.card (2 * S.card) with hcase | hcase
  · omega
  · omega

/-- **The conditional bound.** If `G[V₃]` has no `K₂` component then strictly more than
`12/17` of the vertices are cubic:  `12|V| ≤ 17|V₃|`.

This is `≈ 0.7059`, against Bisch's `2/3 ≈ 0.6667`. The hypothesis is exactly the
configuration that Bisch's Proposition 4 constrains; see the header for why removing it
resists the standard minimality arguments. -/
theorem twelve_seventeenths_of_noK2 (H : MinCexHyps G) (hno : noK2Component G) :
    12 * Fintype.card V ≤ 17 * (cubic G).card := by
  have hpart := card_cubic_add_card_big H.degree_ge
  have hmain := four_card_big_add_sum_cubicDeg_le H
  have hsum := three_mul_sum_cubicDeg_ge H hno
  omega

/-- The same over `ℚ`. -/
theorem twelve_seventeenths_rat_of_noK2 (H : MinCexHyps G) (hno : noK2Component G) :
    (12 / 17 : ℚ) * Fintype.card V ≤ ((cubic G).card : ℚ) := by
  have h := twelve_seventeenths_of_noK2 H hno
  have h' : (12 * Fintype.card V : ℚ) ≤ 17 * ((cubic G).card : ℚ) := by exact_mod_cast h
  linarith

end EGCStrict
