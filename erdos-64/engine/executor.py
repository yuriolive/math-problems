"""Executor stage of the LoongFlow PES loop.

Turns the planner's blueprint into a generator function, verifies it with the Rust
verifier, and optionally hands the graph to the CUDA swarm for local polishing.
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path

try:
    from .agy_client import call_agy_prompt, extract_python_code
    from .island import GraphProgram
    from .evaluator import (
        evaluate_graph_code,
        run_candidate_for_n,
        verify_with_rust_binary,
        find_verifier_binary,
        score_detail,
    )
except ImportError:  # direct script execution
    from agy_client import call_agy_prompt, extract_python_code
    from island import GraphProgram
    from evaluator import (
        evaluate_graph_code,
        run_candidate_for_n,
        verify_with_rust_binary,
        find_verifier_binary,
        score_detail,
    )

logger = logging.getLogger(__name__)


def find_gpu_swarm_binary() -> Path | None:
    root = Path(__file__).resolve().parent.parent
    exe = root / "cuda" / "swarm_64.exe"
    return exe if exe.is_file() else None


def adjacency_to_generator_code(n: int, adj: list[list[int]]) -> str:
    """Emits a generator that reproduces exactly this graph at this order.

    Used to make a GPU-polished graph a first-class, reproducible candidate. Without
    this the polished adjacency was thrown away and only its metadata was copied onto
    the pre-polish program, so a winning graph could not be regenerated.
    """
    return (
        "def generate_graph(n: int) -> dict:\n"
        f"    # Graph found by the CUDA swarm at n = {n}.\n"
        f"    adj = {adj!r}\n"
        f"    if n != {n}:\n"
        f"        raise ValueError('this candidate is only defined for n = {n}')\n"
        f"    return {{'n': {n}, 'adj': adj}}\n"
    )


def polish_with_gpu(
    graph_dict: dict,
    iterations: int = 5000,
    timeout_sec: float = 120.0,
    threads: int = 10240,
) -> dict | None:
    """Runs the CUDA swarm seeded with `graph_dict` and returns its best graph.

    The seed is passed through a temporary file rather than on the command line: a
    64-vertex adjacency list is several kilobytes and argv is a limited resource on
    Windows.
    """
    gpu_binary = find_gpu_swarm_binary()
    if not gpu_binary:
        return None

    n = graph_dict.get("n")
    if not n:
        return None

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump({"n": n, "adj": graph_dict.get("adj", [])}, fh)
            tmp_path = fh.name

        proc = subprocess.run(
            [
                str(gpu_binary), str(n), str(iterations),
                "--threads", str(threads),
                "--seed-file", tmp_path,
                "--json-only",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        # The binary exits 1 when it finds no counterexample, which is the normal case.
        if proc.returncode not in (0, 1):
            logger.warning("GPU swarm failed (exit %s): %s", proc.returncode, proc.stderr.strip()[:300])
            return None

        out = proc.stdout.strip()
        start, end = out.find("{"), out.rfind("}") + 1
        if start == -1 or end <= start:
            return None
        return json.loads(out[start:end])
    except Exception as e:
        logger.warning("GPU swarm polish encountered an error: %s", e)
        return None
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass


def execute_plan(
    blueprint: str,
    parent: GraphProgram | None,
    test_ns: list[int] | None = None,
    enable_gpu_polish: bool = True,
    timeout_sec: float = 60.0,
    count_cap: int = 1000,
) -> tuple[GraphProgram, str]:
    """PES stage 2: synthesize, verify, optionally polish on the GPU.

    Returns the best program found. If the GPU polish produces a strictly better
    graph, the returned program *is* that graph (code, fitness and details all
    describe the polished adjacency).
    """
    if test_ns is None:
        test_ns = [36, 38, 40]

    prompt = f"""You are the implementer in a LoongFlow PES agent attacking Erdős Problem #64.

THE PLANNER PRODUCED THIS BLUEPRINT:
======================================================================
{blueprint}
======================================================================

YOUR TASK:
Implement `def generate_graph(n: int) -> dict:` following the blueprint above.

CONSTRAINTS:
1. Return `{{'n': n, 'adj': [[neighbour, ...], ...]}}` with 0-indexed adjacency lists.
2. DYNAMIC SCALING: accept any even integer n (for example {', '.join(str(x) for x in test_ns)})
   and build a graph on exactly n vertices, indices 0 .. n-1.
