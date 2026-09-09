"""Summarizer stage of the LoongFlow PES loop: abductive reflection into memory."""

import json
import logging

try:
    from .agy_client import call_agy_prompt, AgyError
    from .island import GraphProgram
    from .pes_memory import EvolutionaryMemory
except ImportError:  # direct script execution
    from agy_client import call_agy_prompt, AgyError
    from island import GraphProgram
    from pes_memory import EvolutionaryMemory

logger = logging.getLogger(__name__)


def summarize_and_reflect(
    blueprint: str,
    program: GraphProgram,
    memory: EvolutionaryMemory,
    timeout_sec: float = 60.0,
) -> dict:
    """PES stage 3: extract one transferable rule and store it."""
    is_elite = memory.map_elites.add(program)

    if program.is_counterexample:
        logger.info("Verifier reports a counterexample; nothing to reflect on.")
        return {
            "counterexample": True,
            "lesson": "Construction eliminates every power-of-two cycle length; verify "
                      "independently and record the graph.",
            "is_elite": is_elite,
        }

    witness = program.cycle_witness
    counts_by_n = {d.get("n"): d.get("counts") for d in program.details}

    prompt = f"""You are the reviewer in a LoongFlow PES agent attacking Erdős Problem #64.

THE PLANNER PROPOSED:
{blueprint}

THE RUST VERIFIER REPORTED:
- Fitness: {program.fitness:.1f}
- Cubic: {program.all_cubic} | Connected: {program.connected}
- Girth: {program.girth} | Diameter: {program.diameter} | Bipartite: {program.bipartite}
- Cycle counts per order (length -> count): {counts_by_n}
- Shortest offending cycle (vertex path): {witness}
- Diagnostics: {program.diagnostic_trace}

TASK (ABDUCTIVE REFLECTION):
1. Identify WHY this construction failed to avoid the shortest offending length.
   Refer to the actual vertices in the witness path where that helps.
2. State ONE generalizable, checkable mathematical rule a future planner can apply.
   It must be about the construction family, not about this single graph. If the real
   lesson is "this family cannot work", say that and why.

Reply with ONLY a JSON object:
{{
  "family": "name of the construction family tested",
  "failure_mode": "short phrase for why the cycle closed",
  "lesson": "one or two sentences, actionable and mathematically specific",
  "cycle_len": {len(witness) if witness else 0}
}}
"""

    logger.info("Calling LoongFlow Summarizer (agy -p)...")
    try:
        raw_summary = call_agy_prompt(prompt, timeout_sec=timeout_sec)
    except AgyError as e:
        logger.warning("Summarizer LLM call failed: %s", e)
        return {"counterexample": False, "lesson": None, "is_elite": is_elite, "error": str(e)}

    start_idx = raw_summary.find("{")
    end_idx = raw_summary.rfind("}") + 1
    if start_idx == -1 or end_idx <= start_idx:
        logger.warning("Summarizer returned no JSON object; no lesson recorded.")
        return {"counterexample": False, "lesson": None, "is_elite": is_elite}

    try:
        data = json.loads(raw_summary[start_idx:end_idx])
    except json.JSONDecodeError as e:
        logger.warning("Summarizer JSON was malformed (%s); no lesson recorded.", e)
        return {"counterexample": False, "lesson": None, "is_elite": is_elite}

    # No synthetic fallback lesson: an entry that just restates the diagnostic teaches
    # the planner nothing and used to pollute the memory file.
    stored = memory.add_lesson(
        family=data.get("family", "Unknown family"),
        failure_mode=data.get("failure_mode", "cycle closure"),
        lesson=data.get("lesson", ""),
        cycle_len=int(data.get("cycle_len") or (len(witness) if witness else 0)),
    )

    return {
        "counterexample": False,
        "lesson": data.get("lesson") if stored else None,
        "stored": stored,
        "is_elite": is_elite,
        "data": data,
    }
