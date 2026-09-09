import Problem64.Basic

/-!
# Certificate template for Erdős Problem #64

What Lean can and cannot do here, stated plainly.

**Checked in Lean, by `decide`, i.e. by the kernel:**
* the adjacency data is a well-formed simple graph (`wellFormed`),
* every vertex has degree 3 (`isCubic`) and minimum degree at least 3,
* absence of cycles of a *short* power-of-two length.

**Not checked in Lean:** absence of `C16` and `C32` for a graph of 36+ vertices.
`hasCycleOfLength` enumerates simple paths, so at length 16 on a cubic graph there
are on the order of a million of them; the kernel will not evaluate that. Those
lengths are checked by the compiled Rust verifier (`verifier_64 --full`), which is
therefore a **trusted component**, not a verified one.

So a generated certificate is a genuine machine-checked proof of the structural
facts, plus a machine-checked proof of the short-cycle facts, plus a citation to the
Rust verifier for the long ones. Anyone claiming a solved problem needs to close that
last gap — by a Lean decision procedure with real pruning, or by an independent
reimplementation of the counter.

The self-tests below run on every `lake build`, so the machinery cannot silently rot.
-/

namespace Problem64.Certificate

open Problem64

/-! ## Self-tests: the predicates detect what they should -/

/-- K4: cubic, and it does contain a 4-cycle. -/
def k4 : GraphData :=
  { n := 4, adj := [[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]] }

example : k4.wellFormed = true := by decide
example : k4.isCubic = true := by decide
example : k4.minDegreeAtLeast 3 = true := by decide
example : hasCycleOfLength k4 4 = true := by decide

/-- A concrete 4-cycle in K4, exhibited as a cycle in the sense of `IsCycleOf`. -/
example : IsCycleOf k4 [0, 1, 2, 3] = true := by decide

/-- The cycle predicate rejects a repeated-vertex list. This is exactly the hole in
the previous formalization, which only asked for a list of the right length. -/
example : IsCycleOf k4 [0, 0, 0, 0] = false := by decide

/-- The Petersen graph: girth 5, so no 4-cycle, and it is not a counterexample
because it does contain an 8-cycle (checked by the Rust verifier; the Lean check
below is limited to the cheap lengths). -/
def petersen : GraphData :=
  { n := 10,
    adj := [[1, 4, 5], [0, 2, 6], [1, 3, 7], [2, 4, 8], [0, 3, 9],
            [0, 7, 8], [1, 8, 9], [2, 5, 9], [3, 5, 6], [4, 6, 7]] }

example : petersen.wellFormed = true := by decide
example : petersen.isCubic = true := by decide
example : hasCycleOfLength petersen 4 = false := by decide
example : hasCycleOfLength petersen 5 = true := by decide

/-- The powers of two a graph of this size could contain. -/
example : pow2LengthsUpTo 10 = [4, 8] := by decide
example : pow2LengthsUpTo 36 = [4, 8, 16, 32] := by decide
example : pow2LengthsUpTo 64 = [4, 8, 16, 32, 64] := by decide

/-! ## Template for a real candidate

`engine/main.py::export_lean_certificate` fills this in when the Rust verifier reports
a counterexample. The shape is:

```lean
def candidate : GraphData :=
  { n := 36, adj := [[..], ..] }

-- Kernel-checked structural facts:
theorem candidate_wellFormed : candidate.wellFormed = true := by decide
theorem candidate_cubic : candidate.isCubic = true := by decide
theorem candidate_minDegree : candidate.minDegreeAtLeast 3 = true := by decide

-- Kernel-checked short-cycle facts:
theorem candidate_no_c4 : hasCycleOfLength candidate 4 = false := by decide

-- Remaining obligation, currently discharged by verifier_64 and NOT by Lean:
--   hasCycleOfLength candidate 8  = false
--   hasCycleOfLength candidate 16 = false
--   hasCycleOfLength candidate 32 = false
-- Supplying those, `Problem64.IsCounterexample candidate` follows and
-- `not_conjecture_of_counterexample` turns it into a refutation of the conjecture.
```

No `sorry` appears anywhere in this project: an unproved obligation is written down as
a comment naming the tool that discharged it, never as a fake proof.
-/

end Problem64.Certificate
