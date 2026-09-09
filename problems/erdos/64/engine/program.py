"""The candidate record passed between the searcher, the evaluator and the archive.

This is a plain data carrier with no search policy in it, which is why it outlived the
LLM synthesis loop it was originally written for: the GPU sweep, the MAP-Elites archive
and the Lean certificate export all speak in these.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GraphProgram:
    id: str
    code: str
    fitness: float
    is_counterexample: bool
    all_cubic: bool
    island_id: int = 0
    generation: int = 0
    parent_id: str | None = None
    details: list[dict[str, Any]] = field(default_factory=list)
    girth: int = 0
    diameter: int = 0
    bipartite: bool = False
    connected: bool = True
    pow2_cycle_total: int = 0
    diagnostic_trace: str = ""
    cycle_witness: list[int] | None = None


def rank_key(p: GraphProgram) -> tuple:
    """Ranking key, best last (use with max / reverse sort).

    A verified counterexample outranks everything. Otherwise fitness decides -- being
    cubic is already worth CUBIC_BONUS inside fitness, so it must not be a separate
    higher-priority term. An earlier key ordered on (counterexample, all_cubic, fitness),
    which let a cubic candidate scoring -500 displace a non-cubic one scoring 50000.
    """
    return (1 if p.is_counterexample else 0, p.fitness)
