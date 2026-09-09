/-
# Lifting cycles through the contraction

`EGCStrict` reduces the strict two-thirds bound to one geometric fact: a cycle in the
contracted graph lifts to a cycle of twice the length in `G`. This file builds that lift.

The construction: a contraction edge `a ~ b` exists because some cubic vertex `x` is
adjacent to both, so a walk `a → b` in the contraction becomes `a → x → b` in `G`. Doing
this along a whole cycle doubles its length.

The work is entirely in showing the result is a *cycle*, i.e. that no vertex repeats:

* the `V₄` vertices are distinct because the contraction cycle is a cycle;
* the inserted cubic vertices are distinct because, in the equality case, a cubic vertex
  has exactly two `V₄` neighbours and therefore determines the contraction edge it came
  from — and a cycle traverses each edge once;
* the two families are disjoint because `V₃ ∩ V₄ = ∅`.
-/

import EGCStrict

open Finset SimpleGraph

namespace EGCStrict

universe u

variable {V : Type u} [Fintype V] [DecidableEq V]
variable {G : SimpleGraph V} [DecidableRel G.Adj]

/-! ### The chosen cubic vertex of a contraction edge -/

/-- A cubic vertex adjacent to both endpoints of a contraction edge. -/
noncomputable def mid {a b : Big G} (h : (contract G).Adj a b) : V :=
  (contract_adj.mp h).2.choose

lemma mid_cubic {a b : Big G} (h : (contract G).Adj a b) : G.degree (mid h) = 3 :=
  (contract_adj.mp h).2.choose_spec.1

lemma adj_mid_left {a b : Big G} (h : (contract G).Adj a b) : G.Adj (↑a) (mid h) :=
  (contract_adj.mp h).2.choose_spec.2.1

lemma adj_mid_right {a b : Big G} (h : (contract G).Adj a b) : G.Adj (↑b) (mid h) :=
  (contract_adj.mp h).2.choose_spec.2.2

/-- The chosen vertex is never one of the `V₄` vertices: it is cubic and they are not. -/
lemma mid_ne_coe {a b : Big G} (h : (contract G).Adj a b) (c : Big G) : mid h ≠ ↑c := by
  intro hc
  have h3 : G.degree (mid h) = 3 := mid_cubic h
  have h4 : 4 ≤ G.degree (↑c : V) := c.2
  rw [hc] at h3
  omega

/-! ### The lift of a walk -/

/-- Replace every contraction edge by the two-edge path through its cubic vertex. -/
noncomputable def lift : {a b : Big G} → (contract G).Walk a b → G.Walk (↑a) (↑b)
  | _, _, Walk.nil => Walk.nil
  | _, _, Walk.cons h p => Walk.cons (adj_mid_left h) (Walk.cons (adj_mid_right h).symm (lift p))

@[simp] lemma lift_nil {a : Big G} : lift (Walk.nil : (contract G).Walk a a) = Walk.nil := rfl

@[simp] lemma lift_cons {a b c : Big G} (h : (contract G).Adj a b)
    (p : (contract G).Walk b c) :
    lift (Walk.cons h p)
      = Walk.cons (adj_mid_left h) (Walk.cons (adj_mid_right h).symm (lift p)) := rfl

/-- Lifting doubles the length. -/
lemma length_lift {a b : Big G} (p : (contract G).Walk a b) :
    (lift p).length = 2 * p.length := by
  induction p with
  | nil => simp
  | cons h p ih => simp [lift_cons, ih]; omega

/-! ### The inserted vertices -/

/-- The cubic vertices inserted along a walk, in order. -/
noncomputable def midList : {a b : Big G} → (contract G).Walk a b → List V
  | _, _, Walk.nil => []
  | _, _, Walk.cons h p => mid h :: midList p

@[simp] lemma midList_nil {a : Big G} :
    midList (Walk.nil : (contract G).Walk a a) = [] := rfl

@[simp] lemma midList_cons {a b c : Big G} (h : (contract G).Adj a b)
    (p : (contract G).Walk b c) :
    midList (Walk.cons h p) = mid h :: midList p := rfl

/-- The support of a lift is the `V₄` vertices together with the inserted cubic ones. -/
lemma mem_support_lift {a b : Big G} (p : (contract G).Walk a b) {v : V} :
    v ∈ (lift p).support ↔ v ∈ p.support.map (fun c : Big G => (↑c : V)) ∨ v ∈ midList p := by
  induction p with
  | nil => simp
  | cons h p ih =>
    simp only [lift_cons, Walk.support_cons, midList_cons, Walk.support_cons, List.map_cons,
      List.mem_cons, ih]
    tauto

