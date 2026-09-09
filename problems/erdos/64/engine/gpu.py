"""Driving the CUDA swarm binary and turning its output back into a candidate.

The three helpers here are the whole non-LLM half of what used to be the PES loop's
executor stage: find the binary, run it seeded with a graph, and emit a generator that
reproduces the polished result exactly. Nothing here evaluates or scores -- that is
`engine.evaluator`, which owns the compiled verifier.
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path

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
