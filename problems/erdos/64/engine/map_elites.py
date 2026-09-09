"""MAP-Elites quality-diversity archive for Erdős #64.

Behavioural descriptors matter here. The original grid was
(girth, diameter, bipartite), but every graph the GPU swarm produces has girth 3,
diameter 6-8 and is non-bipartite, so the whole archive collapsed into one or two
niches and provided no diversity pressure at all.

The descriptors used now spread the population along axes that actually vary for
cubic near-misses:

  * `girth`             3..8+, still useful for algebraically constructed candidates
  * `pow2_decade`       order of magnitude of the total power-of-two cycle count,
                        which is the quantity the search is trying to drive to zero
  * `bipartite`         kept: bipartite cubic graphs are a genuinely different regime
"""

from dataclasses import dataclass
from typing import Any

try:
    from .program import GraphProgram
except ImportError:  # direct script execution
    from program import GraphProgram


def pow2_decade(total_pow2_cycles: int) -> int:
    """Bucket a cycle total into 0, 1, 2, 3, 4 (0 / 1-9 / 10-99 / 100-999 / 1000+)."""
    if total_pow2_cycles <= 0:
        return 0
    decade = 1
    while total_pow2_cycles >= 10 and decade < 4:
        total_pow2_cycles //= 10
        decade += 1
    return decade


@dataclass
class NicheCoord:
    girth: int
    pow2_decade: int
    bipartite: bool

    def key(self) -> tuple[int, int, bool]:
        g = min(8, max(3, self.girth)) if self.girth > 0 else 0
        return (g, self.pow2_decade, self.bipartite)


def _rank_key(p: GraphProgram) -> tuple:
    return (1 if p.is_counterexample else 0, p.fitness)


class MapElitesArchive:
    def __init__(self):
        self.archive: dict[tuple[int, int, bool], GraphProgram] = {}
        self.total_evaluations = 0
        self.improvements = 0

    def add(
        self,
        prog: GraphProgram,
        girth: int | None = None,
        diameter: int | None = None,
        bipartite: bool | None = None,
        pow2_total: int | None = None,
    ) -> bool:
        """Insert `prog` into its niche, replacing a strictly worse occupant.

        `diameter` is accepted for backwards compatibility and ignored: it barely
        varied across candidates and cost a grid dimension.
        """
        self.total_evaluations += 1

        g = prog.girth if girth is None else girth
        bp = prog.bipartite if bipartite is None else bipartite
        total = prog.pow2_cycle_total if pow2_total is None else pow2_total

        coord = NicheCoord(girth=g, pow2_decade=pow2_decade(total), bipartite=bp).key()

        existing = self.archive.get(coord)
        if existing is None or _rank_key(prog) > _rank_key(existing):
            self.archive[coord] = prog
            self.improvements += 1
            return True
        return False

    def get_elites(self) -> list[GraphProgram]:
        return list(self.archive.values())

    def coverage(self) -> int:
        return len(self.archive)

    def summary(self) -> str:
        lines = [
            f"MAP-Elites Archive: {len(self.archive)} niches occupied "
            f"({self.improvements} niche improvements)"
        ]
        for (g, decade, bp), prog in sorted(self.archive.items()):
            bp_str = "Bipartite" if bp else "Non-bipartite"
            band = {0: "0", 1: "1-9", 2: "10-99", 3: "100-999", 4: "1000+"}[decade]
            lines.append(
                f" - [Girth {g}, 2^k-cycles {band}, {bp_str}]: "
                f"{prog.id} | Fitness {prog.fitness:.1f}"
            )
        return "\n".join(lines)