/-- Every inserted vertex comes from an edge of the walk. -/
lemma exists_edge_of_mem_midList {a b : Big G} (p : (contract G).Walk a b) {x : V}
    (hx : x ∈ midList p) :
    ∃ (c d : Big G) (h : (contract G).Adj c d), s(c, d) ∈ p.edges ∧ mid h = x := by
  induction p with
  | nil => simp at hx
  | cons h p ih =>
    rw [midList_cons, List.mem_cons] at hx
    rcases hx with rfl | hx
    · exact ⟨_, _, h, by simp, rfl⟩
    · obtain ⟨c, d, hcd, hmem, hval⟩ := ih hx
      exact ⟨c, d, hcd, by simp [hmem], hval⟩


/-! ### A cubic vertex determines its contraction edge

This is where the equality case is used: a cubic vertex has exactly two `V₄` neighbours,
so the pair of endpoints it joins is forced.
-/

lemma mid_determines_pair (H : MinCexHyps G)
    (heq : (cubic G).card = 2 * (big G).card)
    {a b a' b' : Big G} (h : (contract G).Adj a b) (h' : (contract G).Adj a' b')
    (hmid : mid h = mid h') : s(a, b) = s(a', b') := by
  classical
  have hx3 : G.degree (mid h) = 3 := mid_cubic h
  have h2 : ((big G).filter fun w => G.Adj w (mid h)).card = 2 :=
    H.card_big_nbrs_eq_two_of_equality heq (mem_cubic.mpr hx3)
  have hmem : ∀ c : Big G, G.Adj (↑c) (mid h) →
      (↑c : V) ∈ (big G).filter fun w => G.Adj w (mid h) := by
    intro c hc
    rw [Finset.mem_filter]
    exact ⟨mem_big.mpr c.2, hc⟩
  have hane : (↑a : V) ≠ (↑b : V) := fun hh => h.ne (Subtype.val_injective hh)
  -- the two-element set is exactly {a, b}
  have hsub : ({(↑a : V), (↑b : V)} : Finset V) ⊆ (big G).filter fun w => G.Adj w (mid h) := by
    intro z hz
    rw [Finset.mem_insert, Finset.mem_singleton] at hz
    rcases hz with rfl | rfl
    · exact hmem a (adj_mid_left h)
    · exact hmem b (adj_mid_right h)
  have hcard2 : ({(↑a : V), (↑b : V)} : Finset V).card = 2 := Finset.card_pair hane
  have hEq : (big G).filter (fun w => G.Adj w (mid h)) = {(↑a : V), (↑b : V)} :=
    (Finset.eq_of_subset_of_card_le hsub (by rw [hcard2, h2])).symm
  -- a' and b' are adjacent to the same cubic vertex, so they land in that set
  have ha' : (↑a' : V) ∈ ({(↑a : V), (↑b : V)} : Finset V) := by
    rw [← hEq]
    exact hmem a' (by rw [hmid]; exact adj_mid_left h')
  have hb' : (↑b' : V) ∈ ({(↑a : V), (↑b : V)} : Finset V) := by
    rw [← hEq]
    exact hmem b' (by rw [hmid]; exact adj_mid_right h')
  rw [Finset.mem_insert, Finset.mem_singleton] at ha' hb'
  have hane' : (↑a' : V) ≠ (↑b' : V) := fun hh => h'.ne (Subtype.val_injective hh)
  rw [Sym2.eq_iff]
  rcases ha' with ha' | ha' <;> rcases hb' with hb' | hb'
  · exact absurd (ha'.trans hb'.symm) hane'
  · exact Or.inl ⟨(Subtype.val_injective ha').symm, (Subtype.val_injective hb').symm⟩
  · exact Or.inr ⟨(Subtype.val_injective hb').symm, (Subtype.val_injective ha').symm⟩
  · exact absurd (ha'.trans hb'.symm) hane'

/-- Along a trail, the inserted cubic vertices are pairwise distinct: each determines the
edge it came from, and a trail uses each edge once. -/
lemma mid_not_mem_midList (H : MinCexHyps G)
    (heq : (cubic G).card = 2 * (big G).card)
    {a b c : Big G} (h : (contract G).Adj a b) (p : (contract G).Walk b c)
    (hnodup : (Walk.cons h p).edges.Nodup) : mid h ∉ midList p := by
  intro hmem
  obtain ⟨d, e, hde, hedge, hval⟩ := exists_edge_of_mem_midList p hmem
  have hpair : s(a, b) = s(d, e) := mid_determines_pair H heq h hde hval.symm
  rw [Walk.edges_cons, List.nodup_cons] at hnodup
  exact hnodup.1 (hpair ▸ hedge)

lemma nodup_midList_of_trail (H : MinCexHyps G)
    (heq : (cubic G).card = 2 * (big G).card) :
    ∀ {a b : Big G} (p : (contract G).Walk a b), p.edges.Nodup → (midList p).Nodup := by
  intro a b p
  induction p with
  | nil => intro _; simp
  | @cons x y z h p ih =>
    intro hnodup
    rw [midList_cons, List.nodup_cons]
    refine ⟨mid_not_mem_midList H heq h p hnodup, ?_⟩
    rw [Walk.edges_cons, List.nodup_cons] at hnodup
    exact ih hnodup.2

/-! ### The lift of a path has distinct vertices -/

lemma nodup_support_lift :
    ∀ {a b : Big G} (p : (contract G).Walk a b),
      (p.support.map (fun c : Big G => (↑c : V))).Nodup → (midList p).Nodup →
      (∀ x ∈ midList p, ∀ c ∈ p.support, x ≠ (↑c : V)) →
      (lift p).support.Nodup := by
  intro a b p
  induction p with
  | nil => intro _ _ _; simp
  | @cons x y z h p ih =>
    intro hsupp hmid hdisj
    rw [Walk.support_cons, List.map_cons, List.nodup_cons] at hsupp
    rw [midList_cons, List.nodup_cons] at hmid
    have hdisj' : ∀ w ∈ midList p, ∀ c ∈ p.support, w ≠ (↑c : V) := by
      intro w hw c hc
      exact hdisj w (by rw [midList_cons]; exact List.mem_cons_of_mem _ hw) c
        (by rw [Walk.support_cons]; exact List.mem_cons_of_mem _ hc)
    have hIH : (lift p).support.Nodup := ih hsupp.2 hmid.2 hdisj'
    -- the inserted vertex is not in the rest of the lift
    have hmidnot : mid h ∉ (lift p).support := by
      rw [mem_support_lift]
      rintro (hin | hin)
      · obtain ⟨c, hc, hcv⟩ := List.mem_map.mp hin
        exact mid_ne_coe h c hcv.symm
      · exact hmid.1 hin
    -- and neither is the starting vertex
    have hxnot : (↑x : V) ∉ mid h :: (lift p).support := by
      rw [List.mem_cons]
      rintro (hh | hh)
      · exact mid_ne_coe h x hh.symm
      · rw [mem_support_lift] at hh
        rcases hh with hh | hh
        · exact hsupp.1 hh
        · exact hdisj (↑x : V) (by rw [midList_cons]; exact List.mem_cons_of_mem _ hh)
            x (by rw [Walk.support_cons]; simp) rfl
    rw [lift_cons, Walk.support_cons, Walk.support_cons, List.nodup_cons, List.nodup_cons]
    exact ⟨hxnot, hmidnot, hIH⟩

/-! ### The main lemma -/

/-- **Cycle lifting.** A power-of-two cycle in the contraction gives a power-of-two cycle
in `G`, of twice the length. -/
theorem exists_pow2_cycle_of_contract_cycle (H : MinCexHyps G)
    (heq : (cubic G).card = 2 * (big G).card)
    {u : Big G} (c : (contract G).Walk u u) (hc : c.IsCycle) {k : ℕ}
    (hk : c.length = 2 ^ k) :
    ∃ (v : V) (d : G.Walk v v), d.IsCycle ∧ ∃ k' : ℕ, d.length = 2 ^ k' := by
  classical
  -- peel the first edge off the cycle
  cases c with
  | nil => exact absurd rfl hc.ne_nil
  | @cons _ b _ h p =>
    have hsupp : p.support.Nodup := by
      have := hc.support_nodup
      rwa [Walk.support_cons, List.tail_cons] at this
    have hedges : (Walk.cons h p).edges.Nodup := hc.isTrail.edges_nodup
    have hmid : (midList p).Nodup := by
      have hpe : p.edges.Nodup := by
        rw [Walk.edges_cons, List.nodup_cons] at hedges
        exact hedges.2
      exact nodup_midList_of_trail H heq p hpe
    have hmap : (p.support.map (fun c : Big G => (↑c : V))).Nodup := by
      first
      | exact List.Nodup.map (fun _ _ hh => Subtype.val_injective hh) hsupp
      | exact hsupp.map (fun _ _ hh => Subtype.val_injective hh)
    have hdisj : ∀ x ∈ midList p, ∀ c ∈ p.support, x ≠ (↑c : V) := by
      intro x hx c _
      obtain ⟨d, e, hde, _, hval⟩ := exists_edge_of_mem_midList p hx
      rw [← hval]
      exact mid_ne_coe hde c
    have hliftnodup : (lift p).support.Nodup := nodup_support_lift p hmap hmid hdisj
    have hmidnot : mid h ∉ (lift p).support := by
      rw [mem_support_lift]
      rintro (hin | hin)
      · obtain ⟨d, _, hdv⟩ := List.mem_map.mp hin
        exact mid_ne_coe h d hdv.symm
      · exact mid_not_mem_midList H heq h p hedges hin
    refine ⟨(↑u : V), lift (Walk.cons h p), ?_, k + 1, ?_⟩
    · -- the lift is a cycle: an inner path plus one edge that the path does not use
      rw [lift_cons, Walk.cons_isCycle_iff]
      constructor
      · rw [Walk.isPath_def, Walk.support_cons]
        exact List.nodup_cons.mpr ⟨hmidnot, hliftnodup⟩
      · -- the first edge cannot reappear, because its cubic endpoint is not in the rest
        intro hcontra
        rw [Walk.edges_cons, List.mem_cons] at hcontra
        rcases hcontra with hcontra | hcontra
        · rw [Sym2.eq_iff] at hcontra
          rcases hcontra with ⟨h1, _⟩ | ⟨h1, _⟩
          · exact mid_ne_coe h u h1.symm
          · exact h.ne (Subtype.val_injective h1)
        · exact hmidnot (Walk.snd_mem_support_of_mem_edges _ hcontra)
    · rw [length_lift, hk]
      ring

/-! ### The strict two-thirds bound, unconditionally -/

/-- **The strict bound.** If `|V₃| = 2|V₄|` then the contraction is a 4-regular graph on
strictly fewer vertices, so minimality gives it a power-of-two cycle; lifting that cycle
contradicts `G` having none. Hence the inequality is strict: `|V₃| ≥ 2|V₄| + 1`. -/
theorem card_cubic_ge_succ (H : MinCexHyps G) :
    2 * (big G).card + 1 ≤ (cubic G).card := by
  classical
  rcases Nat.lt_or_ge (2 * (big G).card) (cubic G).card with hlt | hge
  · omega
  -- Equality holds, so we may contract.
  have heq : (cubic G).card = 2 * (big G).card := le_antisymm hge H.card_cubic_ge
  -- `V` is nonempty and `V₃ ∪ V₄ = V`, so neither part can vanish: if `V₄` were empty
  -- then `|V₃| = 2 * 0 = 0` and hence `|V| = 0`.
  have hpart := card_cubic_add_card_big H.degree_ge
  have hVpos : 0 < Fintype.card V := Fintype.card_pos_iff.mpr H.nonempty
  have hbigpos : 0 < (big G).card := by
    rcases Nat.eq_zero_or_pos (big G).card with h0 | h
    · rw [h0] at heq hpart; omega
    · exact h
  have hcubic : (cubic G).Nonempty := by
    have : 0 < (cubic G).card := by omega
    exact Finset.card_pos.mp this
  have hbig : (big G).Nonempty := Finset.card_pos.mp hbigpos
  have hne : Nonempty (Big G) := by
    obtain ⟨u, hu⟩ := hbig
    exact ⟨⟨u, mem_big.mp hu⟩⟩
  obtain ⟨w, c, hc, k, hk⟩ :=
    H.min_order (Big G) (contract G) hne (card_big_lt hcubic)
      (fun w => le_trans (by omega) (contract_degree_ge H heq w))
  obtain ⟨v, d, hd, k', hk'⟩ := exists_pow2_cycle_of_contract_cycle H heq c hc hk
  exact absurd hk' (H.no_pow2 v d hd k')

/-- `3|V₃| > 2|V|`: strictly more than two thirds of the vertices of a minimal
counterexample are cubic. -/
theorem strict_two_thirds (H : MinCexHyps G) :
    2 * Fintype.card V < 3 * (cubic G).card := by
  have hpart := card_cubic_add_card_big H.degree_ge
  have hstrict := card_cubic_ge_succ H
  omega

/-- The same statement over `ℚ`: `|V₃| > (2/3)|V|`. -/
theorem strict_two_thirds_rat (H : MinCexHyps G) :
    (2 / 3 : ℚ) * Fintype.card V < ((cubic G).card : ℚ) := by
  have h := strict_two_thirds H
  have h' : (2 * Fintype.card V : ℚ) < 3 * ((cubic G).card : ℚ) := by exact_mod_cast h
  linarith

end EGCStrict
