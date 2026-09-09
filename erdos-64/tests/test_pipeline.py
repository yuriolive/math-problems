"""Tests for the Erdős #64 pipeline.

The regression tests that matter here are the differential ones: an independent
Python cycle counter is compared against the compiled Rust verifier. The previous
suite only asserted booleans, so a capped or short-circuited counter passed
everything -- which is exactly how the "C32 = 0" reporting bug survived.
"""

import json
import subprocess
import unittest
from itertools import permutations
from pathlib import Path

from engine.baseline_graphs import GENERALIZED_PETERSEN_CODE, get_seed_generators
from engine.evaluator import (
    GraphEvaluationDetail,
    evaluate_graph_candidate,
    find_verifier_binary,
    run_candidate_for_n,
    score_detail,
    verify_with_rust_binary,
)
from engine.island import GraphIslandManager, GraphProgram
from engine.map_elites import MapElitesArchive, pow2_decade
from engine.seeding import candidate_to_generator_code
from sat.cnf_encoder import Erdos64SatEncoder

ROOT = Path(__file__).resolve().parent.parent


def verifier_available() -> bool:
    try:
        find_verifier_binary()
        return True
    except FileNotFoundError:
        return False


def count_cycles_python(n: int, adj: list[list[int]], length: int) -> int:
    """Independent reference counter: brute-force DFS, no shared code with Rust."""
    if length < 3 or length > n:
        return 0
    nb = [sorted(set(a)) for a in adj]
    total = 0

    def walk(start: int, cur: int, depth: int, visited: set[int]):
        nonlocal total
        if depth == length:
            if start in nb[cur]:
                total += 1
            return
        for w in nb[cur]:
            if w > start and w not in visited:
                visited.add(w)
                walk(start, w, depth + 1, visited)
                visited.remove(w)

    for s in range(n):
        walk(s, s, 1, {s})
    return total // 2


def petersen_graph() -> dict:
    return {
        "n": 10,
        "adj": [[1, 4, 5], [0, 2, 6], [1, 3, 7], [2, 4, 8], [0, 3, 9],
                [0, 7, 8], [1, 8, 9], [2, 5, 9], [3, 5, 6], [4, 6, 7]],
    }


def two_disjoint_k4s() -> dict:
    adj = [[] for _ in range(8)]
    for base in (0, 4):
        for u in range(base, base + 4):
            for v in range(base, base + 4):
                if u != v:
                    adj[u].append(v)
    return {"n": 8, "adj": adj}


@unittest.skipUnless(verifier_available(), "verifier_64 not built; run `make build-verifier`")
class TestVerifierAgreement(unittest.TestCase):
    """The Rust verifier must agree with an independent Python counter."""

    def setUp(self):
        self.verifier = find_verifier_binary()

    def test_petersen_counts_match_reference(self):
        g = petersen_graph()
        detail = verify_with_rust_binary(self.verifier, g, count_cap=100000)
        for length in (4, 8):
            self.assertEqual(
                detail.counts[length],
                count_cycles_python(g["n"], g["adj"], length),
                f"C{length} disagreement on the Petersen graph",
            )

    def test_saved_candidates_counts_match_reference(self):
        """Every stored candidate is re-counted independently.

        This is the test that would have caught the published table claiming
        C16 = 1 and C32 = 0.
        """
        candidates = sorted((ROOT / "cuda").glob("best_swarm_n*.json"))
        self.assertTrue(candidates, "no candidate graphs found to check")
        for path in candidates[:4]:  # keep the suite fast
            data = json.loads(path.read_text(encoding="utf-8"))
            detail = verify_with_rust_binary(self.verifier, data, count_cap=100000)
            for length in (4, 8, 16):
                if length > data["n"]:
                    continue
                expected = count_cycles_python(data["n"], data["adj"], length)
                if detail.capped.get(length):
                    self.assertGreaterEqual(detail.counts[length], 1)
                    continue
                self.assertEqual(
                    detail.counts[length], expected,
                    f"{path.name}: C{length} Rust={detail.counts[length]} Python={expected}",
                )

    def test_every_pow2_length_is_checked_not_short_circuited(self):
        """A graph with a C4 must still get its C8/C16 tiers evaluated."""
        g = two_disjoint_k4s()
        detail = verify_with_rust_binary(self.verifier, g, count_cap=100000)
        self.assertEqual(detail.checked_lengths, [4, 8])
        self.assertGreater(detail.counts[4], 0)
        self.assertIn(8, detail.counts)

    def test_disconnected_graph_is_flagged(self):
        detail = verify_with_rust_binary(self.verifier, two_disjoint_k4s(), count_cap=10)
        self.assertFalse(detail.connected)
        self.assertEqual(detail.components, 2)
        self.assertFalse(detail.counterexample)

    def test_counterexample_requires_all_lengths_absent(self):
        detail = verify_with_rust_binary(self.verifier, petersen_graph(), count_cap=10)
        self.assertTrue(detail.has_c8)
        self.assertFalse(detail.counterexample)


