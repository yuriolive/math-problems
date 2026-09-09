/-!
# Erdős Problem #64 (Erdős–Gyárfás): definitions

Every finite graph with minimum degree at least 3 contains a simple cycle whose
length is a power of two.

The previous version of this file stated the conjecture as

    ∃ k, IsPowerOfTwoGe4 k ∧ ∃ cycle : List (Fin G.n), cycle.length = k

which asserts only that a *list* of vertices of length `2^k` exists. `[v, v, v, v]`
satisfies it for any nonempty graph, so the statement was vacuous and could not
certify anything. Everything below therefore builds a real cycle predicate:
pairwise-distinct vertices, consecutive adjacency, and a closing edge.

Only Lean core is used (no Mathlib), so this builds standalone.
-/

namespace Problem64

/-! ### Graphs as adjacency lists -/

/-- A finite graph on the vertices `0, 1, ..., n-1`, given by neighbour lists. -/
structure GraphData where
  n : Nat
  adj : List (List Nat)
  deriving Repr, Inhabited

namespace GraphData

/-- `nthNeighbours l i` is the `i`-th entry of `l`, or `[]` when out of range.
Written out rather than using `List.get?`/`getD` so that this file is insensitive to
core API renames. -/
def nthNeighbours : List (List Nat) → Nat → List Nat
  | [], _ => []
  | x :: _, 0 => x
  | _ :: xs, Nat.succ i => nthNeighbours xs i

/-- The neighbours of vertex `v`. -/
def neighbours (g : GraphData) (v : Nat) : List Nat :=
  nthNeighbours g.adj v

/-- Is `v` listed as a neighbour of `u`? -/
def hasEdge (g : GraphData) (u v : Nat) : Bool :=
  (g.neighbours u).contains v

/-- Degree of `v`, i.e. the length of its neighbour list. -/
def degree (g : GraphData) (v : Nat) : Nat :=
  (g.neighbours v).length

/-- The vertex list `[0, ..., n-1]`. -/
def vertices (g : GraphData) : List Nat :=
  List.range g.n

end GraphData

/-! ### Well-formedness -/

/-- Are all entries of a list pairwise distinct? -/
def allDistinct : List Nat → Bool
  | [] => true
  | x :: xs => !(xs.contains x) && allDistinct xs

namespace GraphData

/-- The adjacency data really describes a simple undirected graph: the right number
of neighbour lists, every neighbour in range, no self-loops, no repeated neighbour,
and symmetry. -/
def wellFormed (g : GraphData) : Bool :=
  (g.adj.length == g.n) &&
    (g.vertices.all fun u =>
      allDistinct (g.neighbours u) &&
        (g.neighbours u).all fun v =>
          Nat.blt v g.n && !(v == u) && g.hasEdge v u)

/-- Every vertex has degree exactly 3. -/
def isCubic (g : GraphData) : Bool :=
  g.vertices.all fun v => g.degree v == 3

/-- Every vertex has degree at least `k`. -/
def minDegreeAtLeast (g : GraphData) (k : Nat) : Bool :=
  g.vertices.all fun v => Nat.ble k (g.degree v)

end GraphData

/-! ### Cycles

A cycle is represented by the list of its vertices in traversal order. The predicate
demands what "simple cycle" actually means, so a repeated-vertex list cannot satisfy
it. -/

/-- Are consecutive entries adjacent? -/
def chainAdj (g : GraphData) : List Nat → Bool
  | [] => true
  | [_] => true
  | u :: v :: rest => g.hasEdge u v && chainAdj g (v :: rest)

/-- Last element of a list, with a default for the empty case. -/
def lastOr (d : Nat) : List Nat → Nat
  | [] => d
  | [x] => x
  | _ :: xs => lastOr d xs

/-- `c` is a simple cycle of `g`: at least three vertices, all distinct, all in
range, consecutive vertices adjacent, and the last adjacent back to the first. -/
def IsCycleOf (g : GraphData) (c : List Nat) : Bool :=
  match c with
  | [] => false
  | first :: _ =>
    Nat.ble 3 c.length &&
      allDistinct c &&
      (c.all fun v => Nat.blt v g.n) &&
      chainAdj g c &&
      g.hasEdge (lastOr first c) first

/-- `k` is a power of two that can be a cycle length, i.e. `k = 2^m` with `m ≥ 2`. -/
def IsPowerOfTwoGe4 (k : Nat) : Prop :=
  ∃ m : Nat, m ≥ 2 ∧ k = 2 ^ m

/-- The powers of two that can occur as a cycle length in a graph on `n` vertices.
A simple cycle has pairwise-distinct vertices, so its length never exceeds `n`. -/
def pow2LengthsUpTo (n : Nat) : List Nat :=
  let rec go (len : Nat) (fuel : Nat) : List Nat :=
    match fuel with
    | 0 => []
    | Nat.succ fuel' => if Nat.ble len n then len :: go (2 * len) fuel' else []
  go 4 n

/-! ### The conjecture, and what a counterexample is -/

/-- The Erdős–Gyárfás conjecture, for graphs given as adjacency data. -/
def ErdosGyarfasConjecture : Prop :=
  ∀ g : GraphData, g.wellFormed = true → g.minDegreeAtLeast 3 = true →
    ∃ c : List Nat, IsCycleOf g c = true ∧ IsPowerOfTwoGe4 c.length

/-- `g` is a counterexample: well-formed, minimum degree at least 3, and no simple
cycle whose length is a power of two. -/
structure IsCounterexample (g : GraphData) : Prop where
  wf : g.wellFormed = true
  minDeg : g.minDegreeAtLeast 3 = true
  noPow2Cycle : ∀ c : List Nat, IsCycleOf g c = true → ¬ IsPowerOfTwoGe4 c.length

/-- A counterexample refutes the conjecture. This is the only bridge lemma the
certificate needs, and it is proved, not assumed. -/
theorem not_conjecture_of_counterexample {g : GraphData} (h : IsCounterexample g) :
    ¬ ErdosGyarfasConjecture := by
  intro hconj
  obtain ⟨c, hc, hpow⟩ := hconj g h.wf h.minDeg
  exact h.noPow2Cycle c hc hpow

/-! ### Enumerating cycles of a fixed length

`pathsOfLength g k` lists every simple path on `k` vertices, most recent vertex
first. `hasCycleOfLength` then closes each path. This is exponential and only usable
for small `k`; see `Certificate.lean` for which lengths are checked in Lean and which
are delegated to the compiled verifier. -/

/-- Extend each path by one new vertex. -/
def extendPaths (g : GraphData) (paths : List (List Nat)) : List (List Nat) :=
  paths.foldr
    (fun p acc =>
      match p with
      | [] => acc
      | last :: _ =>
        (g.neighbours last).foldr
          (fun w acc2 => if p.contains w then acc2 else (w :: p) :: acc2) acc)
    []

/-- Every simple path on exactly `k` vertices, stored newest-vertex-first. -/
def pathsOfLength (g : GraphData) : Nat → List (List Nat)
  | 0 => []
  | 1 => g.vertices.map fun v => [v]
  | Nat.succ k => extendPaths g (pathsOfLength g k)

/-- Does `g` contain a simple cycle on exactly `len` vertices? -/
def hasCycleOfLength (g : GraphData) (len : Nat) : Bool :=
  if Nat.blt len 3 then false
  else
    (pathsOfLength g len).any fun p =>
      match p with
      | [] => false
      | last :: _ => g.hasEdge last (lastOr last p)

end Problem64
