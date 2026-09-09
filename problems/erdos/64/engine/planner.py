"""Planner stage of the LoongFlow PES loop: an explicit blueprint before any code."""

import logging

try:
    from .agy_client import call_agy_prompt
    from .pes_memory import EvolutionaryMemory
    from .island import GraphProgram
except ImportError:  # direct script execution
    from agy_client import call_agy_prompt
    from pes_memory import EvolutionaryMemory
    from island import GraphProgram

logger = logging.getLogger(__name__)

# What is actually known about the problem, so the planner does not re-explore
# territory the literature has already closed off. Sources are listed in README.md.
KNOWN_CONSTRAINTS = """ESTABLISHED RESULTS (do not contradict these):
- Liu and Montgomery (2020) proved the conjecture TRUE for every graph whose minimum
  degree exceeds an absolute constant. A counterexample can therefore only have very
  small minimum degree, which is why the search is restricted to cubic graphs.
- The f(k) scale, where f(k) is the order of the smallest cubic graph with no cycle of
  length 2^m for any m <= k:
    f(2) = 10 exactly (the Petersen graph),
    f(3) = 24 exactly (Markstroem),
    54 <= f(4) <= 78 (lower bound unpublished, Markstroem; upper bound Exoo),
    f(5) <= 450 (Garcia 2026, correcting an error in Exoo's construction),
    f(6) <= 32640 (Garcia 2026).
- CONSEQUENCE THAT BOUNDS EVERY CONSTRUCTION: f(4) >= 54 means no cubic graph on 53 or
  fewer vertices avoids C4, C8 and C16 together. Any counterexample on n >= 16 vertices
  must avoid all three, so a cubic counterexample needs AT LEAST 54 VERTICES. Proposing
  a construction at n <= 52 is proposing something that provably does not exist.
- Garcia (2026): every graph of minimum degree >= 3 on at most 23 vertices has a C4 or a
  C8, so any counterexample needs at least 24 vertices.
- Markstroem (2004): a cubic counterexample needs at least 30 vertices.
- Nowbandegani and Esfandiari (2011): a bipartite counterexample needs at least 32.
  Tranquilli (2026) raised the cubic bipartite bound to 60 by covering n <= 58, and an
  unpublished sweep reports n <= 62.
- Settled families, so constructions inside them cannot work: 3-connected cubic planar
  (Heckman-Krakovski), diameter 2 (Carr), claw-free cubic below 114 vertices,
  P8-free and P10-free graphs, and several Cayley families over generalized
  quaternion, dihedral and semidihedral groups.
- Bipartite cubic graphs are a bad bet: exhaustive search found nothing in that class
  up to 62 vertices that even avoids C4, C8 and C16 simultaneously.

STRUCTURAL FACTS ABOUT A MINIMAL COUNTEREXAMPLE (Bisch, formalized in Lean 4):
- Vertices of degree >= 4 form an independent set.
- Every vertex has a neighbour of degree exactly 3.
- At least 2/3 of all vertices have degree exactly 3. Note this does NOT prove the
  minimal counterexample is cubic; cubic is a search heuristic, not a theorem."""


def generate_plan(
    parent: GraphProgram | None,
    memory: EvolutionaryMemory,
    target_n: int = 36,
    timeout_sec: float = 60.0,
) -> str:
    """PES stage 1: a concrete mathematical hypothesis, no code yet."""
    recent_lessons = memory.get_recent_lessons(k=5)
    elites_summary = memory.map_elites.summary()

    if parent:
        parent_section = f"""CURRENT STATE:
- Parent fitness {parent.fitness:.1f} (cubic: {parent.all_cubic}, girth: {parent.girth},
  connected: {parent.connected}, total 2^k cycles: {parent.pow2_cycle_total})
- MAP-Elites coverage:
{elites_summary}

PARENT GENERATOR CODE:
```python
{parent.code}
```"""
    else:
        parent_section = f"""CURRENT STATE:
- Starting from mathematical principles, no parent.
- MAP-Elites coverage:
{elites_summary}"""

    pow2_targets = [L for L in (4, 8, 16, 32, 64) if L <= target_n]

    prompt = f"""You are the theoretician in a LoongFlow PES agent attacking Erdős Problem #64
(the Erdős-Gyárfás conjecture).

OBJECTIVE:
Construct a 3-regular (cubic) graph on n = {target_n} vertices containing NO cycle whose
length is a power of two. At this order that means avoiding all of: {pow2_targets}.
The construction must be parameterized by the even integer n.

{KNOWN_CONSTRAINTS}

{parent_section}

PERSISTENT MEMORY (distilled from previous failures):
{recent_lessons}

TASK:
Do NOT write Python yet. Produce an explicit mathematical blueprint.

1. HYPOTHESIS: which construction family, and why is it not already excluded above?
   Prefer families with genuine room to avoid 2^k lengths:
   - Cayley graphs over NON-abelian groups (A5, S4, Frobenius groups, semidirect
     products) with three involutions or one involution plus a generator pair.
     Abelian Cayley graphs are hopeless: a*b*a^-1*b^-1 = 1 forces a 4-cycle.
   - Voltage graph / permutation lifts of a small base graph, with voltages chosen so
     that closed fibre walks have lengths outside the powers of two.
   - Snark families (Blanusa, flower, Goldberg) and their double covers.
   - Explicit non-vertex-transitive constructions: cubic graphs assembled from
     boundaried gadgets whose interface lengths are controlled directly.
2. ANTI-CYCLE ARGUMENT: state, for each target length in {pow2_targets}, the algebraic
   reason no cycle of that length can close. If a length can only be handled
   empirically, say so explicitly rather than hand-waving.
3. 2-ADIC CHECK: if the construction uses a modulus g = 2^a * u, remember that
   avoiding cycles modulo the odd part u proves nothing, because every large power of
   two is 0 mod 2^a. Reason with the full modulus g.
4. CONSTRUCTION SPEC: a step-by-step algorithm for arbitrary even n, including how
   3-regularity, simplicity and connectivity are guaranteed.

Be concise and concrete. Structure only, no code.
"""

    logger.info("Calling LoongFlow Planner (agy -p)...")
    return call_agy_prompt(prompt, timeout_sec=timeout_sec)
