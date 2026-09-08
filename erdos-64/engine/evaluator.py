"""
Evaluator for Erdős Problem #64:
Executes candidate Python graph generator functions in a sandboxed subprocess (5s timeout),
pipes candidate graphs to the compiled Rust verifier binary (verifier_64.exe),
and calculates fitness based on cubic regularity and avoidance of 2^k cycles.
"""

import json
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

@dataclass
class GraphEvaluationDetail:
    n: int
    counterexample: bool
    is_cubic: bool
    min_degree: int
    max_degree: int
    edges: int
    girth: int
    diameter: int
    bipartite: bool
    has_c4: bool
    has_c8: bool
    has_c16: bool
    has_c32: bool
    power_of_two_cycle_count: int
    cycle_witness: list[int] | None = None
    diagnostic_trace: str = ""
    error: str | None = None

@dataclass
class GraphEvaluationResult:
    fitness: float
    is_counterexample: bool
    all_cubic: bool
    details: list[GraphEvaluationDetail]
    best_diagnostic: str = ""

def find_verifier_binary(project_root: Path | None = None) -> Path:
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent

    exe_suffix = ".exe" if sys.platform == "win32" else ""
    candidates = [
        project_root / "target" / "release" / f"verifier_64{exe_suffix}",
        project_root / "verifier" / "target" / "release" / f"verifier_64{exe_suffix}",
        project_root / "target" / "debug" / f"verifier_64{exe_suffix}",
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(f"Could not find compiled verifier_64 binary in: {[str(c) for c in candidates]}")

def run_candidate_for_n(code: str, n: int, timeout_sec: float = 5.0) -> dict:
    runner_script = f"""
import json
import sys

{code}

try:
    if 'generate_graph' not in globals():
        print(json.dumps({{'error': 'Function generate_graph(n) not defined'}}))
        sys.exit(1)
    res = generate_graph({n})
    if not isinstance(res, dict) or 'adj' not in res:
        print(json.dumps({{'error': 'generate_graph must return dict with adj'}}))
        sys.exit(1)
    print(json.dumps(res))
    sys.exit(0)
except Exception as e:
    print(json.dumps({{'error': str(e)}}))
    sys.exit(1)
"""
    proc = subprocess.run(
        [sys.executable, "-c", runner_script],
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    if proc.returncode != 0:
        err = "Subprocess exited with error"
        try:
            data = json.loads(proc.stdout)
            err = data.get("error", err)
        except Exception:
            if proc.stderr:
                err = proc.stderr.strip()
        raise RuntimeError(err)

    data = json.loads(proc.stdout)
    if "error" in data:
        raise RuntimeError(data["error"])
    return data

def verify_with_rust_binary(verifier_path: Path, graph_dict: dict) -> GraphEvaluationDetail:
    payload = json.dumps(graph_dict)
    proc = subprocess.run(
        [str(verifier_path)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15.0,
    )
    stdout = proc.stdout.strip()
    if not stdout:
        err = proc.stderr.strip() or "No output from verifier_64"
        return GraphEvaluationDetail(
            n=graph_dict.get("n", 0),
            counterexample=False,
            is_cubic=False,
            min_degree=0,
            max_degree=0,
            edges=0,
            girth=0,
            diameter=0,
            bipartite=False,
            has_c4=True,
            has_c8=True,
            has_c16=True,
            has_c32=True,
            power_of_two_cycle_count=4,
            diagnostic_trace="Process failed: " + err,
            error=err,
        )

    try:
        data = json.loads(stdout)
        return GraphEvaluationDetail(
            n=data.get("n", 0),
            counterexample=data.get("counterexample", False),
            is_cubic=data.get("is_cubic", False),
            min_degree=data.get("min_degree", 0),
            max_degree=data.get("max_degree", 0),
            edges=data.get("edges", 0),
            girth=data.get("girth", 0),
            diameter=data.get("diameter", 0),
            bipartite=data.get("bipartite", False),
            has_c4=data.get("has_c4", False),
            has_c8=data.get("has_c8", False),
            has_c16=data.get("has_c16", False),
            has_c32=data.get("has_c32", False),
            power_of_two_cycle_count=data.get("power_of_two_cycle_count", 0),
            cycle_witness=data.get("cycle_witness"),
            diagnostic_trace=data.get("diagnostic_trace", ""),
            error=None,
        )
    except Exception as e:
        return GraphEvaluationDetail(
            n=graph_dict.get("n", 0),
            counterexample=False,
            is_cubic=False,
            min_degree=0,
            max_degree=0,
            edges=0,
            girth=0,
            diameter=0,
            bipartite=False,
            has_c4=True,
            has_c8=True,
            has_c16=True,
            has_c32=True,
            power_of_two_cycle_count=4,
            diagnostic_trace=f"JSON decode error: {e}",
            error=f"JSON decode error: {e}",
        )

def evaluate_graph_candidate(
    code: str,
    test_ns: list[int] | None = None,
    verifier_path: Path | None = None,
    timeout_sec: float = 5.0,
) -> GraphEvaluationResult:
    if test_ns is None:
        test_ns = [24, 32]

    if verifier_path is None:
        verifier_path = find_verifier_binary()

    details: list[GraphEvaluationDetail] = []
    total_fitness = 0.0
    any_counterexample = False
    all_cubic = True
    best_diag = ""

    for n in test_ns:
        try:
            g_dict = run_candidate_for_n(code, n, timeout_sec=timeout_sec)
        except Exception as e:
            all_cubic = False
            details.append(
                GraphEvaluationDetail(
                    n=n,
                    counterexample=False,
                    is_cubic=False,
                    min_degree=0,
                    max_degree=0,
                    edges=0,
                    girth=0,
                    diameter=0,
                    bipartite=False,
                    has_c4=True,
                    has_c8=True,
                    has_c16=True,
                    has_c32=True,
                    power_of_two_cycle_count=4,
                    diagnostic_trace=str(e),
                    error=str(e),
                )
            )
            total_fitness -= 500.0
            continue

        detail = verify_with_rust_binary(verifier_path, g_dict)
        details.append(detail)

        if detail.diagnostic_trace and not best_diag:
            best_diag = detail.diagnostic_trace

        if detail.is_cubic:
            total_fitness += 500.0
        else:
            all_cubic = False
            total_fitness -= 200.0

        if not detail.has_c4:
            total_fitness += 300.0
        if not detail.has_c8:
            total_fitness += 200.0
        if not detail.has_c16:
            total_fitness += 100.0
        if not detail.has_c32:
            total_fitness += 50.0

        if detail.counterexample:
            any_counterexample = True
            total_fitness += 50000.0

    return GraphEvaluationResult(
        fitness=total_fitness,
        is_counterexample=any_counterexample,
        all_cubic=all_cubic,
        details=details,
        best_diagnostic=best_diag,
    )
