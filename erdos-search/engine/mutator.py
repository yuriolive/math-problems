"""
Mutator module for FunSearch using Antigravity CLI (`agy -p`).
Zero external API keys required; leverages the local authenticated session.
"""

import re
import subprocess
import logging

logger = logging.getLogger(__name__)

def call_agy_prompt(prompt: str, timeout_sec: float = 60.0) -> str:
    """
    Executes `agy -p "<prompt>"` via subprocess.run to call the Antigravity LLM.
    """
    cmd = ["agy", "-p", prompt]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout_sec,
    )
    return result.stdout

def mutate_with_agy(prompt: str, timeout_sec: float = 60.0) -> str:
    """
    Invokes Antigravity CLI non-interactively using existing authenticated session.
    Extracts and returns the Python code block.
    """
    raw_output = call_agy_prompt(prompt, timeout_sec=timeout_sec)

    # 1. Look for ```python\n ... \n```
    match = re.search(r"```python\s*\n(.*?)\n```", raw_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 2. Look for any ```\n ... \n```
    match_any = re.search(r"```\s*\n(.*?)\n```", raw_output, re.DOTALL)
    if match_any:
        return match_any.group(1).strip()

    # 3. Fallback: if 'def generate_set' is directly in the output
    if "def generate_set" in raw_output:
        lines = raw_output.splitlines()
        code_lines = []
        capturing = False
        for line in lines:
            if line.startswith("def generate_set") or line.startswith("import "):
                capturing = True
            if capturing:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines).strip()

    return raw_output.strip()

def build_mutation_prompt(
    parent_code: str,
    parent_ratio: float,
    parent_valid: bool,
    island_id: int,
    generation: int,
) -> str:
    """
    Constructs a targeted prompt guiding the LLM to evolve the mathematical heuristic.
    """
    prompt = f"""You are a combinatorial mathematician and algorithms expert working on Erdős Problem #1 (Distinct Subset Sums / Bohman's Bound).

The objective is to produce an n-element set of positive integers A = {{a_1 < a_2 < ... < a_n}} such that all 2^n subset sums are strictly distinct, minimizing the ratio R = max(A) / (2^n).
Target to beat: Bohman's bound R < 0.22002.
Current parent program ratio: {parent_ratio:.6f} (valid subset sums: {parent_valid}).
Island: {island_id}, Generation: {generation}.

Here is the current Python generator program:
```python
{parent_code}
```

Task:
Propose a mutated or improved Python function `def generate_set(n: int) -> list[int]:` that:
1. Returns an n-element list of strictly positive integers [a_1, a_2, ..., a_n].
2. Ensures all 2^n subset sums remain strictly distinct (no two subsets sum to the same value).
3. Achieves an even lower ratio R = max(A) / 2^n, pushing towards or beating Bohman's constant 0.22002.
4. You may explore:
   - Modifications to Conway-Guy recurrence u_{{k+1}} = 2*u_k - u_{{k-r_k}} with refined indexing r_k or offset compressions.
   - Bohman's randomized or deterministic greedy perturbations.
   - Difference-set pruning and greedy insertion.
   - Combining sequence differences with modular adjustments.

Output ONLY the Python code enclosed in a ```python ... ``` block. Do not include markdown commentary outside the block.
"""
    return prompt
