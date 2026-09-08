import Problem1.Basic

namespace Problem1

/--
  Decidable boolean checker for distinct subset sums on concrete integer lists.
--/

def checkDuplicates (l : List Nat) : Bool :=
  let rec loop (seen : List Nat) : List Nat → Bool
    | [] => true
    | x :: xs => if seen.contains x then false else loop (x :: seen) xs
  loop [] l

/-- Computes all subset sums and verifies if there are no collisions -/
def verifySubsetSumsDecidable (A : List Nat) : Bool :=
  let sums := (allSubsets A).map subsetSum
  checkDuplicates sums

/-- Certificate verification theorem: if decidable checker evaluates to true, then sums are distinct -/
theorem decidable_verification_sound (A : List Nat) (h : verifySubsetSumsDecidable A = true) :
    ∀ s1 s2, s1 ∈ allSubsets A → s2 ∈ allSubsets A → subsetSum s1 = subsetSum s2 → s1 = s2 := by
  sorry

end Problem1
