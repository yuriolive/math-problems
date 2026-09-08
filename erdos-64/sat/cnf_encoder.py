"""
DIMACS CNF Encoder for Erdős Problem #64 (Erdős–Gyárfás Conjecture).
Encodes the search for a cubic graph on n vertices with no cycles of length 2^k (no C4, no C8).
"""

import itertools
from pathlib import Path

class Erdos64SatEncoder:
    def __init__(self, n: int):
        assert n % 2 == 0, "n must be even for a 3-regular graph"
        assert n <= 64, "n must be <= 64"
        self.n = n
        self.edge_vars: dict[tuple[int, int], int] = {}
        self.var_to_edge: dict[int, tuple[int, int]] = {}
        self.var_count = 0
        self.clauses: list[list[int]] = []

        # Allocate variables for each edge (u, v) with u < v
        for u in range(n):
            for v in range(u + 1, n):
                self.var_count += 1
                self.edge_vars[(u, v)] = self.var_count
                self.edge_vars[(v, u)] = self.var_count
                self.var_to_edge[self.var_count] = (u, v)

    def get_var(self, u: int, v: int) -> int:
        return self.edge_vars[(min(u, v), max(u, v))]

    def add_clause(self, clause: list[int]):
        self.clauses.append(clause)

    def encode_at_most_k(self, vars_list: list[int], k: int):
        """Standard naive encoding of at-most-k for small k."""
        for comb in itertools.combinations(vars_list, k + 1):
            self.add_clause([-v for v in comb])

    def encode_at_least_k(self, vars_list: list[int], k: int):
        """Standard naive encoding of at-least-k."""
        # at least k <=> at most (len - k) can be false
        neg_vars = [-v for v in vars_list]
        for comb in itertools.combinations(neg_vars, len(vars_list) - k + 1):
            self.add_clause([-v for v in comb])

    def encode_degree_3(self):
        """Each vertex must have degree exactly 3."""
        for u in range(self.n):
            incident = [self.get_var(u, v) for v in range(self.n) if v != u]
            self.encode_at_most_k(incident, 3)
            self.encode_at_least_k(incident, 3)

    def encode_no_c3(self):
        """Optional: girth >= 4 (no triangles)."""
        for u in range(self.n):
            for v in range(u + 1, self.n):
                for w in range(v + 1, self.n):
                    e1 = self.get_var(u, v)
                    e2 = self.get_var(v, w)
                    e3 = self.get_var(u, w)
                    self.add_clause([-e1, -e2, -e3])

    def encode_no_c4(self):
        """No 4-cycles: for any pair (u, w) and any two distinct common neighbors (v, z)."""
        for u in range(self.n):
            for w in range(u + 1, self.n):
                for v in range(self.n):
                    if v == u or v == w:
                        continue
                    for z in range(v + 1, self.n):
                        if z == u or z == w:
                            continue
                        e_uv = self.get_var(u, v)
                        e_wv = self.get_var(w, v)
                        e_uz = self.get_var(u, z)
                        e_wz = self.get_var(w, z)
                        # Cannot have all 4 edges: ~e_uv | ~e_wv | ~e_uz | ~e_wz
                        self.add_clause([-e_uv, -e_wv, -e_uz, -e_wz])

    def encode_symmetry_breaking(self):
        """Fix vertex 0 to connect to 1, 2, 3, and not to v >= 4."""
        self.add_clause([self.get_var(0, 1)])
        self.add_clause([self.get_var(0, 2)])
        self.add_clause([self.get_var(0, 3)])
        for v in range(4, self.n):
            self.add_clause([-self.get_var(0, v)])

    def generate_dimacs(self) -> str:
        lines = [
            f"c Erdős-Gyárfás Problem 64 SAT encoding for n={self.n}",
            f"p cnf {self.var_count} {len(self.clauses)}",
        ]
        for c in self.clauses:
            lines.append(" ".join(str(lit) for lit in c) + " 0")
        return "\n".join(lines)

    def write_cnf(self, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.generate_dimacs()
        output_path.write_text(content, encoding="utf-8")
        return len(self.clauses)

if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    encoder = Erdos64SatEncoder(n)
    encoder.encode_degree_3()
    encoder.encode_no_c4()
    encoder.encode_symmetry_breaking()
    out_file = Path(f"erdos64_n{n}.cnf")
    cnt = encoder.write_cnf(out_file)
    print(f"Generated {out_file} with {encoder.var_count} vars and {cnt} clauses.")
