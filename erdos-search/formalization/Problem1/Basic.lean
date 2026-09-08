import Init.Data.List.Basic

namespace Problem1

/--
  A finite set (or list without duplicates) of positive integers has distinct subset sums (SSD)
  if every subset sums to a unique value.
--/

/-- Sum of elements in a sublist -/
def subsetSum (s : List Nat) : Nat :=
  s.foldl (· + ·) 0

/-- Computes all subsets of a list -/
def allSubsets : List Nat → List (List Nat)
  | [] => [[]]
  | x :: xs =>
    let rest := allSubsets xs
    rest ++ rest.map (fun sub => x :: sub)

/-- A list of positive integers has Distinct Subset Sums (DSS / SSD) -/
def HasDistinctSubsetSums (A : List Nat) : Prop :=
  ∀ s1 s2, s1 ∈ allSubsets A → s2 ∈ allSubsets A → subsetSum s1 = subsetSum s2 → s1 = s2

/-- Bohman's asymptotic constant -/
def bohmanConstant : Float := 0.22002

/-- Ratio R = max(A) / 2^n -/
def ratio (maxVal : Nat) (n : Nat) : Float :=
  (maxVal.toFloat) / (2.0 ^ (n.toFloat))

/-- Erdős Problem #1 Asymptotic Goal: find constructions with ratio R < bohmanConstant -/
def BeatsBohmanBound (maxVal : Nat) (n : Nat) : Prop :=
  ratio maxVal n < bohmanConstant

end Problem1
