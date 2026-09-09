"""Exact maximum uniform 3-sunflower-free family sizes, by SAT.

For each order `n` and set size `k`, decide "is there a `k`-uniform 3-sunflower-free
family of size at least `s` on [n]?" and raise `s` until it fails. The largest satisfiable
`s` is the exact value, written `Munif(n, k)`.

Why this quantity and not the one already in the literature: the tensor-power argument
that turns a finite family into a lower bound on the capacity mu_3 requires the family to
be **uniform**. For a sunflower in a direct sum, each coordinate must separately be a
sunflower or have coincident sets, and the case A1 = A2 != A3 only forces A1 subset A3 --
it is uniformity, via equal cardinality, that closes it. So

    mu_3 >= Munif(n, k) ** (1 / n)

for every n and k, whereas the non-uniform maxima bound nothing. The record to beat is
1.551 (Deuber-Erdos-Gunderson-Kostochka-Meyer 1997), or 1.554 (Naslund, unpublished).

Two rules this driver follows, both from the repository's working rules:

* **Ground truth is a separate program.** Every satisfiable model is handed to the
  compiled checker (`verifier_857`'s `check` binary), which re-derives uniformity,
  distinctness and the sunflower count from scratch. A model the solver calls SAT but the
  checker rejects is a bug and stops the run.
* **"Absent" never means "not evaluated".** An `s` that exhausts its budget is recorded as
  `lower-bound-only` and printed with a trailing `+`, never as an exact value.

Cells are independent, so they run across processes. The solver is CaDiCaL 1.9.5 via
python-sat; it is a pure SAT solver and much faster here than an SMT solver.

    uv run python sat/sweep.py --n 6 --k 3
    uv run python sat/sweep.py --n 4-12 --all-k --budget 120 --jobs 30
    uv run python sat/sweep.py --n 3-6 --all-k --verify-against-brute
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

try:
    from pysat.card import CardEnc, EncType
    from pysat.formula import IDPool
    from pysat.solvers import Cadical195
except ImportError:
    sys.exit("python-sat is required: declared in pyproject.toml, so run under `uv run`")

HERE = Path(__file__).resolve().parent
PROBLEM_ROOT = HERE.parent

# The two published lower bounds on mu_3. A ratio above the first is a new record.
RECORD_CITABLE = 1.551
RECORD_BAR = 1.554


def binary(name: str) -> Path:
    """Locate a release binary from the verifier crate, or explain how to build it."""
    exe = name + (".exe" if sys.platform == "win32" else "")
    path = PROBLEM_ROOT / "verifier" / "target" / "release" / exe
    if not path.is_file():
        sys.exit(
            f"{path} not found. Build it first:\n"
            f"  cargo build --release --manifest-path "
            f"{PROBLEM_ROOT / 'verifier' / 'Cargo.toml'}"
        )
    return path


def load_instance(n: int, k: int) -> tuple[list[int], list[tuple[int, int, int]]]:
    """The k-subsets of [n] and every sunflower triple, via the compiled enumerator."""
    out = subprocess.run(
        [str(binary("triples")), str(n), str(k)],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()

    assert out[0].startswith("sets "), f"unexpected header {out[0]!r}"
    num = int(out[0].split()[1])
    sets = [int(x) for x in out[1 : 1 + num]]

    head = out[1 + num]
    assert head.startswith("triples "), f"unexpected header {head!r}"
    count = int(head.split()[1])
    triples = [
        tuple(int(v) for v in line.split())
        for line in out[2 + num : 2 + num + count]
    ]
    assert len(triples) == count, f"expected {count} triples, parsed {len(triples)}"
    return sets, triples  # type: ignore[return-value]


def verify_with_checker(n: int, sets: list[int]) -> dict:
    """Re-derive everything with the compiled checker. Never trust the solver's word."""
    payload = json.dumps({"n": n, "sets": sets})
    proc = subprocess.run(
        [str(binary("check"))], input=payload, capture_output=True, text=True,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"checker produced no JSON (exit {proc.returncode}): {proc.stdout[:200]}"
        )


def decide(
    sets: list[int],
    triples: list[tuple[int, int, int]],
    s: int,
    budget: int,
) -> tuple[str, list[int] | None]:
    """Is there an admissible family of size >= s?

    Returns ("sat", masks) | ("unsat", None) | ("unknown", None). `budget` caps conflicts;
    exceeding it yields "unknown", which the caller must not read as "unsat".
    """
    num = len(sets)
    if s > num:
        return "unsat", None
    if s <= 0:
        return "sat", []

    pool = IDPool(start_from=num + 1)
    clauses: list[list[int]] = [[-(a + 1), -(b + 1), -(c + 1)] for a, b, c in triples]

    # At least s of the variables true. Sequential encoding, with auxiliaries drawn from
    # the pool so they cannot collide with the set variables.
    card = CardEnc.atleast(
        lits=list(range(1, num + 1)), bound=s, vpool=pool, encoding=EncType.seqcounter
    )
    clauses.extend(card.clauses)

    with Cadical195(bootstrap_with=clauses) as solver:
        if budget > 0:
            solver.conf_budget(budget)
            result = solver.solve_limited(expect_interrupt=False)
        else:
            result = solver.solve()

        if result is None:
            return "unknown", None
        if not result:
            return "unsat", None
        model = set(solver.get_model())
        chosen = [sets[i] for i in range(num) if (i + 1) in model]
        return "sat", chosen