@unittest.skipUnless(verifier_available(), "verifier_64 not built; run `make build-verifier`")
class TestFitness(unittest.TestCase):
    def test_no_credit_for_unchecked_tiers(self):
        """A candidate that failed to run must not earn tier bonuses."""
        broken = "def generate_graph(n):\n    raise RuntimeError('boom')\n"
        res = evaluate_graph_candidate(broken, test_ns=[10])
        self.assertLess(res.fitness, 0)
        self.assertEqual(res.details[0].clean_tiers, 0)

    def test_shallow_tier_beats_deep_improvement(self):
        """No C8 with many C16 must outrank one C8 with few C16.

        This is the ordering the old weighted score got backwards.
        """
        clean_c8 = GraphEvaluationDetail(
            n=32, counterexample=False, is_cubic=True, min_degree=3, max_degree=3,
            edges=48, girth=3, diameter=6, checked_lengths=[4, 8, 16, 32],
            counts={4: 0, 8: 0, 16: 424, 32: 19},
        )
        one_c8 = GraphEvaluationDetail(
            n=32, counterexample=False, is_cubic=True, min_degree=3, max_degree=3,
            edges=48, girth=3, diameter=6, checked_lengths=[4, 8, 16, 32],
            counts={4: 0, 8: 1, 16: 5, 32: 0},
        )
        self.assertGreater(score_detail(clean_c8), score_detail(one_c8))

    def test_disconnected_is_penalised(self):
        base = dict(
            n=8, counterexample=False, is_cubic=True, min_degree=3, max_degree=3,
            edges=12, girth=3, diameter=1, checked_lengths=[4, 8], counts={4: 3, 8: 0},
        )
        connected = GraphEvaluationDetail(connected=True, components=1, **base)
        split = GraphEvaluationDetail(connected=False, components=2, **base)
        self.assertGreater(score_detail(connected), score_detail(split))


class TestArchive(unittest.TestCase):
    def test_pow2_decade_buckets(self):
        self.assertEqual(pow2_decade(0), 0)
        self.assertEqual(pow2_decade(7), 1)
        self.assertEqual(pow2_decade(42), 2)
        self.assertEqual(pow2_decade(424), 3)
        self.assertEqual(pow2_decade(99999), 4)

    def test_archive_separates_candidates_by_cycle_count(self):
        """The old (girth, diameter, bipartite) grid collapsed every GPU candidate
        into a single niche."""
        archive = MapElitesArchive()
        a = GraphProgram(id="a", code="a", fitness=1.0, is_counterexample=False,
                         all_cubic=True, girth=3, pow2_cycle_total=424)
        b = GraphProgram(id="b", code="b", fitness=1.0, is_counterexample=False,
                         all_cubic=True, girth=3, pow2_cycle_total=5)
        self.assertTrue(archive.add(a))
        self.assertTrue(archive.add(b))
        self.assertEqual(archive.coverage(), 2)

    def test_higher_fitness_replaces_niche_occupant(self):
        archive = MapElitesArchive()
        weak = GraphProgram(id="weak", code="w", fitness=10.0, is_counterexample=False,
                            all_cubic=True, girth=3, pow2_cycle_total=100)
        strong = GraphProgram(id="strong", code="s", fitness=99.0, is_counterexample=False,
                              all_cubic=True, girth=3, pow2_cycle_total=100)
        archive.add(weak)
        self.assertTrue(archive.add(strong))
        self.assertEqual(archive.get_elites()[0].id, "strong")


