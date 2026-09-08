"""
Evolutionary Memory module for LoongFlow PES (Plan-Execute-Summarize) architecture.
Combines MAP-Elites Quality-Diversity archive with persistent Episodic Knowledge (Lessons Learned).
"""

import json
import logging
from pathlib import Path
from typing import Any
try:
    from .map_elites import MapElitesArchive, GraphProgram
except ImportError:
    from map_elites import MapElitesArchive, GraphProgram

logger = logging.getLogger(__name__)

DEFAULT_LESSONS_FILE = Path(__file__).resolve().parent.parent / "lessons_learned.json"

DEFAULT_INITIAL_LESSONS = [
    {
        "family": "Petersen Variants / GP(n/2, k)",
        "failure_mode": "Star-to-ring chord resonance",
        "lesson": "Generalized Petersen graphs GP(n/2, k) always close an 8-cycle when 2*k = n/2 or k = 2. Steps must avoid divisors of cycle lengths.",
        "cycle_len": 8
    },
    {
        "family": "Chordal Rings C_n + chords (i, i+k)",
        "failure_mode": "Constant chord step symmetry",
        "lesson": "Uniform constant chord offsets k create 4-cycles whenever 2*k = 4 or n-4, and 8-cycles whenever 2*k = 8. Chords must be non-uniform or affine-permuted.",
        "cycle_len": 4
    },
    {
        "family": "Cayley Graphs over Abelian Groups",
        "failure_mode": "Commutativity of generator paths",
        "lesson": "Any abelian group Cayley graph with generators a, b has a*b*a^(-1)*b^(-1) = 1, inevitably creating 4-cycles. Only non-abelian groups (e.g., A_4, S_4, dihedral with careful odd reflections) can have girth >= 5.",
        "cycle_len": 4
    },
    {
        "family": "Bipartite Cubic Graphs",
        "failure_mode": "Even cycle abundance",
        "lesson": "Every cycle in a bipartite graph has even length. Since bipartite cubic graphs have only even cycles, eliminating C4 and C8 is extraordinarily constrained; non-bipartite graphs provide vastly greater room to avoid 2^k cycles.",
        "cycle_len": 8
    }
]

class EvolutionaryMemory:
    def __init__(self, lessons_path: Path = DEFAULT_LESSONS_FILE):
        self.lessons_path = lessons_path
        self.map_elites = MapElitesArchive()
        self.lessons: list[dict[str, Any]] = []
        self._load_lessons()

    def _load_lessons(self):
        if self.lessons_path.exists():
            try:
                with open(self.lessons_path, "r", encoding="utf-8") as f:
                    self.lessons = json.load(f)
            except Exception as e:
                logger.warning("Could not read lessons file, initializing defaults: %s", e)
                self.lessons = list(DEFAULT_INITIAL_LESSONS)
                self._save_lessons()
        else:
            self.lessons = list(DEFAULT_INITIAL_LESSONS)
            self._save_lessons()

    def _save_lessons(self):
        try:
            with open(self.lessons_path, "w", encoding="utf-8") as f:
                json.dump(self.lessons, f, indent=2)
        except Exception as e:
            logger.error("Failed to save lessons: %s", e)

    def add_lesson(self, family: str, failure_mode: str, lesson: str, cycle_len: int = 0):
        entry = {
            "family": family,
            "failure_mode": failure_mode,
            "lesson": lesson,
            "cycle_len": cycle_len,
        }
        self.lessons.append(entry)
        self._save_lessons()
        logger.info("New lesson recorded into Evolutionary Memory: %s", lesson)

    def get_recent_lessons(self, k: int = 4) -> str:
        recent = self.lessons[-k:] if len(self.lessons) >= k else self.lessons
        lines = []
        for i, l in enumerate(recent, 1):
            cycle_str = f" [Failed on C{l.get('cycle_len', '?')}]" if l.get("cycle_len") else ""
            lines.append(f"{i}. [{l.get('family', 'General')}]{cycle_str}: {l.get('lesson')}")
        return "\n".join(lines)

    def summary(self) -> str:
        return f"EvolutionaryMemory: {len(self.lessons)} persistent lessons recorded | {self.map_elites.coverage()} MAP-Elites niches occupied"