3. STRICT 3-REGULARITY: every vertex i must satisfy len(adj[i]) == 3.
4. SIMPLICITY: no self-loops (i not in adj[i]), no multi-edges (len(set(adj[i])) == 3),
   and symmetry (u in adj[v] iff v in adj[u]).
5. CONNECTIVITY: return a connected graph. A disconnected cubic graph is never a new
   counterexample, because one of its components would already be a smaller one.
6. Self-contained, standard library only.

Output ONLY the Python code in a ```python ... ``` block.
"""

    logger.info("Calling LoongFlow Executor (agy -p)...")
    raw_code = call_agy_prompt(prompt, timeout_sec=timeout_sec)
    code = extract_python_code(raw_code)

    logger.info("Verifying synthesized code at n = %s via verifier_64...", test_ns)
    parent_id = parent.id if parent else "root"
    program = evaluate_graph_code(
        code=code,
        program_id=f"pes_{parent_id}_child",
        test_ns=test_ns,
        parent_id=parent_id,
        count_cap=count_cap,
    )

    if not (enable_gpu_polish and program.all_cubic and not program.is_counterexample):
        return program, code

    n_target = test_ns[0]
    try:
        raw_graph = run_candidate_for_n(code, n_target)
    except Exception as e:
        logger.warning("Could not regenerate the graph for GPU polish: %s", e)
        return program, code

    logger.info("Engaging the CUDA swarm on the candidate (n=%d)...", n_target)
    gpu_res = polish_with_gpu(raw_graph, iterations=5000)
    if not gpu_res or "adj" not in gpu_res:
        return program, code

    verifier_path = find_verifier_binary()
    polished_detail = verify_with_rust_binary(
        verifier_path, {"n": gpu_res["n"], "adj": gpu_res["adj"]}, count_cap=count_cap
    )
    polished_fitness = score_detail(polished_detail)

    # Compare like with like: the pre-polish score at the same order.
    baseline = next((d for d in program.details if d.get("n") == n_target), None)
    baseline_fitness = float(baseline.get("fitness", program.fitness)) if baseline else program.fitness
    if baseline is not None and "fitness" not in baseline:
        baseline_fitness = program.fitness / max(1, len(program.details))

    logger.info(
        "GPU polish: cubic=%s connected=%s counts=%s counterexample=%s (fitness %.1f vs %.1f)",
        polished_detail.is_cubic, polished_detail.connected, polished_detail.counts,
        polished_detail.counterexample, polished_fitness, baseline_fitness,
    )

    if not polished_detail.counterexample and polished_fitness <= baseline_fitness:
        return program, code

    # Adopt the polished graph as a real, reproducible candidate.
    polished_code = adjacency_to_generator_code(gpu_res["n"], gpu_res["adj"])
    polished_program = GraphProgram(
        id=f"{program.id}_gpu_polished",
        code=polished_code,
        fitness=polished_fitness,
        is_counterexample=polished_detail.counterexample,
        all_cubic=polished_detail.is_cubic,
        island_id=program.island_id,
        generation=program.generation,
        parent_id=program.id,
        details=[{
            "n": polished_detail.n,
            "counterexample": polished_detail.counterexample,
            "is_cubic": polished_detail.is_cubic,
            "girth": polished_detail.girth,
            "diameter": polished_detail.diameter,
            "connected": polished_detail.connected,
            "components": polished_detail.components,
            "bipartite": polished_detail.bipartite,
            "checked_lengths": polished_detail.checked_lengths,
            "counts": polished_detail.counts,
            "has_c4": polished_detail.has_c4,
            "has_c8": polished_detail.has_c8,
            "has_c16": polished_detail.has_c16,
            "has_c32": polished_detail.has_c32,
            "has_c64": polished_detail.has_c64,
            "power_of_two_cycle_count": polished_detail.power_of_two_cycle_count,
            "diagnostic_trace": polished_detail.diagnostic_trace,
            "error": None,
            "fitness": polished_fitness,
        }],
        girth=polished_detail.girth,
        diameter=polished_detail.diameter,
        bipartite=polished_detail.bipartite,
        connected=polished_detail.connected,
        pow2_cycle_total=sum(polished_detail.counts.values()),
        diagnostic_trace=f"[GPU swarm polish] {polished_detail.diagnostic_trace}",
        cycle_witness=polished_detail.cycle_witness,
    )

    if polished_detail.counterexample:
        logger.info("Verifier reports a counterexample after GPU polish at n=%d.", gpu_res["n"])

    return polished_program, polished_code
