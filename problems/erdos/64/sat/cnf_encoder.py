"""DIMACS CNF encoder for Erdős Problem #64.

Encodes "cubic graph on n vertices with no cycle of length L" for given L.

Two things the earlier version got wrong:

* `encode_at_most_k` used the naive "forbid every (k+1)-subset" encoding. At k = 3
  over the 63 possible neighbours of a vertex that is C(63,4) = 595665 clauses per
  vertex, about 38 million at n = 64, which never finishes. This uses the sequential
  counter (Sinz) encoding: O(n*k) clauses and O(n*k) auxiliary variables.
* The module was dead code. Nothing imported it, so its `encode_no_c4` was never
  exercised while `run_sat.py` silently ignored its own `avoid_c8` flag. It is now
  the shared source of the cycle enumeration used by `run_sat.py`.
"""

import itertools
from pathlib import Path


def enumerate_cycles(n: int, length: int):
    """Yields every simple cycle on `length` of the `n` vertices, once.

    Canonical form: the cycle starts at its smallest vertex and its second vertex is
    smaller than its last, which picks one of the two traversal directions.
    """
    if length < 3 or length > n:
        return
    for subset in itertools.combinations(range(n), length):
        start = subset[0]
        rest = subset[1:]
        for perm in itertools.permutations(rest):
            if perm[0] > perm[-1]:
                continue  # same cycle, opposite direction
            yield (start,) + perm


def count_cycles(n: int, length: int) -> int:
    """How many clauses `encode_no_cycles_of_length` would emit."""
    if length < 3 or length > n:
        return 0
    from math import comb, factorial
    return comb(n, length) * factorial(length - 1) // 2


class ClauseBudgetExceeded(RuntimeError):
    """The requested constraint would need more clauses than allowed."""


