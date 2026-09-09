"""Mutation prompts for the island engine.

The LLM call itself lives in `agy_client`; this module only builds prompts.
"""

import logging

try:
    from .agy_client import call_agy_prompt, extract_python_code
    from .planner import KNOWN_CONSTRAINTS
except ImportError:  # direct script execution
    from agy_client import call_agy_prompt, extract_python_code
    from planner import KNOWN_CONSTRAINTS

logger = logging.getLogger(__name__)


def mutate_with_agy(prompt: str, timeout_sec: float = 60.0) -> str:
    return extract_python_code(call_agy_prompt(prompt, timeout_sec=timeout_sec))


def build_graph_mutation_prompt(
    parent_code: str,
    parent_fitness: float,
    island_id: int,
    generation: int,
    diagnostic_trace: str = "",
    target_ns: list[int] | None = None,
) -> str:
    """Trace-reflective mutation prompt: parent code plus the verifier's witness."""
    if target_ns is None:
        target_ns = [36, 38, 40]

    trace_section = ""
    if diagnostic_trace:
        trace_section = f"""
=== VERIFIER DIAGNOSTICS FOR THE PREVIOUS CANDIDATE ===
{diagnostic_trace}

Use this: the witness lists the exact vertices of the shortest offending cycle.
Change the generator so that cycle cannot close, while keeping strict 3-regularity.
=======================================================
"""

    pow2_targets = sorted({L for n in target_ns for L in (4, 8, 16, 32, 64) if L <= n})

    return f"""You are an extremal graph theorist attacking Erdős Problem #64
(the Erdős-Gyárfás conjecture).

GOAL: a cubic graph with no cycle whose length is a power of two. At the orders being
tested ({target_ns}) that means avoiding all of: {pow2_targets}.

Parent fitness: {parent_fitness:.1f} | Island {island_id} | Generation {generation}.

{KNOWN_CONSTRAINTS}
{trace_section}
CURRENT GENERATOR:
```python
{parent_code}
```

TASK: propose an improved `def generate_graph(n: int) -> dict:` that
1. returns {{'n': n, 'adj': [[neighbour, ...], ...]}};
2. gives every vertex degree exactly 3, with no self-loops or multi-edges;
3. returns a CONNECTED graph (a disconnected cubic graph is never a new
   counterexample, since one component would already be a smaller one);
4. targets the lengths above, shortest first: eliminating C4 and C8 matters more than
   reducing C16, and a graph with no C8 beats one with fewer C16 but an C8 present.

Worth exploring: Cayley graphs on non-abelian groups (A4, A5, S4) with three chosen
generators; voltage graph and permutation lifts; snarks (Blanusa, flower, Goldberg)
and their covers; boundaried gadget assemblies with controlled interface lengths.
Avoid abelian Cayley graphs: the commutator relation forces a 4-cycle.

Output ONLY the Python code in a ```python ... ``` block.
"""
