"""Evaluator for Erdős Problem #64.

Runs candidate Python graph generators in a sandboxed subprocess, pipes the resulting
graphs to the compiled Rust verifier, and turns the verifier's report into a fitness.

Fitness is LEXICOGRAPHIC in the same sense as the CUDA energy: clearing a shallower
cycle length always beats any improvement at a deeper one. The old scoring handed out
credit for `not has_c8` / `not has_c16` even when those tiers had never been computed,
which rewarded candidates for cycle classes nobody had checked.
"""

import json
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass, field

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Fitness constants.
CUBIC_BONUS = 500.0
NON_CUBIC_PENALTY = -200.0
GENERATOR_FAILURE_PENALTY = -500.0
DISCONNECTED_PENALTY = -100.0
TIER_BONUS = 1000.0            # per power-of-two length that is completely absent
COUNT_PENALTY_CAP = 999.0      # gradient inside the first violated tier
COUNTEREXAMPLE_BONUS = 50000.0


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
    connected: bool = True
    components: int = 1
    bipartite: bool = False
    checked_lengths: list[int] = field(default_factory=list)
    # Exact (or capped) count per power-of-two length, e.g. {4: 0, 8: 0, 16: 424}.
    counts: dict[int, int] = field(default_factory=dict)
    capped: dict[int, bool] = field(default_factory=dict)
    has_c4: bool = False
    has_c8: bool = False
    has_c16: bool = False
    has_c32: bool = False
    has_c64: bool = False
    power_of_two_cycle_count: int = 0
    cycle_witness: list[int] | None = None
    diagnostic_trace: str = ""
    error: str | None = None

    @property
    def clean_tiers(self) -> int:
        """How many power-of-two lengths are clean, counting from the shortest.

        This is a PREFIX count and stops at the first violated length. Counting every
        clean tier regardless of order would credit a graph for having no C32 while it
        still has a C8, which inverts the ordering the search needs: absence of a
        short cycle must always outweigh absence of a longer one.
        """
        clean = 0
        for length in sorted(self.checked_lengths):
            if self.counts.get(length, 1) != 0:
                break
            clean += 1
        return clean

    @property
    def first_violated(self) -> tuple[int, int] | None:
        """(length, count) of the shortest power-of-two cycle present, if any."""
        for length in sorted(self.checked_lengths):
            c = self.counts.get(length, 0)
            if c > 0:
                return (length, c)
        return None


@dataclass
class GraphEvaluationResult:
    fitness: float
    is_counterexample: bool
    all_cubic: bool
    details: list[GraphEvaluationDetail]
    best_diagnostic: str = ""


def _failed_detail(n: int, error: str) -> GraphEvaluationDetail:
    """A detail record for a candidate that could not be evaluated at all.

    Nothing was verified, so no cycle length is recorded as absent and no tier bonus
    can be earned. `counts` stays empty rather than claiming zeros.
    """
    return GraphEvaluationDetail(
        n=n,
        counterexample=False,
        is_cubic=False,
        min_degree=0,
        max_degree=0,
        edges=0,
        girth=0,
        diameter=0,
        connected=False,
        components=0,
        checked_lengths=[],
        counts={},
        diagnostic_trace=error,
        error=error,
    )


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
    raise FileNotFoundError(
        "Could not find a compiled verifier_64 binary (run `make build-verifier`). "
        f"Searched: {[str(c) for c in candidates]}"
    )


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


def verify_with_rust_binary(
    verifier_path: Path,
    graph_dict: dict,
    count_cap: int = 1000,
    timeout_sec: float = 120.0,
) -> GraphEvaluationDetail:
    """Runs the Rust verifier. `count_cap > 1` asks for counts, not just existence."""
    payload = json.dumps({"n": graph_dict.get("n"), "adj": graph_dict.get("adj")})
    args = [str(verifier_path)]
    if count_cap > 1:
        args += ["--full", "--cap", str(count_cap)]

    try:
        proc = subprocess.run(
            args, input=payload, capture_output=True, text=True, timeout=timeout_sec
        )
    except subprocess.TimeoutExpired:
        return _failed_detail(graph_dict.get("n", 0), f"verifier timed out after {timeout_sec}s")

    stdout = proc.stdout.strip()
    if not stdout:
        return _failed_detail(
            graph_dict.get("n", 0),
            "Verifier produced no output: " + (proc.stderr.strip() or "unknown error"),
        )

    try:
        data = json.loads(stdout)
    except Exception as e:
        return _failed_detail(graph_dict.get("n", 0), f"JSON decode error: {e}")

    counts = {c["length"]: c["count"] for c in data.get("counts", [])}
    capped = {c["length"]: c["capped"] for c in data.get("counts", [])}

    return GraphEvaluationDetail(
        n=data.get("n", 0),
        counterexample=data.get("counterexample", False),
        is_cubic=data.get("is_cubic", False),
        min_degree=data.get("min_degree", 0),
        max_degree=data.get("max_degree", 0),
        edges=data.get("edges", 0),
        girth=data.get("girth", 0),
        diameter=data.get("diameter", 0),
        connected=data.get("connected", True),
        components=data.get("components", 1),
        bipartite=data.get("bipartite", False),
        checked_lengths=data.get("checked_lengths", []),
        counts=counts,
        capped=capped,
        has_c4=data.get("has_c4", False),
        has_c8=data.get("has_c8", False),
        has_c16=data.get("has_c16", False),
        has_c32=data.get("has_c32", False),
        has_c64=data.get("has_c64", False),
        power_of_two_cycle_count=data.get("power_of_two_cycle_count", 0),
        cycle_witness=data.get("cycle_witness"),
        diagnostic_trace=data.get("diagnostic_trace", ""),
        error=None,
    )


