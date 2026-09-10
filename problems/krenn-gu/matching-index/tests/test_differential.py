"""Differential tests: the Rust checker against a slow, independently written reference.

The two programs disagree about almost everything except the answer. The Rust checker
enumerates the perfect matchings of the coloured multi-graph once and buckets them by the
colouring each one induces; it never builds a filtered graph and never iterates over
colourings. The reference here does the opposite: it walks all ``d**n`` vertex colourings,
filters the graph for each one, and evaluates a Hafnian by recursive expansion. The
bookkeeping that connects a matching to the colouring it induces -- the part most likely to
be wrong -- is therefore written twice, in opposite directions.

What is shared, and so is *not* tested here: the mathematics of reducing modulo the
cyclotomic polynomial. Both sides reduce a weight in ``Q[z]/(z^m - 1)`` modulo ``Phi_m``
to decide whether it is zero. The implementations are separate, the method is the same.
"""

from __future__ import annotations

import json
import random
import subprocess
import unittest
from fractions import Fraction
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BINARY = ROOT / "verifier" / "target" / "release" / "ghzcheck"


def binary() -> Path:
    if not BINARY.exists():
        subprocess.run(
            ["cargo", "build", "--release"],
            cwd=ROOT / "verifier",
            check=True,
            capture_output=True,
        )
    return BINARY


# --- exact arithmetic in Q(zeta_m) -----------------------------------------------------


def cyclotomic(m: int) -> list[int]:
    """Coefficients of Phi_m, ascending. x^m - 1 = prod_{d | m} Phi_d."""
    num = [0] * (m + 1)
    num[0], num[m] = -1, 1
    for d in range(1, m):
        if m % d == 0:
            num = poly_div(num, cyclotomic(d))
    return num


def poly_div(a: list[int], b: list[int]) -> list[int]:
    bd = len(b) - 1
    rem = list(a)
    quo = [0] * max(len(a) - bd, 0)
    for i in range(len(rem) - 1, bd - 1, -1):
        lead = rem[i]
        if lead == 0:
            continue
        quo[i - bd] = lead
        for j in range(bd + 1):
            rem[i - bd + j] -= lead * b[j]
    assert all(c == 0 for c in rem), "inexact division"
    return quo


def mul(a: list[Fraction], b: list[Fraction], m: int) -> list[Fraction]:
    out = [Fraction(0)] * m
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                if y:
                    out[(i + j) % m] += x * y
    return out


def add(a: list[Fraction], b: list[Fraction]) -> list[Fraction]:
    return [x + y for x, y in zip(a, b)]


def reduce_mod(a: list[Fraction], phi: list[int]) -> list[Fraction]:
    k = len(phi) - 1
    r = list(a)
    for i in range(len(r) - 1, k - 1, -1):
        lead = r[i]
        if not lead:
            continue
        for j in range(k + 1):
            r[i - k + j] -= lead * phi[j]
    return r[:k]


# --- the reference checker -------------------------------------------------------------


def hafnian(entry, verts, m, unit):
    """Sum over perfect matchings of `verts` of the product of entries."""
    if not verts:
        return list(unit)
    u = verts[0]
    total = [Fraction(0)] * m
    for i in range(1, len(verts)):
        v = verts[i]
        a = entry(u, v)
        if not any(a):
            continue
        rest = verts[1:i] + verts[i + 1 :]
        total = add(total, mul(a, hafnian(entry, rest, m, unit), m))
    return total