class Erdos64SatEncoder:
    def __init__(self, n: int, max_clauses: int = 2_000_000):
        assert n % 2 == 0, "n must be even for a 3-regular graph"
        assert n <= 64, "n must be <= 64"
        self.n = n
        self.max_clauses = max_clauses
        self.edge_vars: dict[tuple[int, int], int] = {}
        self.var_to_edge: dict[int, tuple[int, int]] = {}
        self.var_count = 0
        self.clauses: list[list[int]] = []

        for u in range(n):
            for v in range(u + 1, n):
                self.var_count += 1
                self.edge_vars[(u, v)] = self.var_count
                self.edge_vars[(v, u)] = self.var_count
                self.var_to_edge[self.var_count] = (u, v)

    # ---- variables and clauses ----

    def get_var(self, u: int, v: int) -> int:
        return self.edge_vars[(min(u, v), max(u, v))]

    def new_aux_var(self) -> int:
        self.var_count += 1
        return self.var_count

    def add_clause(self, clause: list[int]) -> None:
        if len(self.clauses) >= self.max_clauses:
            raise ClauseBudgetExceeded(
                f"clause budget {self.max_clauses} exhausted; raise max_clauses or "
                "reduce n / the cycle lengths being encoded"
            )
        self.clauses.append(clause)

    # ---- cardinality ----

    def encode_at_most_k(self, vars_list: list[int], k: int) -> None:
        """Sequential counter (Sinz) encoding of sum(vars) <= k."""
        m = len(vars_list)
        if k >= m:
            return
        if k == 0:
            for v in vars_list:
                self.add_clause([-v])
            return

        # s[i][j] means "at least j+1 of the first i+1 variables are true".
        s = [[self.new_aux_var() for _ in range(k)] for _ in range(m)]

        self.add_clause([-vars_list[0], s[0][0]])
        for j in range(1, k):
            self.add_clause([-s[0][j]])

        for i in range(1, m):
            self.add_clause([-vars_list[i], s[i][0]])
            self.add_clause([-s[i - 1][0], s[i][0]])
            for j in range(1, k):
                self.add_clause([-vars_list[i], -s[i - 1][j - 1], s[i][j]])
                self.add_clause([-s[i - 1][j], s[i][j]])
            # The (k+1)-th simultaneous true value is forbidden.
            self.add_clause([-vars_list[i], -s[i - 1][k - 1]])

    def encode_at_least_k(self, vars_list: list[int], k: int) -> None:
        """sum(vars) >= k, i.e. at most len-k of them are false.

        Kept naive: for the degree constraints here len-k+1 is 2 or 3, so this is a
        few thousand clauses, not millions.
        """
        m = len(vars_list)
        if k <= 0:
            return
        if k > m:
            self.add_clause([])  # unsatisfiable
            return
        for combo in itertools.combinations(vars_list, m - k + 1):
            self.add_clause(list(combo))

    def encode_degree_3(self) -> None:
        for u in range(self.n):
            incident = [self.get_var(u, v) for v in range(self.n) if v != u]
            self.encode_at_most_k(incident, 3)
            self.encode_at_least_k(incident, 3)

    # ---- structural constraints ----

    def encode_no_c3(self) -> None:
        """No triangles. Optional: girth 3 is allowed by the conjecture."""
        for u in range(self.n):
            for v in range(u + 1, self.n):
                for w in range(v + 1, self.n):
                    self.add_clause([
                        -self.get_var(u, v), -self.get_var(v, w), -self.get_var(u, w)
                    ])

    def encode_no_cycles_of_length(self, length: int) -> int:
        """Forbid every simple cycle on exactly `length` vertices.

        Returns the number of clauses added. Raises ClauseBudgetExceeded before
        emitting anything if the constraint is too large, so callers can fall back to
        the lazy refinement loop in `run_sat.py` instead of hanging.
        """
        needed = count_cycles(self.n, length)
        if needed == 0:
            return 0
        if len(self.clauses) + needed > self.max_clauses:
            raise ClauseBudgetExceeded(
                f"forbidding every C{length} on n={self.n} needs {needed} clauses, "
                f"over the budget of {self.max_clauses}. Use the lazy cycle-blocking "
                "mode in run_sat.py for lengths this large."
            )

        added = 0
        for cyc in enumerate_cycles(self.n, length):
            clause = []
            for i in range(length):
                u, v = cyc[i], cyc[(i + 1) % length]
                clause.append(-self.get_var(u, v))
            self.add_clause(clause)
            added += 1
        return added

    def encode_no_c4(self) -> int:
        """Backwards-compatible alias."""
        return self.encode_no_cycles_of_length(4)

    def encode_symmetry_breaking(self) -> None:
        """Vertex 0 is adjacent to exactly 1, 2, 3.

        Valid because any vertex of degree 3 can be relabelled this way.
        """
        self.add_clause([self.get_var(0, 1)])
        self.add_clause([self.get_var(0, 2)])
        self.add_clause([self.get_var(0, 3)])
        for v in range(4, self.n):
            self.add_clause([-self.get_var(0, v)])

    # ---- inspection ----

    def assignment_satisfies(self, assignment: dict[int, bool]) -> bool:
        """Can `assignment` (over edge variables) be extended to satisfy the formula?

        Auxiliary variables introduced by the cardinality encoding are left free, so
        this asks about extendability rather than evaluating clauses directly. Used by
        the tests to confirm the encoding really forbids what it claims to.
        """
        import z3

        solver = z3.Solver()
        lits = {}

        def lit(v: int):
            if v not in lits:
                lits[v] = z3.Bool(f"x{v}")
            return lits[v]

        for clause in self.clauses:
            if not clause:
                return False
            solver.add(z3.Or([lit(abs(x)) if x > 0 else z3.Not(lit(abs(x))) for x in clause]))
        for var, value in assignment.items():
            solver.add(lit(var) if value else z3.Not(lit(var)))
        return solver.check() == z3.sat

    def generate_dimacs(self) -> str:
        lines = [
            f"c Erdos-Gyarfas Problem 64 SAT encoding for n={self.n}",
            f"p cnf {self.var_count} {len(self.clauses)}",
        ]
        for c in self.clauses:
            lines.append(" ".join(str(lit) for lit in c) + " 0")
        return "\n".join(lines)

    def write_cnf(self, output_path: Path) -> int:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.generate_dimacs(), encoding="utf-8")
        return len(self.clauses)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Emit DIMACS CNF for Erdos #64")
    ap.add_argument("n", type=int, nargs="?", default=10)
    ap.add_argument("--avoid", type=str, default="4",
                    help="comma-separated cycle lengths to forbid explicitly")
    ap.add_argument("--max-clauses", type=int, default=2_000_000)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    encoder = Erdos64SatEncoder(args.n, max_clauses=args.max_clauses)
    encoder.encode_degree_3()
    for length in [int(x) for x in args.avoid.split(",") if x.strip()]:
        try:
            added = encoder.encode_no_cycles_of_length(length)
            print(f"C{length}: {added} clauses")
        except ClauseBudgetExceeded as e:
            print(f"C{length}: skipped - {e}")
    encoder.encode_symmetry_breaking()

    out_file = Path(args.out) if args.out else Path(f"erdos64_n{args.n}.cnf")
    count = encoder.write_cnf(out_file)
    print(f"Wrote {out_file}: {encoder.var_count} vars, {count} clauses.")
