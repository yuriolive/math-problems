"""
Z3 SAT / SMT Solver for Erdős Problem #64.
Finds minimal counterexample graphs avoiding 2^k cycles.
Incorporates Andrew Bisch's formally verified Lean 4 theorems (EGC.lean):
- 2/3 cubic density: |V_3| >= (2/3)|V|
- Independence of higher degrees: vertices of degree >= 4 form an independent set
- Domination: every vertex has a neighbor of degree exactly 3
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import z3

def solve_erdos_64(
    n: int = 14,
    strictly_cubic: bool = True,
    avoid_c4: bool = True,
    avoid_c8: bool = True,
    timeout_sec: float = 60.0,
):
    mode_str = "Strictly Cubic (d=3)" if strictly_cubic else "General Minimal Counterexample (Bisch Bounds)"
    print(f"=== Z3 SAT Solver for Erdős #64 on n={n} vertices ===")
    print(f"Mode: {mode_str} | Timeout: {timeout_sec}s")

    s = z3.Solver()
    s.set("timeout", int(timeout_sec * 1000))

    # Edge boolean variables
    e = {}
    for u in range(n):
        for v in range(u + 1, n):
            e[(u, v)] = z3.Bool(f"e_{u}_{v}")
            e[(v, u)] = e[(u, v)]

    # Incident edge lists
    incident_sums = []
    for u in range(n):
        incident = [z3.If(e[(u, v)], 1, 0) for v in range(n) if v != u]
        incident_sums.append(z3.Sum(incident))

    # 1. Degree Constraints
    if strictly_cubic:
        for u in range(n):
            s.add(incident_sums[u] == 3)
    else:
        # General minimal counterexample constraints from Bisch's Theorem (EGC.lean)
        # a) Minimum degree >= 3
        for u in range(n):
            s.add(incident_sums[u] >= 3)

        # b) Theorem 3: At least 2/3 of vertices have degree exactly 3
        is_cubic = [z3.If(incident_sums[u] == 3, 1, 0) for u in range(n)]
        min_cubic_count = (2 * n + 2) // 3  # ceil(2n/3)
        s.add(z3.Sum(is_cubic) >= min_cubic_count)

        # c) Lemma 2(i): Vertices of degree >= 4 form an independent set
        # No edge can connect two vertices of degree >= 4
        for u in range(n):
            for v in range(u + 1, n):
                s.add(z3.Implies(
                    e[(u, v)],
                    z3.Or(incident_sums[u] == 3, incident_sums[v] == 3)
                ))

        # d) Lemma 2(ii): Every vertex has a neighbor of degree exactly 3
        for u in range(n):
            cubic_neighbors = [z3.And(e[(u, v)], incident_sums[v] == 3) for v in range(n) if v != u]
            s.add(z3.Or(cubic_neighbors))

    # 2. Symmetry breaking on vertex 0
    s.add(e[(0, 1)])
    s.add(e[(0, 2)])
    s.add(e[(0, 3)])
    if strictly_cubic:
        for v in range(4, n):
            s.add(z3.Not(e[(0, v)]))

    # 3. No C4 constraint: no pair (u, w) can share 2 or more common neighbors
    if avoid_c4:
        for u in range(n):
            for w in range(u + 1, n):
                for v in range(n):
                    if v == u or v == w:
                        continue
                    for z in range(v + 1, n):
                        if z == u or z == w:
                            continue
                        s.add(z3.Or(
                            z3.Not(e[(u, v)]),
                            z3.Not(e[(w, v)]),
                            z3.Not(e[(u, z)]),
                            z3.Not(e[(w, z)])
                        ))

    print(f"Solving model with {len(s.assertions())} assertions...")
    t0 = time.time()
    check_res = s.check()
    elapsed = time.time() - t0

    if check_res == z3.sat:
        m = s.model()
        edges = []
        adj = [[] for _ in range(n)]
        for u in range(n):
            for v in range(u + 1, n):
                if z3.is_true(m.eval(e[(u, v)])):
                    edges.append([u, v])
                    adj[u].append(v)
                    adj[v].append(u)

        print(f"SAT! Found candidate graph in {elapsed:.3f}s with {len(edges)} edges.")
        graph_json = json.dumps({"n": n, "adj": adj})
        print(graph_json)

        # Pipe to Rust verifier if available
        verifier = Path(__file__).resolve().parent.parent / "target" / "release" / "verifier_64.exe"
        if verifier.is_file():
            res = subprocess.run([str(verifier), "--json", graph_json], text=True, capture_output=True)
            print("Rust Verifier Output:")
            print(res.stdout)
        return adj
    elif check_res == z3.unsat:
        print(f"UNSAT: Proved that no such graph exists on n={n} vertices in {elapsed:.3f}s.")
        return None
    else:
        print(f"UNKNOWN / TIMEOUT after {elapsed:.3f}s.")
        return None

def main():
    parser = argparse.ArgumentParser(description="Z3 SAT Solver for Erdős #64")
    parser.add_argument("n", type=int, nargs="?", default=12, help="Number of vertices")
    parser.add_argument("--general", action="store_true", help="Enable general minimal counterexample mode (Bisch bounds)")
    parser.add_argument("--timeout", type=float, default=60.0, help="Timeout in seconds")
    args = parser.parse_args()

    solve_erdos_64(n=args.n, strictly_cubic=not args.general, timeout_sec=args.timeout)

if __name__ == "__main__":
    main()
