import unittest
from pathlib import Path
from engine.baseline_graphs import GENERALIZED_PETERSEN_CODE, RING_CHORD_CODE
from engine.evaluator import evaluate_graph_candidate, find_verifier_binary
from engine.island import GraphIslandManager, GraphProgram
from sat.cnf_encoder import Erdos64SatEncoder

class TestErdos64Pipeline(unittest.TestCase):
    def test_verifier_binary_exists(self):
        verifier_path = find_verifier_binary()
        self.assertTrue(verifier_path.is_file())

    def test_evaluate_generalized_petersen(self):
        res = evaluate_graph_candidate(GENERALIZED_PETERSEN_CODE, test_ns=[10, 16])
        self.assertTrue(res.all_cubic)
        self.assertEqual(len(res.details), 2)
        # GP(5, 2) has no C4 (girth 5) but has C8
        self.assertFalse(res.details[0].has_c4)
        self.assertTrue(res.details[0].has_c8)

    def test_sat_encoder(self):
        encoder = Erdos64SatEncoder(8)
        encoder.encode_degree_3()
        encoder.encode_no_c4()
        self.assertGreater(len(encoder.clauses), 10)

    def test_island_manager_and_migration(self):
        manager = GraphIslandManager(num_islands=3, max_population_per_island=5)
        def mock_eval(code):
            from engine.evaluator import GraphEvaluationResult
            return GraphEvaluationResult(fitness=100.0, is_counterexample=False, all_cubic=True, details=[])

        manager.initialize_seeds(mock_eval)
        self.assertEqual(len(manager.islands), 3)

        novel = GraphProgram(
            id="novel_g1",
            code="def generate_graph(n): return {'n': n, 'adj': []}",
            fitness=300.0,
            is_counterexample=False,
            all_cubic=True,
            island_id=0,
            generation=1,
        )
        manager.islands[0].add(novel)
        migrated = manager.migrate(num_migrants=1)
        self.assertGreaterEqual(migrated, 1)

if __name__ == "__main__":
    unittest.main()
