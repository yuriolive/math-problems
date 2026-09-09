"""PES orchestrator for Erdős Problem #64: Plan -> Execute -> Summarize.

The PES pattern (Plan, Execute, Summary) is borrowed from Baidu's LoongFlow agent
framework. LoongFlow itself is NOT a dependency of this project: the loop below is a
local reimplementation of the pattern that drives the `agy` CLI directly.
"""

import argparse
import logging
import random
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from .agy_client import AgyError
    from .pes_memory import EvolutionaryMemory
    from .planner import generate_plan
    from .executor import execute_plan
    from .summarizer import summarize_and_reflect
    from .seeding import seed_archive_from_candidates, seed_archive_from_generators
except ImportError:  # direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from engine.agy_client import AgyError
    from engine.pes_memory import EvolutionaryMemory
    from engine.planner import generate_plan
    from engine.executor import execute_plan
    from engine.summarizer import summarize_and_reflect
    from engine.seeding import seed_archive_from_candidates, seed_archive_from_generators

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PES")

# f(4) >= 54 means no cubic graph below 54 vertices avoids C4, C8 and C16 together, so
# no counterexample exists below 54 either. Defaults start at that floor.
DEFAULT_TEST_NS = [54, 56, 58]


def select_parent(memory: EvolutionaryMemory, rng: random.Random, tournament: int = 3):
    """Tournament selection over the archive.

    Deterministically taking the top elite (the previous behaviour) meant every cycle
    re-planned from the same parent and the loop could not explore.
    """
    elites = memory.map_elites.get_elites()
    if not elites:
        return None
    k = min(tournament, len(elites))
    contenders = rng.sample(elites, k)
    return max(contenders, key=lambda p: (1 if p.is_counterexample else 0, p.fitness))


def run_pes(
    iterations: int = 10,
    test_ns: list[int] | None = None,
    timeout_sec: float = 60.0,
    seed: int | None = None,
    count_cap: int = 1000,
):
    test_ns = test_ns or list(DEFAULT_TEST_NS)
    rng = random.Random(seed)

    print("=" * 70)
    print("PES COGNITIVE LOOP (Erdos Problem #64)")
    print(f"Target orders: {test_ns} | Cycles: {iterations}")
    print("=" * 70)

    memory = EvolutionaryMemory()
    root = Path(__file__).resolve().parent.parent

    print("\n[Phase 0] Seeding the MAP-Elites archive...")
    n_gen = seed_archive_from_generators(memory, test_ns, count_cap=count_cap)
    n_cand = seed_archive_from_candidates(memory, root / "cuda", count_cap=count_cap)
    print(f"  baseline families: {n_gen} niches | saved candidates: {n_cand} niches")
    print(f"Archive holds {memory.map_elites.coverage()} behavioural niches.")
    print(memory.get_recent_lessons(k=3))
    print("-" * 70)

    for cycle in range(1, iterations + 1):
        print(f"\n=== [CYCLE {cycle}/{iterations}] ===")

        parent = select_parent(memory, rng)
        if parent is None:
            print("Archive is empty; nothing to evolve from.")
            break
        print(
            f"Parent: {parent.id} (fitness {parent.fitness:.1f}, girth {parent.girth}, "
            f"2^k cycles {parent.pow2_cycle_total})"
        )

        # ---- 1. PLAN ----
        t0 = time.time()
        print("\n[1: PLAN] Formulating a blueprint...")
        try:
            blueprint = generate_plan(parent, memory, target_n=test_ns[0], timeout_sec=timeout_sec)
        except AgyError as e:
            logger.error("Planner unavailable: %s", e)
            break
        except Exception as e:
            logger.error("Planner step failed: %s", e)
            continue
        print(f"Blueprint in {time.time() - t0:.1f}s:")
        for line in blueprint.splitlines()[:8]:
            print(f"   | {line}")
        if len(blueprint.splitlines()) > 8:
            print("   | ...")

        # ---- 2. EXECUTE ----
        t1 = time.time()
        print("\n[2: EXECUTE] Synthesizing and verifying...")
        try:
            child, code = execute_plan(
                blueprint, parent, test_ns=test_ns, timeout_sec=timeout_sec, count_cap=count_cap
            )
        except AgyError as e:
            logger.error("Executor unavailable: %s", e)
            break
        except Exception as e:
            logger.error("Executor step failed: %s", e)
            continue
        print(f"Verified in {time.time() - t1:.1f}s:")
        print(
            f"   | fitness {child.fitness:.1f} | cubic {child.all_cubic} | "
            f"connected {child.connected} | girth {child.girth}"
        )
        print(f"   | {child.diagnostic_trace}")

        if child.is_counterexample:
            out = root / "cuda" / f"CANDIDATE_COUNTEREXAMPLE_n{test_ns[0]}.py"
            out.write_text(code, encoding="utf-8")
            print("\n" + "=" * 70)
            print("The verifier reports NO power-of-two cycle and min degree >= 3.")
            print(f"Generator written to {out}")
            print("Before claiming anything: re-verify with an independent tool, check")
            print("connectivity, and confirm every power-of-two length <= n was tested.")
            print("=" * 70)
            break

        # ---- 3. SUMMARIZE ----
        t2 = time.time()
        print("\n[3: SUMMARIZE] Reflecting into memory...")
        try:
            summary_res = summarize_and_reflect(blueprint, child, memory, timeout_sec=timeout_sec)
            tag = "new niche" if summary_res.get("is_elite") else "existing niche"
            print(f"Reflected in {time.time() - t2:.1f}s [{tag}]:")
            lesson = summary_res.get("lesson")
            print(f"   | lesson: {lesson}" if lesson else "   | no transferable lesson recorded")
        except AgyError as e:
            logger.warning("Summarizer unavailable: %s", e)
        except Exception as e:
            logger.error("Summarizer step failed: %s", e)

        print(f"\n{memory.summary()}")
        print("-" * 70)

    print("\nRun complete.")
    print(memory.map_elites.summary())


def main():
    parser = argparse.ArgumentParser(description="PES evolutionary engine for Erdos #64")
    parser.add_argument("--iterations", type=int, default=5, help="PES cycles to run")
    parser.add_argument(
        "--test-ns",
        type=str,
        default=",".join(str(x) for x in DEFAULT_TEST_NS),
        help="comma-separated orders; n <= 52 is provably empty (f(4) >= 54)",
    )
    parser.add_argument("--timeout", type=float, default=90.0, help="per-LLM-call timeout")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for parent selection")
    parser.add_argument(
        "--count-cap", type=int, default=1000,
        help="max cycles counted per length when verifying (1 = existence only)",
    )
    args = parser.parse_args()

    test_ns = [int(x.strip()) for x in args.test_ns.split(",") if x.strip()]
    settled = [n for n in test_ns if n < 54]
    if settled:
        logger.warning(
            "Orders %s are below the f(4) >= 54 floor, so no cubic counterexample exists "
            "there; they can only serve as warm-up.", settled
        )

    run_pes(
        iterations=args.iterations,
        test_ns=test_ns,
        timeout_sec=args.timeout,
        seed=args.seed,
        count_cap=args.count_cap,
    )


if __name__ == "__main__":
    main()