def reference(inst: dict) -> dict:
    n, d = inst["n"], inst["colours"]
    m = inst.get("root_of_unity", 1)
    phi = cyclotomic(m)
    one = [Fraction(0)] * m
    one[0] = Fraction(1)

    edges = []
    for e in inst["edges"]:
        u, v, cu, cv = e["u"], e["v"], e["cu"], e["cv"]
        if u > v:
            u, v, cu, cv = v, u, cv, cu
        w = [Fraction(0)] * m
        for i, (num, den) in enumerate(e.get("w") or [[1, 1]]):
            w[i] = Fraction(num, den)
        edges.append((u, v, cu, cv, w))

    colourings = {}
    for vc in product(range(d), repeat=n):

        def weight_entry(u, v, vc=vc):
            acc = [Fraction(0)] * m
            for (a, b, ca, cb, w) in edges:
                if (a, b) == (u, v) and ca == vc[u] and cb == vc[v]:
                    acc = add(acc, w)
            return acc

        def count_entry(u, v, vc=vc):
            c = sum(
                1
                for (a, b, ca, cb, _) in edges
                if (a, b) == (u, v) and ca == vc[u] and cb == vc[v]
            )
            out = [Fraction(0)] * m
            out[0] = Fraction(c)
            return out

        verts = list(range(n))
        count = hafnian(count_entry, verts, m, one)[0]
        if not count:
            continue
        weight = reduce_mod(hafnian(weight_entry, verts, m, one), phi)
        colourings[vc] = (int(count), weight)

    mono = [vc for vc in colourings if len(set(vc)) == 1]
    ghz = bool(mono)
    for vc, (_, w) in colourings.items():
        target = 1 if len(set(vc)) == 1 else 0
        expect = [Fraction(target)] + [Fraction(0)] * (len(w) - 1)
        if w != expect:
            ghz = False
    return {
        "colourings": colourings,
        "matchings": sum(c for c, _ in colourings.values()),
        "ghz": ghz,
        "dimension": len(mono) if ghz else 0,
    }


def run_checker(inst: dict) -> dict:
    proc = subprocess.run(
        [str(binary()), "--dump-colourings", "/dev/stdin"],
        input=json.dumps(inst),
        capture_output=True,
        text=True,
    )
    out = json.loads(proc.stdout)
    if out.get("status") != "evaluated":
        raise AssertionError(f"checker returned unknown: {out.get('reason')}")
    return out


def compare(case: unittest.TestCase, inst: dict) -> None:
    got, want = run_checker(inst), reference(inst)
    case.assertEqual(got["matchings"], want["matchings"], "matching count")
    case.assertEqual(got["ghz"], want["ghz"], "GHZ verdict")
    case.assertEqual(got["dimension"], want["dimension"], "dimension")

    seen = {}
    for entry in got["colourings"]:
        weight = [Fraction(num, den) for num, den in entry["weight"]]
        seen[tuple(entry["colouring"])] = (entry["matchings"], weight)
    case.assertEqual(set(seen), set(want["colourings"]), "feasible colourings")
    for vc, (count, weight) in want["colourings"].items():
        case.assertEqual(seen[vc][0], count, f"matchings for {vc}")
        case.assertEqual(seen[vc][1], weight, f"weight for {vc}")


class Instances(unittest.TestCase):
    def test_every_instance_in_the_corpus(self):
        paths = sorted((ROOT / "instances").glob("*.json"))
        self.assertTrue(paths, "no instances found")
        for path in paths:
            with self.subTest(instance=path.name):
                compare(self, json.loads(path.read_text()))


class Random(unittest.TestCase):
    """Random coloured multi-graphs, where the disagreements would actually live."""

    @staticmethod
    def nonzero_at_root(w, phi, m):
        coeffs = [Fraction(num, den) for num, den in w]
        return any(reduce_mod(coeffs + [Fraction(0)] * (m - len(coeffs)), phi))

    def instances(self):
        rng = random.Random(20260910)
        for _ in range(60):
            n = rng.choice([4, 6])
            d = rng.choice([2, 3])
            m = rng.choice([1, 2, 3, 4])
            phi = cyclotomic(m)
            edges = []
            for u in range(n):
                for v in range(u + 1, n):
                    for cu in range(d):
                        for cv in range(d):
                            if rng.random() < 0.18:
                                w = [[0, 1]] * m
                                # A weight that is zero in Q(zeta_m) is not a legal input,
                                # so keep the constant term non-zero.
                                w[0] = [rng.choice([-2, -1, 1, 2, 3]), rng.choice([1, 2])]
                                if m > 1 and rng.random() < 0.5:
                                    w[rng.randrange(1, m)] = [rng.choice([-1, 1, 2]), 1]
                                # A weight that vanishes at zeta_m is an absent edge, and
                                # the checker refuses to be handed one.
                                if not self.nonzero_at_root(w, phi, m):
                                    continue
                                edges.append(
                                    {"u": u, "v": v, "cu": cu, "cv": cv, "w": w}
                                )
            if not edges:
                continue
            yield {"n": n, "colours": d, "root_of_unity": m, "edges": edges}

    def test_random_multigraphs_agree(self):
        checked = 0
        for inst in self.instances():
            with self.subTest(edges=len(inst["edges"]), n=inst["n"]):
                compare(self, inst)
            checked += 1
        self.assertGreater(checked, 40, "too few random instances actually ran")


if __name__ == "__main__":
    unittest.main()
