import unittest
from pathlib import Path
from engine.baseline import conway_guy_sequence, bohman_randomized, CONWAY_GUY_CODE
from engine.evaluator import evaluate_candidate, find_verifier_binary
from engine.mutator import mutate_with_agy
from engine.island import IslandManager, Program

class TestErdosPipeline(unittest.TestCase):
    def test_conway_guy_n4(self):
        s4 = conway_guy_sequence(4)
        self.assertEqual(s4, [3, 5, 6, 7])
        self.assertEqual(max(s4), 7)
        ratio = max(s4) / (2**4)
        self.assertAlmostEqual(ratio, 0.4375)

    def test_bohman_randomized_n4(self):
        s = bohman_randomized(4, seed=42)
        self.assertEqual(len(s), 4)
        self.assertTrue(all(x > 0 for x in s))
        # strictly increasing
        self.assertEqual(s, sorted(s))

    def test_evaluator_with_rust_binary(self):
        verifier_path = find_verifier_binary()
        self.assertTrue(verifier_path.exists())

        res = evaluate_candidate(CONWAY_GUY_CODE, test_ns=[4, 7], verifier_path=verifier_path)
        self.assertTrue(res.all_valid)
        self.assertEqual(len(res.details), 2)
        self.assertAlmostEqual(res.details[0].ratio, 0.4375)
        self.assertAlmostEqual(res.details[1].ratio, 44.0 / 128.0)

    def test_island_manager_and_migration(self):
        manager = IslandManager(num_islands=3, max_population_per_island=5)
        def mock_eval(code):
            from engine.evaluator import EvaluationResult
            return EvaluationResult(
                fitness=100.0,
                best_ratio=0.25,
                beats_bohman=False,
                all_valid=True,
                details=[],
            )

        manager.initialize_seeds(mock_eval)
        self.assertEqual(len(manager.islands), 3)

        # Add a unique mutated program to island 0
        novel_prog = Program(
            id="novel_1",
            code="def generate_set(n):\n    return [2**i for i in range(n)]",
            fitness=500.0,
            best_ratio=0.20,
            beats_bohman=True,
            all_valid=True,
            island_id=0,
            generation=1,
        )
        manager.islands[0].add(novel_prog)

        migrated = manager.migrate(num_migrants=1)
        self.assertGreaterEqual(migrated, 1)

if __name__ == "__main__":
    unittest.main()
