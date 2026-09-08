"""
Summarizer module for LoongFlow PES architecture.
Performs Abductive Reflection on verifier diagnostic traces and updates Evolutionary Memory.
"""

import json
import logging
import subprocess
try:
    from .island import GraphProgram
    from .pes_memory import EvolutionaryMemory
except ImportError:
    from island import GraphProgram
    from pes_memory import EvolutionaryMemory

logger = logging.getLogger(__name__)

def call_agy_prompt(prompt: str, timeout_sec: float = 60.0) -> str:
    cmd = ["agy", "-p", prompt]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout_sec,
    )
    return result.stdout.strip()

def summarize_and_reflect(
    blueprint: str,
    program: GraphProgram,
    memory: EvolutionaryMemory,
    timeout_sec: float = 60.0,
) -> dict:
    """
    Step 3 of PES: Summarizer extracts actionable structural insights and updates memory.
    """
    # 1. Update MAP-Elites
    is_elite = memory.map_elites.add(
        prog=program,
        girth=program.girth,
        diameter=program.diameter,
        bipartite=program.bipartite,
    )

    if program.is_counterexample:
        logger.info("🎉🎉🎉 COUNTEREXAMPLE CONFIRMED BY VERIFIER! 🎉🎉🎉")
        return {
            "counterexample": True,
            "lesson": "SUCCESS: Construction fully eliminates all 2^k cycles!",
            "is_elite": is_elite,
        }

    # 2. Extract cycle information from diagnostics
    diagnostic = program.diagnostic_trace
    witness = program.cycle_witness

    prompt = f"""You are the Chief Scientist & Reviewer in a LoongFlow PES agent attacking Erdős Problem #64.

THE PLANNER PROPOSED THIS BLUEPRINT:
{blueprint}

THE RUST VERIFIER RETURNED THIS DIAGNOSTIC TRACE:
- Fitness: {program.fitness:.1f}
- Is Cubic: {program.all_cubic}
- Girth: {program.girth}
- Diameter: {program.diameter}
- Bipartite: {program.bipartite}
- Diagnostics: {diagnostic}
- Collision Path (Cycle Witness): {witness}

YOUR TASK (ABDUCTIVE REFLECTION):
1. Identify WHY the algebraic construction failed to eliminate this cycle.
2. Formulate ONE concise, generalizable mathematical lesson that the Planner can use in future blueprints to avoid this failure.

OUTPUT FORMAT (Respond with a valid JSON object ONLY):
{{
  "family": "Brief name of the mathematical family tested",
  "failure_mode": "Brief phrase describing why the cycle formed",
  "lesson": "Actionable, 1-2 sentence mathematical rule for future planners",
  "cycle_len": {len(witness) if witness else 0}
}}
"""

    logger.info("Calling LoongFlow Summarizer (agy -p) for abductive reflection...")
    try:
        raw_summary = call_agy_prompt(prompt, timeout_sec=timeout_sec)
        # Parse JSON
        start_idx = raw_summary.find("{")
        end_idx = raw_summary.rfind("}") + 1
        if start_idx != -1 and end_idx != -1:
            data = json.loads(raw_summary[start_idx:end_idx])
            memory.add_lesson(
                family=data.get("family", "Unknown Family"),
                failure_mode=data.get("failure_mode", "Cycle Collision"),
                lesson=data.get("lesson", "Avoid symmetric resonances."),
                cycle_len=data.get("cycle_len", len(witness) if witness else 0),
            )
            return {
                "counterexample": False,
                "lesson": data.get("lesson"),
                "is_elite": is_elite,
                "data": data,
            }
    except Exception as e:
        logger.warning("Summarizer failed to parse structured JSON from LLM: %s", e)

    # Fallback lesson
    fallback = f"Girth {program.girth} reached, but cycle collision occurred on path {witness[:6] if witness else []}..."
    memory.add_lesson(
        family="Exploration",
        failure_mode="Cycle Collision",
        lesson=fallback,
        cycle_len=len(witness) if witness else 0,
    )
    return {
        "counterexample": False,
        "lesson": fallback,
        "is_elite": is_elite,
    }
