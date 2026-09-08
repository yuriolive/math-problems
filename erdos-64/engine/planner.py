"""
Planner module for LoongFlow PES architecture.
Generates an explicit strategic mathematical blueprint BEFORE code synthesis.
"""

import logging
import subprocess
try:
    from .pes_memory import EvolutionaryMemory
    from .island import GraphProgram
except ImportError:
    from pes_memory import EvolutionaryMemory
    from island import GraphProgram

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

def generate_plan(
    parent: GraphProgram,
    memory: EvolutionaryMemory,
    target_n: int = 32,
    timeout_sec: float = 60.0,
) -> str:
    """
    Step 1 of PES: Planner formulates a concrete mathematical hypothesis.
    """
    recent_lessons = memory.get_recent_lessons(k=5)
    elites_summary = memory.map_elites.summary()

    prompt = f"""You are the Lead Theoretical Mathematician in a LoongFlow PES agent attacking Erdős Problem #64 (The Erdős–Gyárfás Conjecture).

OBJECTIVE:
Find a 3-regular (cubic) graph with NO cycles of length 2^k (no C4, no C8, no C16, no C32).
The construction MUST be parameterized by the target vertex count `n` (which is even, e.g. n={target_n}).

CURRENT STATE:
- Parent Fitness: {parent.fitness:.1f} (Cubic: {parent.all_cubic}, Girth: {parent.girth})
- Current MAP-Elites Coverage:
{elites_summary}

PERSISTENT EXPERIENTIAL MEMORY (Lessons Learned from Past Failures):
{recent_lessons}

PARENT GENERATOR CODE:
```python
{parent.code}
```

TASK FOR PLANNER:
Do NOT write Python code yet. Formulate an explicit, rigorous MATHEMATICAL BLUEPRINT for the Executor.
Address:
1. HYPOTHESIS: What mathematical construction family should we construct?
   The construction MUST scale to the requested `n` (e.g. n={target_n}) using modular arithmetic over Z_n, bipartite/2-factor pairings with m = n // 2, or affine chord permutations pi(x) = ax + b (mod n).
2. ANTI-CYCLE INSULATION: How does this specific algebraic structure mathematically break the symmetries that create C4, C8, and C16?
3. EXACT CONSTRUCTION SPECIFICATION: Outline the step-by-step algorithm for the Executor to implement for arbitrary even `n`.

Keep your response concise, structured, and focused purely on the mathematical blueprint.
"""

    logger.info("Calling LoongFlow Planner (agy -p)...")
    plan = call_agy_prompt(prompt, timeout_sec=timeout_sec)
    return plan
