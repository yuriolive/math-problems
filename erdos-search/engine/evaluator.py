"""
Evaluator module:
Executes candidate Python generator functions in a sandboxed subprocess with a 5s timeout,
pipes generated sets into the compiled Rust verifier binary,
and computes a composite fitness score.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any

BOHMAN_CONSTANT = 0.22002

@dataclass
class EvaluationDetail:
    n: int
    valid: bool
    max_val: int
    ratio: float
    beats_bohman: bool
    collision: list[int] | None
    error: str | None = None

@dataclass
class EvaluationResult:
    fitness: float
    best_ratio: float
    beats_bohman: bool
    all_valid: bool
    details: list[EvaluationDetail]
    error_message: str | None = None

def find_verifier_binary(project_root: Path | None = None) -> Path:
    """Finds the compiled Rust verifier binary."""
    if project_root is None:
        # Default to parent directory of engine/
        project_root = Path(__file__).resolve().parent.parent

    exe_suffix = ".exe" if sys.platform == "win32" else ""
    candidates = [
        project_root / "target" / "release" / f"verifier{exe_suffix}",
        project_root / "verifier" / "target" / "release" / f"verifier{exe_suffix}",
        project_root / "target" / "debug" / f"verifier{exe_suffix}",
        project_root / "verifier" / "target" / "debug" / f"verifier{exe_suffix}",
    ]

    for p in candidates:
        if p.is_file():
            return p

    raise FileNotFoundError(
        f"Could not find compiled verifier binary. Searched in: {[str(c) for c in candidates]}. "
        "Please run 'cargo build --release' first."
    )

def run_candidate_for_n(code: str, n: int, timeout_sec: float = 5.0) -> list[int]:
    """
    Safely executes candidate code in a sandboxed subprocess to generate set for n.
    """
    runner_script = f"""
import json
import sys

{code}

try:
    if 'generate_set' not in globals():
        print(json.dumps({{'error': 'Function generate_set(n) not defined'}}))
        sys.exit(1)
    res = generate_set({n})
    if not isinstance(res, (list, tuple)):
        print(json.dumps({{'error': 'generate_set did not return a list or tuple'}}))
        sys.exit(1)
    # Ensure positive integers
    res = [int(x) for x in res]
    print(json.dumps({{'set': res}}))
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
    return data.get("set", [])

def verify_with_rust_binary(verifier_path: Path, n: int, candidate_set: list[int]) -> EvaluationDetail:
    """
    Pipes candidate set into the compiled Rust binary and parses the strict JSON output.
    """
    payload = json.dumps({"n": n, "set": candidate_set})
    proc = subprocess.run(
        [str(verifier_path)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30.0,
    )

    stdout = proc.stdout.strip()
    if not stdout:
        err = proc.stderr.strip() or "No output from Rust verifier"
        return EvaluationDetail(
            n=n,
            valid=False,
            max_val=0,
            ratio=1.0,
            beats_bohman=False,
            collision=None,
            error=err,
        )

    try:
        data = json.loads(stdout)
        return EvaluationDetail(
            n=data.get("n", n),
            valid=data.get("valid", False),
            max_val=data.get("max_val", 0),
            ratio=data.get("ratio", 1.0),
            beats_bohman=data.get("beats_bohman", False),
            collision=data.get("collision"),
            error=None,
        )
    except json.JSONDecodeError as e:
        return EvaluationDetail(
            n=n,
            valid=False,
            max_val=0,
            ratio=1.0,
            beats_bohman=False,
            collision=None,
            error=f"JSON decode error: {e}, stdout was: {stdout}",
        )

def evaluate_candidate(
    code: str,
    test_ns: list[int] | None = None,
    verifier_path: Path | None = None,
    timeout_sec: float = 5.0,
) -> EvaluationResult:
    """
    Evaluates a candidate code string across benchmark n values.
    Returns composite fitness and evaluation metrics.
    """
    if test_ns is None:
        test_ns = [15, 20, 22, 24]

    if verifier_path is None:
        verifier_path = find_verifier_binary()

    details: list[EvaluationDetail] = []
    total_fitness = 0.0
    best_ratio = 1.0
    any_beats_bohman = False
    all_valid = True

    for n in test_ns:
        try:
            candidate_set = run_candidate_for_n(code, n, timeout_sec=timeout_sec)
        except subprocess.TimeoutExpired:
            all_valid = False
            details.append(
                EvaluationDetail(
                    n=n,
                    valid=False,
                    max_val=0,
                    ratio=1.0,
                    beats_bohman=False,
                    collision=None,
                    error=f"Timeout after {timeout_sec}s",
                )
            )
            total_fitness -= 200.0
            continue
        except Exception as e:
            all_valid = False
            details.append(
                EvaluationDetail(
                    n=n,
                    valid=False,
                    max_val=0,
                    ratio=1.0,
                    beats_bohman=False,
                    collision=None,
                    error=str(e),
                )
            )
            total_fitness -= 200.0
            continue

        detail = verify_with_rust_binary(verifier_path, n, candidate_set)
        details.append(detail)

        if detail.valid:
            best_ratio = min(best_ratio, detail.ratio)
            # Base validity bonus
            step_fitness = 1000.0
            # Higher fitness for smaller ratio
            step_fitness += (1.0 - detail.ratio) * 1000.0
            if detail.beats_bohman:
                step_fitness += 5000.0
                any_beats_bohman = True
            total_fitness += step_fitness
        else:
            all_valid = False
            total_fitness -= 100.0

    return EvaluationResult(
        fitness=total_fitness,
        best_ratio=best_ratio,
        beats_bohman=any_beats_bohman,
        all_valid=all_valid,
        details=details,
    )
