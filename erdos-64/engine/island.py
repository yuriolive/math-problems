"""
Island model for Erdős Problem #64 graph evolutionary search.
"""

import random
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from engine.baseline_graphs import GENERALIZED_PETERSEN_CODE, RING_CHORD_CODE
    from engine.evaluator import GraphEvaluationResult
else:
    from .baseline_graphs import GENERALIZED_PETERSEN_CODE, RING_CHORD_CODE
    from .evaluator import GraphEvaluationResult

@dataclass
class GraphProgram:
    id: str
    code: str
    fitness: float
    is_counterexample: bool
    all_cubic: bool
    island_id: int
    generation: int
    parent_id: str | None = None
    details: list[dict[str, Any]] = field(default_factory=list)

class GraphIsland:
    def __init__(self, island_id: int, max_population: int = 10):
        self.island_id = island_id
        self.max_population = max_population
        self.population: list[GraphProgram] = []

    def add(self, program: GraphProgram) -> bool:
        for p in self.population:
            if p.code.strip() == program.code.strip():
                if program.fitness > p.fitness:
                    p.fitness = program.fitness
                return False

        self.population.append(program)
        self.population.sort(
            key=lambda p: (
                1 if p.is_counterexample else 0,
                1 if p.all_cubic else 0,
                p.fitness,
            ),
            reverse=True,
        )
        if len(self.population) > self.max_population:
            self.population = self.population[: self.max_population]
        return program in self.population

    def sample_parent(self, tournament_size: int = 3) -> GraphProgram:
        if not self.population:
            raise ValueError(f"Island {self.island_id} is empty!")
        k = min(tournament_size, len(self.population))
        tournament = random.sample(self.population, k)
        return max(tournament, key=lambda p: (1 if p.is_counterexample else 0, 1 if p.all_cubic else 0, p.fitness))

    def get_elite(self, k: int = 1) -> list[GraphProgram]:
        return self.population[:k]

    def best_program(self) -> GraphProgram | None:
        return self.population[0] if self.population else None

    def __len__(self) -> int:
        return len(self.population)

class GraphIslandManager:
    def __init__(self, num_islands: int = 5, max_population_per_island: int = 10):
        self.num_islands = num_islands
        self.islands: list[GraphIsland] = [
            GraphIsland(i, max_population=max_population_per_island)
            for i in range(num_islands)
        ]
        self.global_best: GraphProgram | None = None

    def initialize_seeds(self, evaluate_fn) -> None:
        seeds = [
            ("generalized_petersen", GENERALIZED_PETERSEN_CODE),
            ("ring_chord", RING_CHORD_CODE),
        ]
        for name, code in seeds:
            eval_res: GraphEvaluationResult = evaluate_fn(code)
            for island in self.islands:
                prog = GraphProgram(
                    id=f"seed_{name}_{uuid.uuid4().hex[:6]}",
                    code=code,
                    fitness=eval_res.fitness,
                    is_counterexample=eval_res.is_counterexample,
                    all_cubic=eval_res.all_cubic,
                    island_id=island.island_id,
                    generation=0,
                    parent_id=None,
                    details=[
                        {
                            "n": d.n,
                            "counterexample": d.counterexample,
                            "is_cubic": d.is_cubic,
                            "has_c4": d.has_c4,
                            "has_c8": d.has_c8,
                            "has_c16": d.has_c16,
                            "has_c32": d.has_c32,
                            "power_of_two_cycle_count": d.power_of_two_cycle_count,
                        }
                        for d in eval_res.details
                    ],
                )
                island.add(prog)
                self.update_global_best(prog)

    def update_global_best(self, program: GraphProgram) -> bool:
        if self.global_best is None:
            self.global_best = program
            return True

        if program.is_counterexample and not self.global_best.is_counterexample:
            self.global_best = program
            return True

        if program.all_cubic and not self.global_best.all_cubic:
            self.global_best = program
            return True

        if program.fitness > self.global_best.fitness:
            self.global_best = program
            return True

        return False

    def migrate(self, num_migrants: int = 1) -> int:
        migrated_count = 0
        migrants = [island.get_elite(num_migrants) for island in self.islands]

        for i in range(self.num_islands):
            target_idx = (i + 1) % self.num_islands
            for migrant in migrants[i]:
                new_prog = GraphProgram(
                    id=f"migrant_{migrant.id}_{uuid.uuid4().hex[:4]}",
                    code=migrant.code,
                    fitness=migrant.fitness,
                    is_counterexample=migrant.is_counterexample,
                    all_cubic=migrant.all_cubic,
                    island_id=target_idx,
                    generation=migrant.generation,
                    parent_id=migrant.id,
                    details=migrant.details,
                )
                if self.islands[target_idx].add(new_prog):
                    migrated_count += 1

        return migrated_count
