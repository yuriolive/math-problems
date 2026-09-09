"""Evolutionary memory: MAP-Elites archive plus a persistent lessons file.

Two things the earlier version got wrong and this one does not:

* A corrupt `lessons_learned.json` was silently replaced with the defaults, destroying
  every accumulated lesson. It is now preserved as a `.corrupt` sidecar and the error
  is raised to the caller.
* Lessons were stored verbatim from the LLM, which produced double-encoded UTF-8
  ("\\u00c2\\u00b1") and content-free entries. Text is repaired and empty lessons are
  refused on both write and read.
"""

import json
import logging
from pathlib import Path
from typing import Any

try:
    from .map_elites import MapElitesArchive
except ImportError:  # direct script execution
    from map_elites import MapElitesArchive

logger = logging.getLogger(__name__)

DEFAULT_LESSONS_FILE = Path(__file__).resolve().parent.parent / "lessons_learned.json"

DEFAULT_INITIAL_LESSONS = [
    {
        "family": "Generalized Petersen GP(n/2, k)",
        "failure_mode": "Star-to-ring chord resonance",
        "lesson": "Generalized Petersen graphs GP(n/2, k) close an 8-cycle whenever "
                  "2k = n/2 or k = 2. Chord steps must avoid divisors of the target "
                  "cycle lengths.",
        "cycle_len": 8,
    },
    {
        "family": "Chordal rings C_n plus chords (i, i+k)",
        "failure_mode": "Constant chord step symmetry",
        "lesson": "A uniform chord offset k creates 4-cycles when 2k = 4 or n-4 and "
                  "8-cycles when 2k = 8. Chords must be non-uniform or "
                  "affine-permuted.",
        "cycle_len": 4,
    },
    {
        "family": "Cayley graphs over abelian groups",
        "failure_mode": "Commutativity of generator paths",
        "lesson": "In any abelian Cayley graph the relation a*b*a^-1*b^-1 = 1 forces a "
                  "4-cycle. Only non-abelian groups can reach girth >= 5.",
        "cycle_len": 4,
    },
    {
        "family": "Bipartite cubic graphs",
        "failure_mode": "Even cycle abundance",
        "lesson": "Every cycle in a bipartite graph is even, so all 2^k lengths stay in "
                  "play. Exhaustive search up to n = 62 found no cubic bipartite graph "
                  "that even avoids C4, C8 and C16 together; treat the class as closed.",
        "cycle_len": 8,
    },
    {
        "family": "Cyclic and voltage lifts with modulus g = 2^a * u",
        "failure_mode": "Projection to the odd part discards the 2-adic congruence",
        "lesson": "Avoiding cycles modulo the odd part u proves nothing, because every "
                  "2^k with k >= a is 0 mod 2^a. Reason with the full modulus g and "
                  "enforce L + r != 0 mod 2^a for all closed fibre walks.",
        "cycle_len": 16,
    },
]


def _repair_text(value: Any) -> Any:
    """Undoes the common double-encoded UTF-8 mangling in LLM output."""
    if not isinstance(value, str):
        return value
    if "Â" in value or "â" in value:
        try:
            return value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
    return value


def _is_useful(entry: dict) -> bool:
    """Rejects entries that carry no transferable mathematical content."""
    lesson = (entry.get("lesson") or "").strip()
    if len(lesson) < 25:
        return False
    # The old fallback path wrote things like "Girth 0 reached, but cycle collision
    # occurred on path []..." which tells a future planner nothing.
    noise_markers = ("collision occurred on path []", "Girth 0 reached")
    return not any(marker in lesson for marker in noise_markers)


class EvolutionaryMemory:
    def __init__(self, lessons_path: Path = DEFAULT_LESSONS_FILE):
        self.lessons_path = lessons_path
        self.map_elites = MapElitesArchive()
        self.lessons: list[dict[str, Any]] = []
        self._load_lessons()

    def _load_lessons(self) -> None:
        if not self.lessons_path.exists():
            self.lessons = [dict(entry) for entry in DEFAULT_INITIAL_LESSONS]
            self._save_lessons()
            return

        try:
            raw = json.loads(self.lessons_path.read_text(encoding="utf-8"))
        except Exception as exc:
            # Never overwrite: keep the bytes so the lessons can be recovered by hand.
            backup = self.lessons_path.with_suffix(".corrupt.json")
            try:
                backup.write_bytes(self.lessons_path.read_bytes())
            except OSError:
                pass
            raise RuntimeError(
                f"{self.lessons_path.name} is not valid JSON ({exc}). "
                f"A copy was kept at {backup.name}; fix or delete the original, "
                "it was NOT overwritten."
            ) from exc

        if not isinstance(raw, list):
            raise RuntimeError(f"{self.lessons_path.name} must contain a JSON array")

        cleaned = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            entry = {k: _repair_text(v) for k, v in entry.items()}
            if _is_useful(entry):
                cleaned.append(entry)

        self.lessons = cleaned
        if len(cleaned) != len(raw):
            logger.info(
                "Dropped %d uninformative or malformed lesson(s) while loading memory.",
                len(raw) - len(cleaned),
            )
            self._save_lessons()

    def _save_lessons(self) -> None:
        try:
            self.lessons_path.write_text(
                json.dumps(self.lessons, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.error("Failed to save lessons: %s", e)

    def add_lesson(self, family: str, failure_mode: str, lesson: str, cycle_len: int = 0) -> bool:
        """Appends a lesson. Returns False if it carried no usable content."""
        entry = {
            "family": _repair_text(family),
            "failure_mode": _repair_text(failure_mode),
            "lesson": _repair_text(lesson),
            "cycle_len": cycle_len,
        }
        if not _is_useful(entry):
            logger.info("Discarded an uninformative lesson: %r", lesson[:80])
            return False

        self.lessons.append(entry)
        self._save_lessons()
        logger.info("Recorded lesson: %s", entry["lesson"][:120])
        return True

    def get_recent_lessons(self, k: int = 4) -> str:
        recent = self.lessons[-k:] if len(self.lessons) >= k else self.lessons
        if not recent:
            return "(no lessons recorded yet)"
        lines = []
        for i, l in enumerate(recent, 1):
            cycle_str = f" [failed on C{l.get('cycle_len')}]" if l.get("cycle_len") else ""
            lines.append(f"{i}. [{l.get('family', 'General')}]{cycle_str}: {l.get('lesson')}")
        return "\n".join(lines)

    def summary(self) -> str:
        return (
            f"EvolutionaryMemory: {len(self.lessons)} persistent lessons | "
            f"{self.map_elites.coverage()} MAP-Elites niches occupied"
        )