def score_detail(detail: GraphEvaluationDetail) -> float:
    """Fitness for one (candidate, n) pair.

    Credit is only ever given for a cycle length the verifier actually checked, and
    a shallower clean tier always dominates a deeper improvement.
    """
    if detail.error is not None:
        return GENERATOR_FAILURE_PENALTY

    score = CUBIC_BONUS if detail.is_cubic else NON_CUBIC_PENALTY

    # A disconnected cubic graph is never a *new* counterexample: one of its
    # components would already be a smaller one.
    if not detail.connected:
        score += DISCONNECTED_PENALTY

    score += TIER_BONUS * detail.clean_tiers

    violated = detail.first_violated
    if violated is not None:
        _, count = violated
        score -= min(float(count), COUNT_PENALTY_CAP)

    if detail.counterexample:
        score += COUNTEREXAMPLE_BONUS

    return score


def evaluate_graph_candidate(
    code: str,
    test_ns: list[int] | None = None,
    verifier_path: Path | None = None,
    timeout_sec: float = 5.0,
    count_cap: int = 1000,
) -> GraphEvaluationResult:
    if test_ns is None:
        test_ns = [32, 36]

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
            detail = _failed_detail(n, str(e))
            details.append(detail)
            total_fitness += score_detail(detail)
            all_cubic = False
            continue

        detail = verify_with_rust_binary(verifier_path, g_dict, count_cap=count_cap)
        details.append(detail)
        total_fitness += score_detail(detail)

        if detail.diagnostic_trace and not best_diag:
            best_diag = detail.diagnostic_trace
        if not detail.is_cubic:
            all_cubic = False
        if detail.counterexample:
            any_counterexample = True

    return GraphEvaluationResult(
        fitness=total_fitness,
        is_counterexample=any_counterexample,
        all_cubic=all_cubic,
        details=details,
        best_diagnostic=best_diag,
    )


def evaluate_graph_code(
    code: str,
    program_id: str = "prog",
    test_ns: list[int] | None = None,
    parent_id: str | None = None,
    island_id: int = 0,
    generation: int = 0,
    timeout_sec: float = 5.0,
    count_cap: int = 1000,
):
    try:
        from .program import GraphProgram
    except ImportError:
        from program import GraphProgram

    eval_res = evaluate_graph_candidate(
        code, test_ns=test_ns, timeout_sec=timeout_sec, count_cap=count_cap
    )

    girth = 0
    diameter = 0
    bipartite = False
    connected = True
    cycle_witness = None
    total_pow2_cycles = 0

    for d in eval_res.details:
        girth = max(girth, d.girth)
        diameter = max(diameter, d.diameter)
        bipartite = bipartite or d.bipartite
        connected = connected and d.connected
        if d.cycle_witness and not cycle_witness:
            cycle_witness = d.cycle_witness
        total_pow2_cycles += sum(d.counts.values())

    return GraphProgram(
        id=program_id,
        code=code,
        fitness=eval_res.fitness,
        is_counterexample=eval_res.is_counterexample,
        all_cubic=eval_res.all_cubic,
        island_id=island_id,
        generation=generation,
        parent_id=parent_id,
        details=[
            {
                "n": d.n,
                "counterexample": d.counterexample,
                "is_cubic": d.is_cubic,
                "min_degree": d.min_degree,
                "max_degree": d.max_degree,
                "edges": d.edges,
                "girth": d.girth,
                "diameter": d.diameter,
                "connected": d.connected,
                "components": d.components,
                "bipartite": d.bipartite,
                "checked_lengths": d.checked_lengths,
                "counts": d.counts,
                "has_c4": d.has_c4,
                "has_c8": d.has_c8,
                "has_c16": d.has_c16,
                "has_c32": d.has_c32,
                "has_c64": d.has_c64,
                "power_of_two_cycle_count": d.power_of_two_cycle_count,
                "diagnostic_trace": d.diagnostic_trace,
                "error": d.error,
            }
            for d in eval_res.details
        ],
        girth=girth,
        diameter=diameter,
        bipartite=bipartite,
        connected=connected,
        pow2_cycle_total=total_pow2_cycles,
        diagnostic_trace=eval_res.best_diagnostic,
        cycle_witness=cycle_witness,
    )