class TestIslands(unittest.TestCase):
    def test_global_best_never_downgrades(self):
        """A cubic but low-scoring program must not displace a high-scoring one.

        The old ranking put `all_cubic` above `fitness`, so this exact case
        regressed the global best.
        """
        manager = GraphIslandManager(num_islands=2, max_population_per_island=4)
        strong = GraphProgram(id="strong", code="s", fitness=50000.0,
                              is_counterexample=False, all_cubic=False)
        weak_cubic = GraphProgram(id="weak", code="w", fitness=-500.0,
                                  is_counterexample=False, all_cubic=True)
        self.assertTrue(manager.update_global_best(strong))
        self.assertFalse(manager.update_global_best(weak_cubic))
        self.assertEqual(manager.global_best.id, "strong")

    def test_counterexample_outranks_everything(self):
        manager = GraphIslandManager(num_islands=1)
        strong = GraphProgram(id="strong", code="s", fitness=50000.0,
                              is_counterexample=False, all_cubic=True)
        winner = GraphProgram(id="winner", code="w", fitness=1.0,
                              is_counterexample=True, all_cubic=True)
        manager.update_global_best(strong)
        self.assertTrue(manager.update_global_best(winner))
        self.assertEqual(manager.global_best.id, "winner")

    def test_migration_moves_elites(self):
        manager = GraphIslandManager(num_islands=3, max_population_per_island=5)
        for i, island in enumerate(manager.islands):
            island.add(GraphProgram(id=f"p{i}", code=f"code{i}", fitness=float(i),
                                    is_counterexample=False, all_cubic=True))
        self.assertGreaterEqual(manager.migrate(num_migrants=1), 1)


class TestSeeding(unittest.TestCase):
    def test_candidate_generator_refuses_other_orders(self):
        """A saved candidate must not silently become a different graph at other n.

        Both runners used to wrap candidates in a generator that returned a Möbius
        ladder for every order but one, so multi-order evaluation scored an unrelated
        graph.
        """
        code = candidate_to_generator_code(4, [[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]])
        out = run_candidate_for_n(code, 4)
        self.assertEqual(out["n"], 4)
        with self.assertRaises(RuntimeError):
            run_candidate_for_n(code, 6)


class TestGenerators(unittest.TestCase):
    def test_seed_generators_are_cubic_and_simple(self):
        for name, code in get_seed_generators().items():
            with self.subTest(generator=name):
                g = run_candidate_for_n(code, 20)
                self.assertEqual(len(g["adj"]), 20)
                for u, nbrs in enumerate(g["adj"]):
                    self.assertEqual(len(nbrs), 3, f"{name}: vertex {u} has degree {len(nbrs)}")
                    self.assertEqual(len(set(nbrs)), 3, f"{name}: vertex {u} has a repeated edge")
                    self.assertNotIn(u, nbrs, f"{name}: vertex {u} has a self-loop")
                    for v in nbrs:
                        self.assertIn(u, g["adj"][v], f"{name}: edge {u}-{v} is not symmetric")

    @unittest.skipUnless(verifier_available(), "verifier_64 not built")
    def test_generalized_petersen_has_c8(self):
        res = evaluate_graph_candidate(GENERALIZED_PETERSEN_CODE, test_ns=[10])
        self.assertTrue(res.all_cubic)
        self.assertFalse(res.details[0].has_c4)
        self.assertTrue(res.details[0].has_c8)


class TestSatEncoder(unittest.TestCase):
    def test_degree_and_c4_clauses(self):
        encoder = Erdos64SatEncoder(8)
        encoder.encode_degree_3()
        encoder.encode_no_cycles_of_length(4)
        self.assertGreater(len(encoder.clauses), 10)

    def test_at_most_k_is_satisfied_only_below_the_bound(self):
        """The sequential-counter encoding must reject k+1 true literals."""
        encoder = Erdos64SatEncoder(6)
        vars_list = [encoder.get_var(0, v) for v in range(1, 6)]
        encoder.encode_at_most_k(vars_list, 2)
        # Any 3 of the 5 variables being true must be forbidden.
        for combo in permutations(vars_list, 3):
            assignment = {abs(v): False for v in vars_list}
            for v in combo:
                assignment[abs(v)] = True
            self.assertFalse(
                encoder.assignment_satisfies(assignment),
                f"at-most-2 wrongly allows {combo} to be true together",
            )

    def test_cycle_clauses_forbid_a_known_cycle(self):
        encoder = Erdos64SatEncoder(6)
        encoder.encode_no_cycles_of_length(4)
        assignment = {abs(encoder.get_var(u, v)): False
                      for u in range(6) for v in range(u + 1, 6)}
        for u, v in [(0, 1), (1, 2), (2, 3), (3, 0)]:
            assignment[abs(encoder.get_var(u, v))] = True
        self.assertFalse(encoder.assignment_satisfies(assignment))


if __name__ == "__main__":
    unittest.main()
