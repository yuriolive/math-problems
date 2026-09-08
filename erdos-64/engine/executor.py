"""
Executor module for LoongFlow PES architecture.
Translates the Planner's blueprint into executable Python code and verifies via Rust verifier_64.
Integrates RTX 4070 Super CUDA Swarm as a Micro-Finisher local optimizer.
"""

import re
import json
import logging
import subprocess
from pathlib import Path
try:
    from .island import GraphProgram
    from .evaluator import evaluate_graph_code, run_candidate_for_n, verify_with_rust_binary, find_verifier_binary
except ImportError:
    from island import GraphProgram
    from evaluator import evaluate_graph_code, run_candidate_for_n, verify_with_rust_binary, find_verifier_binary

logger = logging.getLogger(__name__)

def find_gpu_swarm_binary() -> Path | None:
    root = Path(__file__).resolve().parent.parent
    exe = root / "cuda" / "swarm_64.exe"
    if exe.is_file():
        return exe
    return None

def polish_with_gpu(graph_dict: dict, iterations: int = 5000, timeout_sec: float = 15.0) -> dict | None:
    """
    Submits a candidate graph directly into RTX 4070 Super VRAM.
    10,240 threads anneal around the seed graph to extinguish residual cycles.
    """
    gpu_binary = find_gpu_swarm_binary()
    if not gpu_binary:
        return None

    n = graph_dict.get("n", 32)
    payload = json.dumps(graph_dict)
    cmd = [str(gpu_binary), str(n), str(iterations), "--seed-json", payload, "--json-only"]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        if proc.returncode in (0, 1):
            out = proc.stdout.strip()
            start = out.find("{")
            end = out.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(out[start:end])
    except Exception as e:
        logger.warning("GPU swarm polish encountered error: %s", e)
    return None

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
    enable_gpu_polish: bool = True,
    timeout_sec: float = 60.0,
) -> tuple[GraphProgram, str]:
    """
    Step 2 of PES: Executor implements the blueprint into Python code, evaluates in Rust,
    and applies GPU Swarm Annealing to polish boundary seams.
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

    # Hybrid Polish: If candidate is strictly cubic and has not yet achieved counterexample status,
    # engage RTX 4070 Super CUDA Swarm to micro-anneal residual cycles
    if enable_gpu_polish and program.all_cubic and not program.is_counterexample:
        n_target = test_ns[0]
        try:
            raw_graph = run_candidate_for_n(code, n_target)
            logger.info("⚡ Engaging RTX 4070 Super CUDA Swarm Finisher on candidate (n=%d, 5000 iters)...", n_target)
            gpu_res = polish_with_gpu(raw_graph, iterations=5000)
            if gpu_res and "adj" in gpu_res:
                verifier_path = find_verifier_binary()
                detail = verify_with_rust_binary(verifier_path, gpu_res)
                logger.info(
                    "⚡ GPU Swarm Polish Result: Best Energy=%s | Girth=%d | C4=%s | C8=%s | C16=%s | Counterexample=%s",
                    gpu_res.get("best_energy"), detail.girth, detail.has_c4, detail.has_c8, detail.has_c16, detail.counterexample
                )
                if detail.counterexample or (not detail.has_c4 and (not detail.has_c8 or program.girth < detail.girth)):
                    program.diagnostic_trace = f"[RTX 4070 Super Swarm Polish]: {detail.diagnostic_trace}"
                    program.cycle_witness = detail.cycle_witness
                    program.girth = max(program.girth, detail.girth)
                    program.is_counterexample = detail.counterexample
                    if detail.counterexample:
                        program.fitness += 50000.0
                        logger.info("🎉🎉🎉 COUNTEREXAMPLE CONFIRMED VIA HYBRID GPU POLISH! 🎉🎉🎉")
        except Exception as e:
            logger.warning("Hybrid GPU polish step encountered exception: %s", e)

    return program, code
