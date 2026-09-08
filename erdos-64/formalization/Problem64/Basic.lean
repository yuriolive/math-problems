import Init.Data.List.Basic

namespace Problem64

/-- A simple undirected finite graph represented by adjacency matrix -/
structure FiniteGraph where
  n : Nat
  adj : Fin n → Fin n → Bool
  symm : ∀ u v, adj u v = adj v u
  no_loop : ∀ u, adj u u = false

/-- Degree of vertex u -/
def degree (G : FiniteGraph) (u : Fin G.n) : Nat :=
  (List.finRange G.n).filter (fun v => G.adj u v) |>.length

/-- Minimum degree of the graph -/
def minDegree (G : FiniteGraph) : Nat :=
  match (List.finRange G.n).map (degree G) with
  | [] => 0
  | d :: ds => ds.foldl min d

/-- A power of two integer >= 4 -/
def IsPowerOfTwoGe4 (k : Nat) : Prop :=
  ∃ m : Nat, m ≥ 2 ∧ k = 2 ^ m

/-- Statement of Erdős–Gyárfás Conjecture -/
def ErdosGyarfasConjecture : Prop :=
  ∀ (G : FiniteGraph), minDegree G ≥ 3 →
    ∃ (k : Nat), IsPowerOfTwoGe4 k ∧ (∃ (cycle : List (Fin G.n)), cycle.length = k)

end Problem64