@dataclass
class Cell:
    n: int
    k: int
    num_sets: int
    num_triples: int
    best: int = 0
    best_family: list[int] = field(default_factory=list)
    status: str = "exact"  # exact | lower-bound-only
    note: str = ""

    @property
    def ratio(self) -> float:
        return self.best ** (1.0 / self.n) if self.best and self.n else 0.0

    @property
    def label(self) -> str:
        return f"{self.best}{'' if self.status == 'exact' else '+'}"


def solve_cell(n: int, k: int, budget: int) -> Cell:
    """Climb s until unsatisfiable. Runs in a worker process; returns a plain Cell."""
    sets, triples = load_instance(n, k)
    cell = Cell(n=n, k=k, num_sets=len(sets), num_triples=len(triples))

    s = 1
    while True:
        status, model = decide(sets, triples, s, budget)

        if status == "sat":
            checked = verify_with_checker(n, model)
            if not checked.get("admissible"):
                raise RuntimeError(
                    f"CHECKER REJECTED a model CaDiCaL called sat at n={n} k={k} s={s}: "
                    f"{checked}. This is a bug, not a result."
                )
            if checked["size"] < s:
                raise RuntimeError(
                    f"model at n={n} k={k} has {checked['size']} sets, asked for >= {s}"
                )
            if checked["k"] != k:
                raise RuntimeError(f"model at n={n} k={k} has k={checked['k']}")
            cell.best = checked["size"]
            cell.best_family = model
            s = checked["size"] + 1
            continue

        if status == "unsat":
            cell.status = "exact"
            return cell

        cell.status = "lower-bound-only"
        cell.note = f"budget {budget} conflicts exhausted at s={s}"
        return cell


def brute_max(n: int, k: int) -> int:
    """Independent exact maximum, by exhaustive branch and bound. Different algorithm."""
    out = subprocess.run(
        [str(binary("brute")), str(n), str(k)],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)["max"]


def parse_range(spec: str) -> list[int]:
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return list(range(int(lo), int(hi) + 1))
    return [int(spec)]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", required=True, help="order, or a range like 4-12")
    ap.add_argument("--k", help="set size, or a range; omit with --all-k")
    ap.add_argument("--all-k", action="store_true", help="every k from 2 to n-1")
    ap.add_argument("--budget", type=int, default=200000,
                    help="conflict budget per decision; 0 means unlimited")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 2),
                    help="worker processes (default: cores - 2)")
    ap.add_argument("--verify-against-brute", action="store_true",
                    help="cross-check every exact cell against exhaustive search")
    ap.add_argument("--json", help="write results to this file")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    cells_wanted: list[tuple[int, int]] = []
    for n in parse_range(args.n):
        ks = list(range(2, n)) if args.all_k else parse_range(args.k or "")
        for k in ks:
            if 1 <= k < n:
                cells_wanted.append((n, k))
    if not cells_wanted:
        ap.error("no cells selected; give --k or --all-k")

    verbose = not args.quiet
    jobs = max(1, min(args.jobs, len(cells_wanted)))
    if verbose:
        print(f"{len(cells_wanted)} cells, {jobs} workers, "
              f"budget {args.budget or 'unlimited'} conflicts/decision", flush=True)

    cells: list[Cell] = []
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futures = {
            pool.submit(solve_cell, n, k, args.budget): (n, k)
            for n, k in cells_wanted
        }
        for fut in as_completed(futures):
            n, k = futures[fut]
            cell = fut.result()  # a checker rejection raises here, which is intended
            cells.append(cell)
            if verbose:
                print(f"  n={cell.n} k={cell.k}: Munif = {cell.label}  "
                      f"ratio {cell.ratio:.6f}", flush=True)

    if args.verify_against_brute:
        for c in cells:
            if c.status != "exact":
                print(f"  brute check skipped at n={c.n} k={c.k}: {c.status}")
                continue
            b = brute_max(c.n, c.k)
            if b != c.best:
                sys.exit(
                    f"DIFFERENTIAL FAILURE at n={c.n} k={c.k}: "
                    f"SAT says {c.best}, exhaustive search says {b}"
                )
        if verbose:
            print("  exhaustive search agrees on every exact cell")

    print()
    print(f"{'n':>3} {'k':>3} {'subsets':>8} {'triples':>9} {'Munif':>7} "
          f"{'ratio':>9}  status")
    print("-" * 62)
    for c in sorted(cells, key=lambda c: (c.n, c.k)):
        print(f"{c.n:>3} {c.k:>3} {c.num_sets:>8} {c.num_triples:>9} "
              f"{c.label:>7} {c.ratio:>9.6f}  {c.status}")

    print()
    best = max((c for c in cells if c.best), key=lambda c: c.ratio, default=None)
    if best:
        print(f"best ratio: {best.ratio:.6f} at n={best.n} k={best.k} "
              f"(size {best.label})")
        print(f"citable record {RECORD_CITABLE}, bar {RECORD_BAR}")
        if best.ratio > RECORD_BAR:
            print("*** ABOVE THE BAR -- re-verify independently before claiming anything")
        elif best.ratio > RECORD_CITABLE:
            print("*** above the citable record, below the unpublished bar")
        else:
            print(f"short of the record by {RECORD_CITABLE - best.ratio:.6f}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                [
                    {
                        "n": c.n, "k": c.k, "num_sets": c.num_sets,
                        "num_triples": c.num_triples, "munif": c.best,
                        "exact": c.status == "exact", "ratio": c.ratio,
                        "note": c.note, "family": c.best_family,
                    }
                    for c in sorted(cells, key=lambda c: (c.n, c.k))
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"wrote {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
