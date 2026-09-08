"""
MAP-Elites (Multi-dimensional Archive of Phenotypic Elites) for Erdős Problem #64.
Inspired by AlphaEvolve and OpenEvolve Quality-Diversity algorithms.
Maintains diverse structural graph niches to avoid premature convergence.
"""

from dataclasses import dataclass
from typing import Any
from .island import GraphProgram

@dataclass
class NicheCoord:
    girth: int        # Girth niche: 3, 4, 5, 6, 7, 8+
    diameter: int     # Diameter niche: 2, 3, 4, 5, 6, 7+
    bipartite: bool   # Bipartite flag

    def key(self) -> tuple[int, int, bool]:
        g = min(8, max(3, self.girth)) if self.girth > 0 else 0
        d = min(7, max(2, self.diameter)) if self.diameter > 0 else 0
        return (g, d, self.bipartite)

class MapElitesArchive:
    def __init__(self):
        # Maps (girth_bin, diameter_bin, bipartite) -> GraphProgram
        self.archive: dict[tuple[int, int, bool], GraphProgram] = {}
        self.total_evaluations = 0
        self.improvements = 0

    def add(self, prog: GraphProgram, girth: int, diameter: int, bipartite: bool) -> bool:
        self.total_evaluations += 1
        coord = NicheCoord(girth=girth, diameter=diameter, bipartite=bipartite).key()

        if coord not in self.archive:
            self.archive[coord] = prog
            self.improvements += 1
            return True
        else:
            existing = self.archive[coord]
            # Replace if higher fitness or counterexample
            if prog.is_counterexample and not existing.is_counterexample:
                self.archive[coord] = prog
                self.improvements += 1
                return True
            elif prog.all_cubic and not existing.all_cubic:
                self.archive[coord] = prog
                self.improvements += 1
                return True
            elif prog.fitness > existing.fitness:
                self.archive[coord] = prog
                self.improvements += 1
                return True

        return False

    def get_elites(self) -> list[GraphProgram]:
        return list(self.archive.values())

    def coverage(self) -> int:
        return len(self.archive)

    def summary(self) -> str:
        lines = [f"MAP-Elites Archive: {len(self.archive)} niches occupied ({self.improvements} niche improvements)"]
        for (g, d, bp), prog in sorted(self.archive.items()):
            bp_str = "Bipartite" if bp else "Non-bipartite"
            lines.append(f" - [Girth {g}, Diam {d}, {bp_str}]: Program {prog.id} | Fitness {prog.fitness:.1f}")
        return "\n".join(lines)
