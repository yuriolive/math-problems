"""
Mutator module for Erdős Problem #64 using Antigravity CLI (`agy -p`).
Zero external API keys required.
"""

import re
import subprocess
import logging

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
    return result.stdout

def mutate_with_agy(prompt: str, timeout_sec: float = 60.0) -> str:
    raw_output = call_agy_prompt(prompt, timeout_sec=timeout_sec)

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

def build_graph_mutation_prompt(
    parent_code: str,
    parent_fitness: float,
    island_id: int,
    generation: int,
) -> str:
    prompt = f"""You are an extremal graph theory mathematician attacking Erdős Problem #64 (The Erdős–Gyárfás Conjecture).

The objective is to find a counterexample: a 3-regular (cubic) graph with NO simple cycles of length 2^k (no C4, no C8, no C16, no C32).
Current parent fitness: {parent_fitness:.1f}.
Island: {island_id}, Generation: {generation}.

Here is the current generator function:
```python
{parent_code}
```

Task:
Propose an improved Python function `def generate_graph(n: int) -> dict:` that:
1. Returns `{{'n': n, 'adj': [[neighbor_indices], ...]}}`.
2. Strictly ensures EVERY vertex has degree exactly 3.
3. Strategically avoids creating cycles of length 4, 8, 16, and 32!
4. You may explore:
   - Cayley graphs on non-abelian groups (e.g., A_4, S_4, alternating groups) with carefully chosen 3 generators.
   - Voltage graph lifts / permutation covers.
   - Generalized Petersen GP(n/2, k) variations or I-graphs.
   - Chord-exchange networks avoiding even cycle resonances.
   - Snark constructions (like Blanuša snarks, Flower snarks).

Output ONLY the Python code in a ```python ... ``` block. Do not include markdown commentary outside the block.
"""
    return prompt
