"""
Island Evolutionary Model for FunSearch:
Maintains distinct evolutionary islands storing candidate programs ranked by fitness and ratio R.
Implements periodic migration between islands in a ring topology.
"""

import random
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from engine.baseline import CONWAY_GUY_CODE, BOHMAN_RANDOMIZED_CODE
    from engine.evaluator import EvaluationResult
else:
    from .baseline import CONWAY_GUY_CODE, BOHMAN_RANDOMIZED_CODE
    from .evaluator import EvaluationResult

@dataclass
class Program:
    id: str
    code: str
    fitness: float
    best_ratio: float
    beats_bohman: bool
    all_valid: bool
    island_id: int
    generation: int
    parent_id: str | None = None
    details: list[dict[str, Any]] = field(default_factory=list)

class Island:
    def __init__(self, island_id: int, max_population: int = 10):
        self.island_id = island_id
        self.max_population = max_population
        self.population: list[Program] = []

    def add(self, program: Program) -> bool:
        """
        Adds a candidate program to the island.
        Keeps population sorted by fitness (descending), best_ratio (ascending).
        Returns True if program made it into the top population.
        """
        # Avoid duplicate code in the same island
        for p in self.population:
            if p.code.strip() == program.code.strip():
                if program.fitness > p.fitness:
                    p.fitness = program.fitness
                    p.best_ratio = program.best_ratio
                return False

        self.population.append(program)
        # Sort: valid first, highest fitness, lowest best_ratio
        self.population.sort(
            key=lambda p: (
                1 if p.all_valid else 0,
                p.fitness,
                -p.best_ratio,
            ),
            reverse=True,
        )

        if len(self.population) > self.max_population:
            self.population = self.population[: self.max_population]

        return program in self.population

    def sample_parent(self, tournament_size: int = 3) -> Program:
        """
        Samples a parent using tournament selection.
        """
        if not self.population:
            raise ValueError(f"Island {self.island_id} is empty!")
        k = min(tournament_size, len(self.population))
        tournament = random.sample(self.population, k)
        return max(tournament, key=lambda p: (1 if p.all_valid else 0, p.fitness, -p.best_ratio))

    def get_elite(self, k: int = 1) -> list[Program]:
        return self.population[:k]

    def best_program(self) -> Program | None:
        return self.population[0] if self.population else None

    def __len__(self) -> int:
        return len(self.population)

class IslandManager:
    def __init__(self, num_islands: int = 5, max_population_per_island: int = 10):
        self.num_islands = num_islands
        self.islands: list[Island] = [
            Island(i, max_population=max_population_per_island)
            for i in range(num_islands)
        ]
        self.global_best: Program | None = None

    def initialize_seeds(self, evaluate_fn) -> None:
        """
        Seeds each island with baseline programs (Conway-Guy and Bohman variants).
        """
        seeds = [
            ("conway_guy", CONWAY_GUY_CODE),
            ("bohman_randomized", BOHMAN_RANDOMIZED_CODE),
        ]

        for name, code in seeds:
            eval_res: EvaluationResult = evaluate_fn(code)
            for island in self.islands:
                prog = Program(
                    id=f"seed_{name}_{uuid.uuid4().hex[:6]}",
                    code=code,
                    fitness=eval_res.fitness,
                    best_ratio=eval_res.best_ratio,
                    beats_bohman=eval_res.beats_bohman,
                    all_valid=eval_res.all_valid,
                    island_id=island.island_id,
                    generation=0,
                    parent_id=None,
                    details=[
                        {
                            "n": d.n,
                            "valid": d.valid,
                            "max_val": d.max_val,
                            "ratio": d.ratio,
                            "beats_bohman": d.beats_bohman,
                        }
                        for d in eval_res.details
                    ],
                )
                island.add(prog)
                self.update_global_best(prog)

    def update_global_best(self, program: Program) -> bool:
        """
        Updates global best if the new program achieves a better ratio or fitness.
        """
        if self.global_best is None:
            self.global_best = program
            return True

        curr_valid = self.global_best.all_valid
        new_valid = program.all_valid

        if new_valid and not curr_valid:
            self.global_best = program
            return True
        elif new_valid and curr_valid:
            if program.best_ratio < self.global_best.best_ratio:
                self.global_best = program
                return True
        elif not new_valid and not curr_valid:
            if program.fitness > self.global_best.fitness:
                self.global_best = program
                return True

        return False

    def migrate(self, num_migrants: int = 1) -> int:
        """
        Performs periodic migration between islands in a ring topology:
        Island i sends its top migrant to Island (i + 1) % num_islands.
        """
        migrated_count = 0
        migrants: list[list[Program]] = []
        for island in self.islands:
            migrants.append(island.get_elite(num_migrants))

        for i in range(self.num_islands):
            target_idx = (i + 1) % self.num_islands
            for migrant in migrants[i]:
                new_prog = Program(
                    id=f"migrant_{migrant.id}_{uuid.uuid4().hex[:4]}",
                    code=migrant.code,
                    fitness=migrant.fitness,
                    best_ratio=migrant.best_ratio,
                    beats_bohman=migrant.beats_bohman,
                    all_valid=migrant.all_valid,
                    island_id=target_idx,
                    generation=migrant.generation,
                    parent_id=migrant.id,
                    details=migrant.details,
                )
                if self.islands[target_idx].add(new_prog):
                    migrated_count += 1

        return migrated_count
