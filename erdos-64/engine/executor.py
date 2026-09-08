"""
Executor module for LoongFlow PES architecture.
Translates the Planner's blueprint into executable Python code and verifies via Rust verifier_64.
"""

import re
import logging
import subprocess
try:
    from .island import GraphProgram
    from .evaluator import evaluate_graph_code
except ImportError:
    from island import GraphProgram
    from evaluator import evaluate_graph_code

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

def extract_python_code(raw_output: str) -> str:
    match = re.search(r"```python\s*\n(.*?)\n```", raw_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    match_any = re.search(r"```\s*\n(.*?)\n```", raw_output, re.DOTALL)
    if match_any:
        return match_any.group(1).strip()

    if "def generate_graph" in raw_output:
        lines = raw_output.splitlines()
        code_lines = []
        capturing = False
        for line in lines:
            if line.startswith("def generate_graph") or line.startswith("import "):
                capturing = True
            if capturing:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines).strip()

    return raw_output.strip()

def execute_plan(
    blueprint: str,
    parent: GraphProgram,
    test_ns: list[int] = [32, 34, 36],
    timeout_sec: float = 60.0,
) -> tuple[GraphProgram, str]:
    """
    Step 2 of PES: Executor implements the blueprint into Python code and evaluates it.
    """
    prompt = f"""You are the Software Engineer & Implementer in a LoongFlow PES agent attacking Erdős Problem #64.

THE PLANNER HAS PRODUCED THE FOLLOWING STRATEGIC MATHEMATICAL BLUEPRINT:
======================================================================
{blueprint}
======================================================================

YOUR TASK:
Implement the Python function `def generate_graph(n: int) -> dict:` adhering strictly to the blueprint above.

CONSTRAINTS:
1. Return format must be: `{{'n': n, 'adj': [[neighbor_0, neighbor_1, ...], ...]}}` (0-indexed adjacency list).
2. DYNAMIC SCALING: The function must accept ANY even integer `n` passed as input (e.g. `n = 32, 34, 36`), and create a graph with EXACTLY `n` vertices (indices `0` to `n-1`).
3. STRICT 3-REGULARITY: EVERY vertex `i` (from 0 to `n-1`) must have `len(adj[i]) == 3`.
4. SIMPLICITY: Ensure no self-loops (`i not in adj[i]`) and no multi-edges (`len(set(adj[i])) == 3`). If `u in adj[v]`, then `v in adj[u]`.
5. Keep the function self-contained using standard Python libraries only.

Output ONLY the Python code in a ```python ... ``` block. No markdown explanation outside the code block.
"""

    logger.info("Calling LoongFlow Executor (agy -p)...")
    raw_code = call_agy_prompt(prompt, timeout_sec=timeout_sec)
    code = extract_python_code(raw_code)

    logger.info("Evaluating synthesized code across test sizes %s via Rust verifier_64...", test_ns)
    program = evaluate_graph_code(
        code=code,
        program_id=f"pes_{parent.id}_child",
        test_ns=test_ns,
        parent_id=parent.id,
    )

    return program, code
