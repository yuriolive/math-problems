"""Z3 search for a cubic graph with no power-of-two cycle (Erdős Problem #64).

The previous version accepted an `avoid_c8` argument and never used it: the only
structural constraint in the model was "no C4", so neither a SAT nor an UNSAT answer
said anything about the conjecture.

Forbidding every C8 explicitly is not an option either -- on n = 14 that is
C(14,8)*7!/2 = 7.5 million clauses. So longer lengths are handled by lazy refinement
(CEGAR): solve, hand the model to the compiled Rust verifier, and when the verifier
reports a forbidden cycle, add one clause banning exactly that cycle's edge set and
solve again. Every clause added is implied by the specification, so:

  * SAT with no witness  => a genuine graph avoiding all requested lengths;
  * UNSAT                => no such graph exists on n vertices (sound).

Optionally applies Bisch's formally verified structural facts about a *minimal*
counterexample in `--general` mode. Those hold for a minimal counterexample only,
and they do not imply it is cubic; cubic remains a heuristic restriction.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import z3

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sat.cnf_encoder import count_cycles, enumerate_cycles  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def find_verifier() -> Path | None:
    exe = ".exe" if sys.platform == "win32" else ""
    for p in [
        ROOT / "target" / "release" / f"verifier_64{exe}",
        ROOT / "verifier" / "target" / "release" / f"verifier_64{exe}",
    ]:
        if p.is_file():
            return p
    return None


def pow2_lengths(n: int) -> list[int]:
    out, length = [], 4
    while length <= n:
        out.append(length)
        length *= 2
    return out


def verify(graph: dict, verifier: Path, count_cap: int = 1) -> dict:
    payload = json.dumps(graph)
    args = [str(verifier)]
    if count_cap > 1:
        args += ["--full", "--cap", str(count_cap)]
    proc = subprocess.run(args, input=payload, capture_output=True, text=True, timeout=600)
    if not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "verifier produced no output")
    return json.loads(proc.stdout)


def solve_erdos_64(
    n: int = 14,
    strictly_cubic: bool = True,
    avoid: list[int] | None = None,
    timeout_sec: float = 60.0,
    eager_max_clauses: int = 200_000,
    max_refinements: int = 2000,
):
    avoid = avoid or pow2_lengths(n)

    print(f"=== Z3 search for Erdos #64 on n={n} ===")
    print(f"Mode: {'strictly cubic' if strictly_cubic else 'min degree >= 3 (Bisch bounds)'}")
    print(f"Forbidding cycle lengths: {avoid} | timeout {timeout_sec}s")

    verifier = find_verifier()
    if verifier is None:
        print("WARNING: verifier_64 not built, so lazy refinement is unavailable.")
        print("         Only the eagerly encoded lengths will be enforced.")
        print("         Build it with `make build-verifier` for a meaningful answer.")

    s = z3.Solver()
    s.set("timeout", int(timeout_sec * 1000))

    e = {}
    for u in range(n):
        for v in range(u + 1, n):
            e[(u, v)] = z3.Bool(f"e_{u}_{v}")
            e[(v, u)] = e[(u, v)]

    def var(u: int, v: int):
        return e[(min(u, v), max(u, v))]

    incident_sums = [
        z3.Sum([z3.If(var(u, v), 1, 0) for v in range(n) if v != u]) for u in range(n)
    ]

    # 1. degrees
    if strictly_cubic:
        for u in range(n):
            s.add(incident_sums[u] == 3)
    else:
        for u in range(n):
            s.add(incident_sums[u] >= 3)
        # Bisch Theorem 3: at least ceil(2n/3) vertices have degree exactly 3.
        is_cubic = [z3.If(incident_sums[u] == 3, 1, 0) for u in range(n)]
        s.add(z3.Sum(is_cubic) >= (2 * n + 2) // 3)
        # Bisch Lemma 2(i): vertices of degree >= 4 form an independent set.
        for u in range(n):
            for v in range(u + 1, n):
                s.add(z3.Implies(var(u, v),
                                 z3.Or(incident_sums[u] == 3, incident_sums[v] == 3)))
        # Bisch Lemma 2(ii): every vertex has a neighbour of degree exactly 3.
        for u in range(n):
            s.add(z3.Or([z3.And(var(u, v), incident_sums[v] == 3)
                         for v in range(n) if v != u]))

    # 2. symmetry breaking: vertex 0 is adjacent to 1, 2, 3.
    s.add(var(0, 1), var(0, 2), var(0, 3))
    if strictly_cubic:
        for v in range(4, n):
            s.add(z3.Not(var(0, v)))

    # 3. eagerly forbid the lengths that are cheap enough to enumerate
    eager, lazy = [], []
    for length in sorted(avoid):
        if length > n:
            continue
        cost = count_cycles(n, length)
        if cost <= eager_max_clauses:
            eager.append((length, cost))
        else:
            lazy.append((length, cost))

    for length, cost in eager:
        for cyc in enumerate_cycles(n, length):
            s.add(z3.Or([z3.Not(var(cyc[i], cyc[(i + 1) % length]))
                         for i in range(length)]))
        print(f"  C{length}: enumerated eagerly ({cost} clauses)")
    for length, cost in lazy:
        print(f"  C{length}: deferred to lazy refinement (eager cost would be {cost})")

    if lazy and verifier is None:
        print("Cannot enforce the deferred lengths without the verifier. Aborting.")
        return None

    # 4. solve with lazy cycle blocking
    for iteration in range(max_refinements + 1):
        res = s.check()
        if res == z3.unsat:
            print(f"\nUNSAT after {iteration} refinement(s): no such graph exists on n={n}.")
            return None
        if res != z3.sat:
            print(f"\nUNKNOWN / timeout after {iteration} refinement(s) "
                  f"({s.reason_unknown()}).")
            return None

        m = s.model()
        adj = [[] for _ in range(n)]
        for u in range(n):
            for v in range(u + 1, n):
                if z3.is_true(m.eval(var(u, v), model_completion=True)):
                    adj[u].append(v)
                    adj[v].append(u)
        graph = {"n": n, "adj": adj}

        if verifier is None:
            print("\nSAT (eager constraints only, unverified).")
            print(json.dumps(graph))
            return adj

        report = verify(graph, verifier, count_cap=1)
        witness = report.get("cycle_witness")
        offending = [L for L in avoid if L <= n
                     and any(c["length"] == L and c["count"] > 0 for c in report["counts"])]

        if not offending:
            print(f"\nSAT after {iteration} refinement(s).")
            print(f"Verifier: min degree {report['min_degree']}, connected "
                  f"{report['connected']}, counterexample {report['counterexample']}")
            print(json.dumps(graph))
            return adj

        # Block exactly the cycle the verifier found. If the witness is missing,
        # fall back to blocking the whole model, which is weaker but still sound.
        if witness and len(witness) in offending:
            s.add(z3.Or([z3.Not(var(witness[i], witness[(i + 1) % len(witness)]))
                         for i in range(len(witness))]))
        else:
            s.add(z3.Or([z3.Not(var(u, v)) for u in range(n)
                         for v in range(u + 1, n) if v in adj[u]]))

        if iteration % 50 == 0:
            print(f"  refinement {iteration}: blocked a C{len(witness) if witness else '?'} "
                  f"(offending lengths present: {offending})")

    print(f"\nGave up after {max_refinements} refinements without a decision.")
    print("This is not evidence either way. Lazy refinement blocks one cycle per")
    print("iteration, which converges slowly. For a definitive answer at this n, force")
    print(f"eager enumeration: --eager-max-clauses {max(count_cycles(n, L) for L in avoid if L <= n)}")
    print("(watch memory: that many clauses go straight into the solver).")
    return None


def main():
    parser = argparse.ArgumentParser(description="Z3 search for Erdos #64")
    parser.add_argument("n", type=int, nargs="?", default=12, help="number of vertices")
    parser.add_argument("--general", action="store_true",
                        help="min degree >= 3 with Bisch's minimal-counterexample bounds")
    parser.add_argument("--avoid", type=str, default=None,
                        help="comma-separated cycle lengths to forbid "
                             "(default: every power of two <= n)")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--eager-max-clauses", type=int, default=200_000,
                        help="largest eager cycle enumeration to attempt per length")
    args = parser.parse_args()

    avoid = [int(x) for x in args.avoid.split(",")] if args.avoid else None
    solve_erdos_64(
        n=args.n,
        strictly_cubic=not args.general,
        avoid=avoid,
        timeout_sec=args.timeout,
        eager_max_clauses=args.eager_max_clauses,
    )


if __name__ == "__main__":
    main()
