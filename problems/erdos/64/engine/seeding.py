"""Shared seeding helpers.

`campaign_solver.py` and `pes_main.py` both need to load saved candidate graphs into
the MAP-Elites archive. They used to carry separate copies of this logic, including a
copy each of a subtle bug: the loaded graph was wrapped in a generator that returned a
Möbius ladder for every order other than its own, so evaluating the "candidate" across
several orders scored an unrelated graph most of the time.
"""

import json
import logging
from pathlib import Path

try:
    from .evaluator import evaluate_graph_code
    from .program import GraphProgram
except ImportError:  # direct script execution
    from evaluator import evaluate_graph_code
    from program import GraphProgram

logger = logging.getLogger(__name__)


def candidate_to_generator_code(n: int, adj: list[list[int]]) -> str:
    """Wraps a concrete adjacency list as a single-order generator.

    It raises for any other order instead of silently substituting a different graph.
    """
    return (
        "def generate_graph(n: int) -> dict:\n"
        f"    # Saved candidate at n = {n}.\n"
        f"    adj = {adj!r}\n"
        f"    if n != {n}:\n"
        f"        raise ValueError('this candidate is only defined for n = {n}')\n"
        f"    return {{'n': {n}, 'adj': adj}}\n"
    )


def load_candidate(path: Path) -> tuple[int, list[list[int]]] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Could not read candidate %s: %s", path.name, e)
        return None
    adj = data.get("adj")
    n = data.get("n", len(adj) if adj else 0)
    if not adj or n != len(adj):
        logger.warning("Candidate %s has no usable adjacency list.", path.name)
        return None
    return n, adj


def seed_archive_from_candidates(memory, cuda_dir: Path, count_cap: int = 1000) -> int:
    """Adds every `best_swarm_n*.json` candidate to the archive at its own order."""
    added = 0
    for path in sorted(cuda_dir.glob("best_swarm_n*.json")):
        loaded = load_candidate(path)
        if not loaded:
            continue
        n, adj = loaded
        code = candidate_to_generator_code(n, adj)
        prog = evaluate_graph_code(
            code, program_id=f"gpu_swarm_n{n}", test_ns=[n], count_cap=count_cap
        )
        if memory.map_elites.add(prog):
            added += 1
    return added


def seed_archive_from_generators(memory, test_ns: list[int], count_cap: int = 1000) -> int:
    """Adds the baseline algebraic families to the archive."""
    try:
        from .baseline_graphs import get_seed_generators
    except ImportError:
        from baseline_graphs import get_seed_generators

    added = 0
    for name, code in get_seed_generators().items():
        prog = evaluate_graph_code(
            code, program_id=f"seed_{name}", test_ns=test_ns, count_cap=count_cap
        )
        if memory.map_elites.add(prog):
            added += 1
    return added
