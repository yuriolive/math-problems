"""Island model for the Erdős #64 graph search."""

import random
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from engine.baseline_graphs import get_seed_generators
    from engine.evaluator import GraphEvaluationResult
else:
    from .baseline_graphs import get_seed_generators
    from .evaluator import GraphEvaluationResult


@dataclass
class GraphProgram:
    id: str
    code: str
    fitness: float
    is_counterexample: bool
    all_cubic: bool
    island_id: int = 0
    generation: int = 0
    parent_id: str | None = None
    details: list[dict[str, Any]] = field(default_factory=list)
    girth: int = 0
    diameter: int = 0
    bipartite: bool = False
    connected: bool = True
    pow2_cycle_total: int = 0
    diagnostic_trace: str = ""
    cycle_witness: list[int] | None = None


def _rank_key(p: GraphProgram) -> tuple:
    """Ranking key, best last (use with max / reverse sort).

    A verified counterexample outranks everything. Otherwise fitness decides -- being
    cubic is already worth CUBIC_BONUS inside fitness, so it must not be a separate
    higher-priority term. The old key ordered on (counterexample, all_cubic, fitness),
    which let a cubic candidate scoring -500 displace a non-cubic one scoring 50000.
    """
    return (1 if p.is_counterexample else 0, p.fitness)


class GraphIsland:
    def __init__(self, island_id: int, max_population: int = 10):
        self.island_id = island_id
        self.max_population = max_population
        self.population: list[GraphProgram] = []

    def add(self, program: GraphProgram) -> bool:
        for p in self.population:
            if p.code.strip() == program.code.strip():
                # Same generator: keep the better measurement, report no new member.
                if _rank_key(program) > _rank_key(p):
                    p.fitness = program.fitness
                    p.is_counterexample = program.is_counterexample
                    p.details = program.details
                return False

        self.population.append(program)
        self.population.sort(key=_rank_key, reverse=True)
        if len(self.population) > self.max_population:
            self.population = self.population[: self.max_population]
        return any(p is program for p in self.population)

    def sample_parent(self, tournament_size: int = 3) -> GraphProgram:
        if not self.population:
            raise ValueError(f"Island {self.island_id} is empty!")
        k = min(tournament_size, len(self.population))
        tournament = random.sample(self.population, k)
        return max(tournament, key=_rank_key)

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
        for name, code in get_seed_generators().items():
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
                            "girth": d.girth,
                            "diameter": d.diameter,
                            "connected": d.connected,
                            "bipartite": d.bipartite,
                            "checked_lengths": d.checked_lengths,
                            "counts": d.counts,
                            "has_c4": d.has_c4,
                            "has_c8": d.has_c8,
                            "has_c16": d.has_c16,
                            "has_c32": d.has_c32,
                            "has_c64": d.has_c64,
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
        if _rank_key(program) > _rank_key(self.global_best):
            self.global_best = program
            return True
        return False

    def migrate(self, num_migrants: int = 1) -> int:
        """Ring migration: island i sends its elite to island i+1."""
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
                    girth=migrant.girth,
                    diameter=migrant.diameter,
                    bipartite=migrant.bipartite,
                    connected=migrant.connected,
                    pow2_cycle_total=migrant.pow2_cycle_total,
                )
                if self.islands[target_idx].add(new_prog):
                    migrated_count += 1

        return migrated_count
