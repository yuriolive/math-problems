"""
LoongFlow PES Orchestrator for Erdős Problem #64.
Executes the Cognitive Loop (Plan -> Execute -> Summarize) to discover counterexamples.
Zero external API keys required (powered by local `agy -p`).
"""

import argparse
import logging
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
    from .pes_memory import EvolutionaryMemory
    from .planner import generate_plan
    from .executor import execute_plan
    from .summarizer import summarize_and_reflect
    from .baseline_graphs import get_seed_generators
    from .evaluator import evaluate_graph_code
except ImportError:
    from pes_memory import EvolutionaryMemory
    from planner import generate_plan
    from executor import execute_plan
    from summarizer import summarize_and_reflect
    from baseline_graphs import get_seed_generators
    from evaluator import evaluate_graph_code

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("LoongFlow")

def run_loongflow(
    iterations: int = 10,
    test_ns: list[int] = [32, 34, 36],
    timeout_sec: float = 60.0,
):
    print("=" * 70)
    print("🚀 LOONGFLOW COGNITIVE PES ENGINE (Erdős Problem #64)")
    print(f"Target Vertices: {test_ns} | Total PES Cycles: {iterations}")
    print("=" * 70)

    memory = EvolutionaryMemory()

    # 1. Seed the MAP-Elites archive with foundational graph families
    print("\n[Phase 0] Seeding MAP-Elites archive with foundational graph families...")
    seeds = get_seed_generators()
    for name, code in seeds.items():
        prog = evaluate_graph_code(code, program_id=f"seed_{name}", test_ns=test_ns)
        is_new = memory.map_elites.add(prog, prog.girth, prog.diameter, prog.bipartite)
        status = "✨ NEW NICHE" if is_new else "Existing"
        print(f"  • Seed '{name}': Fitness={prog.fitness:.1f}, Girth={prog.girth}, Diam={prog.diameter}, BP={prog.bipartite} [{status}]")

    # Load GPU Swarm elite candidate if available
    swarm_seed_path = Path(__file__).resolve().parent.parent / "cuda" / "best_swarm_graph.json"
    if swarm_seed_path.is_file():
        try:
            import json
            with open(swarm_seed_path, "r", encoding="utf-8") as f:
                swarm_data = json.load(f)
            adj = swarm_data.get("adj", [])
            code = f'''def generate_graph(n: int) -> dict:
    adj = {adj}
    if n == {len(adj)}:
        return {{"n": {len(adj)}, "adj": adj}}
    res = [[] for _ in range(n)]
    for i in range(n):
        res[i].extend([(i + 1) % n, (i - 1 + n) % n, (i + n // 2) % n])
    return {{"n": n, "adj": res}}
'''
            prog = evaluate_graph_code(code, program_id="gpu_swarm_elite_32", test_ns=test_ns)
            is_new = memory.map_elites.add(prog, prog.girth, prog.diameter, prog.bipartite)
            status = "✨ NEW NICHE" if is_new else "Existing"
            print(f"  • Seed 'gpu_swarm_elite_32': Fitness={prog.fitness:.1f}, Girth={prog.girth}, Diam={prog.diameter}, BP={prog.bipartite} [{status}]")
        except Exception as e:
            logger.warning("Could not load GPU swarm seed: %s", e)

    print(f"\nArchive populated with {memory.map_elites.coverage()} initial behavioral niches.")
    print(memory.get_recent_lessons(k=3))
    print("-" * 70)

    # 2. Main PES Cognitive Cycle
    for cycle in range(1, iterations + 1):
        print(f"\n🔄 === [CYCLE {cycle}/{iterations}] LoongFlow PES Loop ===")

        # Selection: Pick an elite with high fitness or high girth
        elites = memory.map_elites.get_elites()
        if not elites:
            print("No elites available in archive.")
            break

        # Bias toward elites with higher girth or higher fitness
        elites.sort(key=lambda p: (p.girth, p.fitness), reverse=True)
        parent = elites[0]
        print(f"🎯 Selected Parent: {parent.id} (Fitness: {parent.fitness:.1f}, Girth: {parent.girth}, Diam: {parent.diameter})")

        # ----------------- 1. PLAN -----------------
        t0 = time.time()
        print("\n🧠 [Step 1: PLAN] Formulating strategic mathematical blueprint...")
        try:
            blueprint = generate_plan(parent, memory, target_n=test_ns[0], timeout_sec=timeout_sec)
            plan_duration = time.time() - t0
            print(f"✅ Blueprint generated in {plan_duration:.1f}s:")
            for line in blueprint.splitlines()[:8]:
                print(f"   │ {line}")
            if len(blueprint.splitlines()) > 8:
                print("   │ ...")
        except Exception as e:
            logger.error("Planner step failed: %s", e)
            continue

        # ----------------- 2. EXECUTE -----------------
        t1 = time.time()
        print("\n⚙️  [Step 2: EXECUTE] Synthesizing generator code & verifying in Rust...")
        try:
            child, code = execute_plan(blueprint, parent, test_ns=test_ns, timeout_sec=timeout_sec)
            exec_duration = time.time() - t1
            print(f"✅ Executed & Verified in {exec_duration:.1f}s:")
            print(f"   │ Child Fitness: {child.fitness:.1f} (Cubic: {child.all_cubic}, Girth: {child.girth}, Diam: {child.diameter})")
            print(f"   │ Trace: {child.diagnostic_trace}")
            if child.cycle_witness:
                print(f"   │ Cycle Witness: {child.cycle_witness}")
        except Exception as e:
            logger.error("Executor step failed: %s", e)
            continue

        # Check for immediate counterexample discovery
        if child.is_counterexample:
            print("\n" + "🎉" * 35)
            print("🏆 UNPRECEDENTED MATHEMATICAL DISCOVERY! ERDŐS #64 COUNTEREXAMPLE FOUND!")
            print("🎉" * 35)
            print(f"\nWinning Program Code:\n{code}")
            break

        # ----------------- 3. SUMMARIZE -----------------
        t2 = time.time()
        print("\n🔬 [Step 3: SUMMARIZE] Abductive reflection & updating Evolutionary Memory...")
        try:
            summary_res = summarize_and_reflect(blueprint, child, memory, timeout_sec=timeout_sec)
            sum_duration = time.time() - t2
            niche_tag = "🌟 NEW MAP-ELITES NICHE CLAIMED!" if summary_res.get("is_elite") else "Existing niche"
            print(f"✅ Reflected in {sum_duration:.1f}s [{niche_tag}]:")
            print(f"   │ Distilled Lesson: {summary_res.get('lesson')}")
        except Exception as e:
            logger.error("Summarizer step failed: %s", e)

        print(f"\n📊 Evolutionary Memory: {memory.summary()}")
        print("-" * 70)

    print("\n🏁 LoongFlow run completed.")
    print(memory.map_elites.summary())

def main():
    parser = argparse.ArgumentParser(description="LoongFlow PES Evolutionary Engine for Erdős #64")
    parser.add_argument("--iterations", type=int, default=5, help="Number of PES cognitive cycles")
    parser.add_argument("--test-ns", type=str, default="32,34,36", help="Comma-separated vertex sizes")
    parser.add_argument("--timeout", type=float, default=90.0, help="Timeout in seconds for LLM calls")
    args = parser.parse_args()

    test_ns = [int(x.strip()) for x in args.test_ns.split(",") if x.strip()]
    run_loongflow(iterations=args.iterations, test_ns=test_ns, timeout_sec=args.timeout)

if __name__ == "__main__":
    main()
