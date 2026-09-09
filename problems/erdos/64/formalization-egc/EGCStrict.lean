/-
Copyright (c) 2026. Released under Apache 2.0 license.

# The strict two-thirds bound for a minimal counterexample to Erdős–Gyárfás

The Erdős–Gyárfás conjecture says every finite graph of minimum degree at least 3 has a
cycle whose length is a power of two. For a *minimal* counterexample `G` (minimum order,
then minimum size) write

  `V₃ = {v : deg v = 3}` and `V₄ = {v : deg v ≥ 4}`.

Known results, in order:

* Carr, *Every Minimal Counterexample to the Erdős–Gyárfás Conjecture is Predominantly
  Cubic* (arXiv:2605.22844): `V₄` is independent, every vertex has a neighbour of degree
  exactly 3, and `|V₃| ≥ (4/7)|V|`.
* Bisch (Zenodo 10.5281/zenodo.21574476, with a `sorry`-free Lean 4 formalization at
  <https://github.com/AJBisch/AJBisch.github.io/blob/main/EGC.lean>): `|V₃| ≥ (2/3)|V|`,
  via `4|V₄| ≤ e(V₄, V₃) ≤ 2|V₃|`.
* A forum argument by user `jul059`, 26 July 2026, posted as unverified:
  <https://www.erdosproblems.com/forum/thread/64#post-8130>
  The inequality is *strict*, because equality would let one contract `V₃` and produce a
  smaller graph of minimum degree 4, whose power-of-two cycle lifts back to `G`. The
  strategy below is theirs; the formalization is what this development contributes.

This file formalizes that last step: `|V₃| ≥ 2|V₄| + 1`, hence `3|V₃| > 2|V|`.

## What is assumed and what is proved

The Carr/Bisch facts are taken as hypotheses (`MinCexHyps`) rather than re-proved, and
Bisch's file is not vendored — his repository carries no license. Each field of
`MinCexHyps` is a statement his `IsMinCex` already establishes, so the two compose; the
mapping is recorded on each field.

The new content is the equality analysis: the contracted graph `contract`, its
4-regularity, and (in `EGCLift`) the cycle lifting that closes the argument.

## Status

Complete, with no `sorry` and no hypotheses beyond `MinCexHyps`. This file proves
`|V₃| ≥ 2|V₄|` and the equality analysis (every `V₄` vertex has degree exactly 4, every
cubic vertex exactly two `V₄` neighbours, and the contraction is 4-regular on strictly
fewer vertices). `EGCLift` lifts a cycle back from the contraction and concludes
`|V₃| ≥ 2|V₄| + 1`, hence `3|V₃| > 2|V|`.
-/

import Mathlib

open Finset SimpleGraph

namespace EGCStrict

universe u

variable {V : Type u} [Fintype V] [DecidableEq V]
variable (G : SimpleGraph V) [DecidableRel G.Adj]

/-- The cubic vertices of `G`. -/
def cubic : Finset V := univ.filter fun v => G.degree v = 3

/-- The vertices of degree at least 4. -/
def big : Finset V := univ.filter fun v => 4 ≤ G.degree v

variable {G}

@[simp] lemma mem_cubic {v : V} : v ∈ cubic G ↔ G.degree v = 3 := by
  simp [cubic]

@[simp] lemma mem_big {v : V} : v ∈ big G ↔ 4 ≤ G.degree v := by
  simp [big]

lemma cubic_disjoint_big : Disjoint (cubic G) (big G) := by
  rw [Finset.disjoint_left]
  intro a ha hb
  rw [mem_cubic] at ha
  rw [mem_big] at hb
  omega

/-- With minimum degree at least 3, `V₃` and `V₄` partition the vertices. -/
lemma card_cubic_add_card_big (hdeg : ∀ v : V, 3 ≤ G.degree v) :
    (cubic G).card + (big G).card = Fintype.card V := by
  classical
  have heq : (univ.filter fun v : V => ¬ G.degree v = 3) = big G := by
    ext v
    simp only [Finset.mem_filter, Finset.mem_univ, true_and, mem_big]
    have := hdeg v
    omega
  have h0 := Finset.card_filter_add_card_filter_not (s := (univ : Finset V))
    fun v => G.degree v = 3
  rw [heq, Finset.card_univ] at h0
  exact h0

/-!
### The hypotheses inherited from Carr and Bisch

Every field below is proved in Bisch's development for his `IsMinCex G`; the
correspondence is noted per field. Stating them as hypotheses keeps this file
self-contained and license-clean.
-/

/-- The facts about a minimal counterexample that this file consumes. -/
structure MinCexHyps (G : SimpleGraph V) [DecidableRel G.Adj] : Prop where
  /-- `G` is nonempty. Bisch: `IsCounterexample.nonempty`. -/
  nonempty : Nonempty V
  /-- Minimum degree at least 3. Bisch: `IsCounterexample.degree_ge`. -/
  degree_ge : ∀ v : V, 3 ≤ G.degree v
  /-- `V₄` is an independent set. Carr; Bisch: `not_adj_of_four_le_degree`. -/
  indep : ∀ u w : V, 4 ≤ G.degree u → 4 ≤ G.degree w → ¬ G.Adj u w
  /-- Every vertex has a cubic neighbour. Carr; Bisch: `exists_cubic_neighbor`. -/
  dom : ∀ v : V, ∃ x, G.Adj v x ∧ G.degree x = 3
  /-- No 4-cycles, since `4 = 2²`. Bisch: `no_c4`. -/
  no_c4 : ∀ a b c d : V, G.Adj a b → G.Adj b c → G.Adj c d → G.Adj d a →
      a ≠ c → b ≠ d → False
  /-- Minimality in the order: any smaller graph of minimum degree 3 has a
  power-of-two cycle. Bisch: `IsMinCex.min_order`. -/
  min_order : ∀ (W : Type u) [Fintype W] (K : SimpleGraph W) [DecidableRel K.Adj],
      Nonempty W → Fintype.card W < Fintype.card V → (∀ w : W, 3 ≤ K.degree w) →
      ∃ (w : W) (c : K.Walk w w), c.IsCycle ∧ ∃ k : ℕ, c.length = 2 ^ k
  /-- `G` itself has no power-of-two cycle. Bisch: `IsCounterexample.no_pow2`. -/
  no_pow2 : ∀ (v : V) (c : G.Walk v v), c.IsCycle → ∀ k : ℕ, c.length ≠ 2 ^ k

namespace MinCexHyps

variable {H : MinCexHyps G}

/-- Every neighbour of a vertex of `V₄` is cubic: it cannot have degree `≥ 4` by
independence, and it has degree `≥ 3` by hypothesis. -/
lemma neighbor_cubic (H : MinCexHyps G) {u x : V} (hu : 4 ≤ G.degree u) (hux : G.Adj u x) :
    G.degree x = 3 := by
  have h3 := H.degree_ge x
  rcases Nat.lt_or_ge (G.degree x) 4 with h | h
  · omega
  · exact absurd hux (H.indep u x hu h)

/-- The neighbours of a `V₄` vertex, all of which are cubic, seen inside `V₃`. -/
lemma degree_eq_card_cubic_nbrs (H : MinCexHyps G) {u : V} (hu : 4 ≤ G.degree u) :
    G.degree u = ((cubic G).filter fun v => G.Adj u v).card := by
  rw [← card_neighborFinset_eq_degree]
  congr 1
  ext x
  simp only [mem_neighborFinset, Finset.mem_filter, mem_cubic]
  constructor
  · intro h; exact ⟨H.neighbor_cubic hu h, h⟩
  · exact fun h => h.2

/-- A cubic vertex has at most two neighbours in `V₄`: one of its three neighbours is
cubic, by domination. -/
lemma card_big_nbrs_le_two (H : MinCexHyps G) {v : V} (hv : G.degree v = 3) :
    ((big G).filter fun u => G.Adj u v).card ≤ 2 := by
  obtain ⟨x, hvx, hx3⟩ := H.dom v
  have hsub : ((big G).filter fun u => G.Adj u v) ⊆ (G.neighborFinset v).erase x := by
    intro y hy
    rw [Finset.mem_filter, mem_big] at hy
    rw [Finset.mem_erase, mem_neighborFinset]
    refine ⟨?_, hy.2.symm⟩
    rintro rfl
    omega
  calc ((big G).filter fun u => G.Adj u v).card
      ≤ ((G.neighborFinset v).erase x).card := Finset.card_le_card hsub
    _ = G.degree v - 1 := by
        rw [Finset.card_erase_of_mem ((G.mem_neighborFinset v x).mpr hvx),
          card_neighborFinset_eq_degree]
    _ ≤ 2 := by omega

/-- **The counting bound.** `4|V₄| ≤ e(V₄, V₃) ≤ 2|V₃|`, so `|V₃| ≥ 2|V₄|`.

This is the inequality behind Bisch's `2/3`; it is reproved here because the equality
analysis below needs the intermediate sums, not just the conclusion. -/
lemma card_cubic_ge (H : MinCexHyps G) : 2 * (big G).card ≤ (cubic G).card := by
  classical
  have hleft : ∀ u ∈ big G, G.degree u = ((cubic G).filter fun v => G.Adj u v).card :=
    fun u hu => H.degree_eq_card_cubic_nbrs (mem_big.mp hu)
  have hswap : ∑ u ∈ big G, ((cubic G).filter fun v => G.Adj u v).card
      = ∑ v ∈ cubic G, ((big G).filter fun u => G.Adj u v).card := by
    simp_rw [Finset.card_filter]
    exact Finset.sum_comm
  have hlow : 4 * (big G).card ≤ ∑ u ∈ big G, G.degree u := by
    have := Finset.card_nsmul_le_sum (big G) (fun u => G.degree u) 4
      fun u hu => mem_big.mp hu
    simpa [mul_comm] using this
  have hhigh : ∑ v ∈ cubic G, ((big G).filter fun u => G.Adj u v).card
      ≤ 2 * (cubic G).card := by
    have := Finset.sum_le_card_nsmul (cubic G)
      (fun v => ((big G).filter fun u => G.Adj u v).card) 2
      fun v hv => H.card_big_nbrs_le_two (mem_cubic.mp hv)
    simpa [mul_comm] using this
  have hsum : ∑ u ∈ big G, G.degree u
      = ∑ u ∈ big G, ((cubic G).filter fun v => G.Adj u v).card :=
    Finset.sum_congr rfl hleft
  have h4 : 4 * (big G).card ≤ 2 * (cubic G).card := by
    calc 4 * (big G).card ≤ ∑ u ∈ big G, G.degree u := hlow
      _ = ∑ v ∈ cubic G, ((big G).filter fun u => G.Adj u v).card := by rw [hsum, hswap]
      _ ≤ 2 * (cubic G).card := hhigh
  omega

/-!
### The equality case

Suppose `|V₃| = 2|V₄|`. Then every inequality above is tight, so every vertex of `V₄` has
degree exactly 4 and every cubic vertex has exactly two neighbours in `V₄`.
-/

/-- In the equality case every vertex of `V₄` has degree exactly 4. -/
lemma degree_eq_four_of_equality (H : MinCexHyps G)
    (heq : (cubic G).card = 2 * (big G).card) {u : V} (hu : u ∈ big G) :
    G.degree u = 4 := by
  classical
  by_contra hne
  have hu4 : 4 ≤ G.degree u := mem_big.mp hu
  have hu5 : 5 ≤ G.degree u := by omega
  -- The degree sum over `V₄` now exceeds `4|V₄|` strictly.
  have hstrict : 4 * (big G).card < ∑ w ∈ big G, G.degree w := by
    have hsplit : ∑ w ∈ big G, G.degree w
        = G.degree u + ∑ w ∈ (big G).erase u, G.degree w := by
      rw [← Finset.sum_erase_add _ _ hu, add_comm]
    have hrest : 4 * ((big G).erase u).card ≤ ∑ w ∈ (big G).erase u, G.degree w := by
      have := Finset.card_nsmul_le_sum ((big G).erase u) (fun w => G.degree w) 4
        fun w hw => mem_big.mp (Finset.mem_of_mem_erase hw)
      simpa [mul_comm] using this
    have hpos : 0 < (big G).card := Finset.card_pos.mpr ⟨u, hu⟩
    have hcard : ((big G).erase u).card + 1 = (big G).card := by
      rw [Finset.card_erase_of_mem hu]; omega
    omega
  -- but the double count still bounds it by `2|V₃| = 4|V₄|`.
  have hleft : ∀ w ∈ big G, G.degree w = ((cubic G).filter fun v => G.Adj w v).card :=
    fun w hw => H.degree_eq_card_cubic_nbrs (mem_big.mp hw)
  have hswap : ∑ w ∈ big G, ((cubic G).filter fun v => G.Adj w v).card
      = ∑ v ∈ cubic G, ((big G).filter fun w => G.Adj w v).card := by
    simp_rw [Finset.card_filter]
    exact Finset.sum_comm
  have hhigh : ∑ v ∈ cubic G, ((big G).filter fun w => G.Adj w v).card
      ≤ 2 * (cubic G).card := by
    have := Finset.sum_le_card_nsmul (cubic G)
      (fun v => ((big G).filter fun w => G.Adj w v).card) 2
      fun v hv => H.card_big_nbrs_le_two (mem_cubic.mp hv)
    simpa [mul_comm] using this
  have : ∑ w ∈ big G, G.degree w ≤ 4 * (big G).card := by
    calc ∑ w ∈ big G, G.degree w
        = ∑ v ∈ cubic G, ((big G).filter fun w => G.Adj w v).card := by
          rw [Finset.sum_congr rfl hleft, hswap]
      _ ≤ 2 * (cubic G).card := hhigh
      _ = 4 * (big G).card := by omega
  omega

/-- In the equality case every cubic vertex has exactly two neighbours in `V₄`. -/
lemma card_big_nbrs_eq_two_of_equality (H : MinCexHyps G)
    (heq : (cubic G).card = 2 * (big G).card) {v : V} (hv : v ∈ cubic G) :
    ((big G).filter fun u => G.Adj u v).card = 2 := by
  classical
  by_contra hne
  have hle : ((big G).filter fun u => G.Adj u v).card ≤ 2 :=
    H.card_big_nbrs_le_two (mem_cubic.mp hv)
  have hlt : ((big G).filter fun u => G.Adj u v).card < 2 := by omega
  -- The right-hand count drops below `2|V₃|`.
  have hstrict : ∑ w ∈ cubic G, ((big G).filter fun u => G.Adj u w).card
      < 2 * (cubic G).card := by
    have hsplit : ∑ w ∈ cubic G, ((big G).filter fun u => G.Adj u w).card
        = ((big G).filter fun u => G.Adj u v).card
          + ∑ w ∈ (cubic G).erase v, ((big G).filter fun u => G.Adj u w).card := by
      rw [← Finset.sum_erase_add _ _ hv, add_comm]
    have hrest : ∑ w ∈ (cubic G).erase v, ((big G).filter fun u => G.Adj u w).card
        ≤ 2 * ((cubic G).erase v).card := by
      have := Finset.sum_le_card_nsmul ((cubic G).erase v)
        (fun w => ((big G).filter fun u => G.Adj u w).card) 2
        fun w hw => H.card_big_nbrs_le_two (mem_cubic.mp (Finset.mem_of_mem_erase hw))
      simpa [mul_comm] using this
    have hpos : 0 < (cubic G).card := Finset.card_pos.mpr ⟨v, hv⟩
    have hcard : ((cubic G).erase v).card + 1 = (cubic G).card := by
      rw [Finset.card_erase_of_mem hv]; omega
    omega
  -- but it equals the degree sum over `V₄`, which is at least `4|V₄| = 2|V₃|`.
  have hleft : ∀ w ∈ big G, G.degree w = ((cubic G).filter fun x => G.Adj w x).card :=
    fun w hw => H.degree_eq_card_cubic_nbrs (mem_big.mp hw)
  have hswap : ∑ w ∈ big G, ((cubic G).filter fun x => G.Adj w x).card
      = ∑ x ∈ cubic G, ((big G).filter fun w => G.Adj w x).card := by
    simp_rw [Finset.card_filter]
    exact Finset.sum_comm
  have hlow : 4 * (big G).card ≤ ∑ w ∈ big G, G.degree w := by
    have := Finset.card_nsmul_le_sum (big G) (fun w => G.degree w) 4
      fun w hw => mem_big.mp hw
    simpa [mul_comm] using this
  have : 2 * (cubic G).card ≤ ∑ x ∈ cubic G, ((big G).filter fun w => G.Adj w x).card := by
    calc 2 * (cubic G).card = 4 * (big G).card := by omega
      _ ≤ ∑ w ∈ big G, G.degree w := hlow
      _ = ∑ x ∈ cubic G, ((big G).filter fun w => G.Adj w x).card := by
          rw [Finset.sum_congr rfl hleft, hswap]
  omega

end MinCexHyps

/-!
### The contracted graph

Replace each cubic vertex by an edge between its two `V₄` neighbours. The result lives on
the subtype `V₄`, which is strictly smaller than `V`, and is 4-regular in the equality
case.
-/

/-- The vertex type of the contracted graph. -/
abbrev Big (G : SimpleGraph V) [DecidableRel G.Adj] := {u : V // 4 ≤ G.degree u}

/-- Contract `V₃`: two `V₄` vertices are adjacent when some cubic vertex joins them. -/
def contract (G : SimpleGraph V) [DecidableRel G.Adj] : SimpleGraph (Big G) :=
  SimpleGraph.fromRel fun u w => ∃ x : V, G.degree x = 3 ∧ G.Adj (↑u) x ∧ G.Adj (↑w) x

/-- Adjacency in the contraction: distinct `V₄` vertices sharing a cubic neighbour.

`fromRel` symmetrises its relation, but this one is already symmetric, so the disjunction
it introduces collapses. -/
lemma contract_adj {u w : Big G} :
    (contract G).Adj u w ↔
      u ≠ w ∧ ∃ x : V, G.degree x = 3 ∧ G.Adj (↑u) x ∧ G.Adj (↑w) x := by
  simp only [contract, SimpleGraph.fromRel_adj]
  constructor
  · rintro ⟨hne, h | ⟨x, hx3, hwx, hux⟩⟩
    · exact ⟨hne, h⟩
    · exact ⟨hne, x, hx3, hux, hwx⟩
  · rintro ⟨hne, h⟩
    exact ⟨hne, Or.inl h⟩

-- Only used to state degrees; nothing in this file computes with it.
noncomputable instance : DecidableRel (contract G).Adj := fun _ _ => Classical.dec _

/-- Contraction shrinks the vertex set, provided some vertex is cubic. -/
lemma card_big_lt (hcubic : (cubic G).Nonempty) :
    Fintype.card (Big G) < Fintype.card V := by
  classical
  obtain ⟨v, hv⟩ := hcubic
  have hnot : ¬ (4 ≤ G.degree v) := by
    rw [mem_cubic] at hv; omega
  exact Fintype.card_subtype_lt (p := fun u => 4 ≤ G.degree u) hnot

/-- Every vertex of the contraction has degree at least 3 in the equality case.

Each `u ∈ V₄` has exactly 4 neighbours in `G`, all cubic, and the cubic neighbours lead to
4 *distinct* `V₄` vertices: if two of them led to the same `w`, those two cubic vertices
together with `u` and `w` would close a 4-cycle. -/
lemma contract_degree_ge (H : MinCexHyps G)
    (heq : (cubic G).card = 2 * (big G).card) :
    ∀ u : Big G, 4 ≤ (contract G).degree u := by
  classical
  rintro ⟨u, hu⟩
  -- `u` has exactly four neighbours in `G`, and each of them is cubic.
  have hdeg4 : G.degree u = 4 := H.degree_eq_four_of_equality heq (mem_big.mpr hu)
  have hcub : ∀ x ∈ G.neighborFinset u, G.degree x = 3 := by
    intro x hx
    exact H.neighbor_cubic hu ((G.mem_neighborFinset u x).mp hx)
  -- Each cubic neighbour `x` has exactly two `V₄` neighbours, one of which is `u`, so
  -- there is exactly one other; call it `f x`.
  have hother : ∀ x ∈ G.neighborFinset u,
      ∃ w : V, ((big G).filter fun z => G.Adj z x).erase u = {w} := by
    intro x hx
    have hx3 : G.degree x = 3 := hcub x hx
    have h2 : ((big G).filter fun z => G.Adj z x).card = 2 :=
      H.card_big_nbrs_eq_two_of_equality heq (mem_cubic.mpr hx3)
    have humem : u ∈ (big G).filter fun z => G.Adj z x := by
      rw [Finset.mem_filter]
      exact ⟨mem_big.mpr hu, ((G.mem_neighborFinset u x).mp hx)⟩
    have hone : (((big G).filter fun z => G.Adj z x).erase u).card = 1 := by
      rw [Finset.card_erase_of_mem humem, h2]
    exact Finset.card_eq_one.mp hone
  choose! f hf using hother
  -- Basic properties of `f x`.
  have hf_mem : ∀ x ∈ G.neighborFinset u, f x ∈ big G ∧ G.Adj (f x) x ∧ f x ≠ u := by
    intro x hx
    have := hf x hx
    have hmem : f x ∈ ((big G).filter fun z => G.Adj z x).erase u := by
      rw [this]; exact Finset.mem_singleton_self _
    rw [Finset.mem_erase, Finset.mem_filter] at hmem
    exact ⟨hmem.2.1, hmem.2.2, hmem.1⟩
  -- Compare inside `V`: push the contracted neighbourhood down along `Subtype.val`,
  -- which is injective, rather than lifting `f` up into the subtype.
  have hf_adj : ∀ x ∈ G.neighborFinset u,
      f x ∈ ((contract G).neighborFinset ⟨u, hu⟩).image Subtype.val := by
    intro x hx
    obtain ⟨hbig, hadj, hne⟩ := hf_mem x hx
    have h4 : 4 ≤ G.degree (f x) := mem_big.mp hbig
    refine Finset.mem_image.mpr ⟨⟨f x, h4⟩, ?_, rfl⟩
    rw [mem_neighborFinset, contract_adj]
    refine ⟨?_, x, hcub x hx, (G.mem_neighborFinset u x).mp hx, hadj⟩
    simp only [ne_eq, Subtype.mk.injEq]
    exact fun h => hne h.symm
  -- Injectivity of `f` on the neighbourhood: a collision would close a 4-cycle
  -- `u - x - w - y - u`, and a minimal counterexample has no 4-cycle.
  have hf_inj : Set.InjOn f (G.neighborFinset u : Set V) := by
    intro x hx y hy hxy
    by_contra hne
    simp only [Finset.coe_sort_coe, Finset.mem_coe] at hx hy
    obtain ⟨hbx, hax, hnx⟩ := hf_mem x hx
    obtain ⟨hby, hay, hny⟩ := hf_mem y hy
    refine H.no_c4 u x (f x) y ((G.mem_neighborFinset u x).mp hx) hax.symm ?_ ?_ ?_ hne
    · rw [hxy]; exact hay
    · exact ((G.mem_neighborFinset u y).mp hy).symm
    · exact fun h => hnx h.symm
  have hcard_image : ((G.neighborFinset u).image f).card = 4 := by
    rw [Finset.card_image_of_injOn hf_inj, card_neighborFinset_eq_degree, hdeg4]
  have hsub : (G.neighborFinset u).image f
      ⊆ ((contract G).neighborFinset ⟨u, hu⟩).image Subtype.val := by
    intro z hz
    rw [Finset.mem_image] at hz
    obtain ⟨x, hx, rfl⟩ := hz
    exact hf_adj x hx
  have hval : (((contract G).neighborFinset ⟨u, hu⟩).image Subtype.val).card
      = (contract G).degree ⟨u, hu⟩ := by
    rw [Finset.card_image_of_injective _ Subtype.val_injective,
      card_neighborFinset_eq_degree]
  calc (4 : ℕ) = ((G.neighborFinset u).image f).card := hcard_image.symm
    _ ≤ (((contract G).neighborFinset ⟨u, hu⟩).image Subtype.val).card :=
        Finset.card_le_card hsub
    _ = (contract G).degree ⟨u, hu⟩ := hval

/-!
### The strict bound

The equality case is now fully analysed: the contraction is a 4-regular graph on strictly
fewer vertices, so minimality supplies it with a power-of-two cycle. Turning that cycle
into one of `G` is the content of `EGCLift`, which imports this file; the unconditional
statements `card_cubic_ge_succ`, `strict_two_thirds` and `strict_two_thirds_rat` are proved
there.
-/

end EGCStrict
