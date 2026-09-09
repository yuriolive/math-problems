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
* **"Absent" never means "not evaluated".** An `s` that times out is recorded as `unknown`,
  never as unsatisfiable, so a timeout can never be read as an exact value.

    uv run python sat/sweep.py --n 6 --k 3
    uv run python sat/sweep.py --n 4-9 --all-k --timeout 60
    uv run python sat/sweep.py --n 6 --k 3 --verify-against-brute
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import z3
except ImportError:
    sys.exit("z3 is required: it is declared in pyproject.toml, so run under `uv run`")

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


@dataclass
class Instance:
    """The k-subsets of [n] and every sunflower triple among them."""

    n: int
    k: int
    sets: list[int]
    triples: list[tuple[int, int, int]]

    @property
    def num_sets(self) -> int:
        return len(self.sets)


def load_instance(n: int, k: int) -> Instance:
    """Enumerate via the compiled helper: the triple loop is O(N^3)."""
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
    triples = []
    for line in out[2 + num : 2 + num + count]:
        a, b, c = line.split()
        triples.append((int(a), int(b), int(c)))
    assert len(triples) == count, f"expected {count} triples, parsed {len(triples)}"

    return Instance(n=n, k=k, sets=sets, triples=triples)


def verify_with_checker(n: int, sets: list[int]) -> dict:
    """Re-derive everything with the compiled checker. Never trust the solver's word."""
    payload = json.dumps({"n": n, "sets": sets})
    proc = subprocess.run(
        [str(binary("check"))], input=payload, capture_output=True, text=True,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        sys.exit(f"checker produced no JSON (exit {proc.returncode}): {proc.stdout[:200]}")


def satisfiable(inst: Instance, s: int, timeout_sec: float) -> tuple[str, list[int] | None]:
    """Is there an admissible family of size >= s? Returns (status, model).

    status is "sat", "unsat" or "unknown"; "unknown" is never collapsed into "unsat".
    """
    if s > inst.num_sets:
        return "unsat", None
    if s <= 0:
        return "sat", []

    solver = z3.Solver()
    xs = [z3.Bool(f"x{i}") for i in range(inst.num_sets)]

    # No triple may be fully chosen.
    for a, b, c in inst.triples:
        solver.add(z3.Or(z3.Not(xs[a]), z3.Not(xs[b]), z3.Not(xs[c])))

    # z3's native cardinality, rather than a hand-rolled counter: fewer moving parts, and
    # a sequential counter over the negated literals would need N - s auxiliaries per
    # position, which is the larger bound in exactly the regime that matters here.
    solver.add(z3.AtLeast(*xs, s))

    solver.set("timeout", int(timeout_sec * 1000))
    result = solver.check()

    if result == z3.sat:
        model = solver.model()
        chosen = [
            inst.sets[i]
            for i in range(inst.num_sets)
            if z3.is_true(model.eval(xs[i], model_completion=True))
        ]
        return "sat", chosen
    if result == z3.unsat:
        return "unsat", None
    return "unknown", None


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


def solve_cell(n: int, k: int, timeout_sec: float, verbose: bool) -> Cell:
    inst = load_instance(n, k)
    cell = Cell(n=n, k=k, num_sets=inst.num_sets, num_triples=len(inst.triples))

    # Climb from 1: the first s that is not satisfiable settles the maximum, and every
    # satisfiable step leaves a checked witness behind.
    s = 1
    while True:
        status, model = satisfiable(inst, s, timeout_sec)

        if status == "sat":
            checked = verify_with_checker(n, model)
            if not checked.get("admissible"):
                sys.exit(
                    f"CHECKER REJECTED a model the solver called sat at "
                    f"n={n} k={k} s={s}: {checked}. This is a bug, not a result."
                )
            if checked["size"] < s:
                sys.exit(
                    f"model at n={n} k={k} has {checked['size']} sets, asked for >= {s}"
                )
            if checked["k"] != k:
                sys.exit(f"model at n={n} k={k} has k={checked['k']}")
            cell.best = checked["size"]
            cell.best_family = model
            if verbose:
                print(f"    s={s}: sat (checked, size {checked['size']})", flush=True)
            s = checked["size"] + 1
            continue

        if status == "unsat":
            if verbose:
                print(f"    s={s}: unsat -> maximum is {cell.best}", flush=True)
            cell.status = "exact"
            return cell

        # Timeout. Rule 2: this is not evidence of unsatisfiability.
        cell.status = "lower-bound-only"
        cell.note = f"timed out at s={s} after {timeout_sec:g}s"
        if verbose:
            print(f"    s={s}: unknown (timeout) -> {cell.best}+ only", flush=True)
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
    ap.add_argument("--n", required=True, help="order, or a range like 4-9")
    ap.add_argument("--k", help="set size, or a range; omit with --all-k")
    ap.add_argument("--all-k", action="store_true", help="every k from 2 to n-1")
    ap.add_argument("--timeout", type=float, default=60.0, help="per-decision seconds")
    ap.add_argument("--verify-against-brute", action="store_true",
                    help="cross-check every cell against exhaustive search")
    ap.add_argument("--json", help="write results to this file")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    ns = parse_range(args.n)
    if not args.all_k and not args.k:
        ap.error("give --k or --all-k")

    verbose = not args.quiet
    cells: list[Cell] = []
    record_hits: list[Cell] = []

    for n in ns:
        ks = list(range(2, n)) if args.all_k else parse_range(args.k)
        for k in ks:
            if k >= n or k < 1:
                continue
            if verbose:
                print(f"n={n} k={k}", flush=True)
            cell = solve_cell(n, k, args.timeout, verbose)

            if args.verify_against_brute:
                if cell.status != "exact":
                    print(f"    brute check skipped: cell is {cell.status}")
                else:
                    b = brute_max(n, k)
                    if b != cell.best:
                        sys.exit(
                            f"DIFFERENTIAL FAILURE at n={n} k={k}: "
                            f"SAT says {cell.best}, exhaustive search says {b}"
                        )
                    if verbose:
                        print(f"    brute agrees: {b}")

            cells.append(cell)
            if cell.status == "exact" and cell.ratio > RECORD_CITABLE:
                record_hits.append(cell)
            if verbose:
                mark = "" if cell.status == "exact" else "+"
                print(f"  -> Munif({n},{k}) = {cell.best}{mark}  "
                      f"ratio {cell.ratio:.6f}", flush=True)

    print()
    print(f"{'n':>3} {'k':>3} {'subsets':>8} {'triples':>9} {'Munif':>7} "
          f"{'ratio':>9}  status")
    print("-" * 60)
    for c in sorted(cells, key=lambda c: (c.n, c.k)):
        mark = "" if c.status == "exact" else "+"
        print(f"{c.n:>3} {c.k:>3} {c.num_sets:>8} {c.num_triples:>9} "
              f"{str(c.best) + mark:>7} {c.ratio:>9.6f}  {c.status}"
              + (f" ({c.note})" if c.note else ""))

    print()
    best = max((c for c in cells if c.best), key=lambda c: c.ratio, default=None)
    if best:
        print(f"best ratio seen: {best.ratio:.6f} at n={best.n} k={best.k} "
              f"(size {best.best})")
        print(f"citable record to beat: {RECORD_CITABLE}   bar: {RECORD_BAR}")
        if best.ratio > RECORD_BAR:
            print("*** ABOVE THE BAR -- re-verify independently before claiming anything")
        elif best.ratio > RECORD_CITABLE:
            print("*** above the citable record, below the unpublished bar")
        else:
            gap = RECORD_CITABLE - best.ratio
            print(f"short of the record by {gap:.6f}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                [
                    {
                        "n": c.n, "k": c.k, "num_sets": c.num_sets,
                        "num_triples": c.num_triples, "munif": c.best,
                        "ratio": c.ratio, "status": c.status, "note": c.note,
                        "family": c.best_family,
                    }
                    for c in cells
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"wrote {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
