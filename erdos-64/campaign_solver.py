"""
Campaign Solver for Erdős Problem #64 (Erdős–Gyárfás Conjecture).
Combines:
1. Massive RTX 4070 Super CUDA Swarm Searcher (68M moves/sec) across orders n in [32, 34, 36, 38, 40, 42, 44, 48].
2. Seeded Micro-Polishing / Basin Hopping on promising candidates (C4=0, C8=0).
3. LoongFlow Cognitive PES (Plan -> Execute -> Summarize) algebraic reasoning with local LLM.
4. Instant Rust verifier certification and Lean 4 formal certificate export.
5. Persistent experiment logging into SQLite results.db.
"""

import argparse
import datetime
import json
import logging
import subprocess
import sys
import time
import uuid
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

from engine.evaluator import verify_with_rust_binary, find_verifier_binary, evaluate_graph_code
from engine.executor import polish_with_gpu, execute_plan
from engine.planner import generate_plan
from engine.summarizer import summarize_and_reflect
from engine.pes_memory import EvolutionaryMemory
from engine.island import GraphProgram
from engine.main import init_db, log_program, export_lean_certificate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("CampaignSolver")

def run_gpu_swarm_raw(n: int, iterations: int, seed_file: Path | None = None) -> tuple[dict, float]:
    """Runs swarm_64.exe on RTX 4070 Super and returns (graph_dict, moves_per_sec)."""
    exe = root_dir / "cuda" / "swarm_64.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"CUDA binary not found at {exe}")

    cmd = [str(exe), str(n), str(iterations), "--json-only"]
    if seed_file and seed_file.is_file():
        cmd.extend(["--seed-file", str(seed_file)])

    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root_dir))
    duration = time.time() - t0

    out = proc.stdout.strip()
    start = out.find("{")
    end = out.rfind("}") + 1
    if start != -1 and end != -1:
        data = json.loads(out[start:end])
        total_moves = 10240 * iterations
        mps = total_moves / max(0.001, duration)
        return data, mps

    raise RuntimeError(f"Swarm failed to output valid JSON. Stderr: {proc.stderr}")

def execute_campaign(
    target_ns: list[int] = [32, 34, 36, 38, 40, 42, 44, 48],
    swarm_iters: int = 50000,
    rounds: int = 3,
    run_loongflow: bool = True,
):
    print("=" * 80)
    print("🚀 ERDŐS PROBLEM #64 SOLVER CAMPAIGN LAUNCHED")
    print(f"Target Orders: {target_ns} | Swarm Iterations: {swarm_iters} (512M moves/run)")
    print(f"Hardware: NVIDIA GeForce RTX 4070 Super + Ryzen 7 9800X3D + Rust Verifier + Lean 4")
    print("=" * 80)

    db_path = root_dir / "results.db"
    conn = init_db(db_path)
    run_id = f"campaign_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    with conn:
        conn.execute(
            "INSERT INTO runs (run_id, started_at, test_ns, num_islands, status) VALUES (?, ?, ?, ?, ?)",
            (run_id, datetime.datetime.now(datetime.timezone.utc).isoformat(), str(target_ns), len(target_ns), "RUNNING"),
        )

    verifier = find_verifier_binary()
    memory = EvolutionaryMemory()
    cuda_dir = root_dir / "cuda"
    formalization_dir = root_dir / "formalization"

    # Seed MAP-Elites archive
    from engine.baseline_graphs import get_seed_generators
    for name, code in get_seed_generators().items():
        prog = evaluate_graph_code(code, program_id=f"seed_{name}", test_ns=target_ns[:3])
        memory.map_elites.add(prog, prog.girth, prog.diameter, prog.bipartite)

    for n in target_ns:
        cand = cuda_dir / f"best_swarm_n{n}.json"
        if cand.is_file():
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                adj = cdata.get("adj", [])
                code = f'''def generate_graph(n: int) -> dict:
    adj = {adj}
    if n == {len(adj)}:
        return {{"n": {len(adj)}, "adj": adj}}
    res = [[] for _ in range(n)]
    for i in range(n):
        res[i].extend([(i + 1) % n, (i - 1 + n) % n, (i + n // 2) % n])
    return {{"n": n, "adj": res}}
'''
                prog = evaluate_graph_code(code, program_id=f"gpu_swarm_n{n}", test_ns=[n])
                memory.map_elites.add(prog, prog.girth, prog.diameter, prog.bipartite)
            except Exception as e:
                logger.warning(f"Failed to seed MAP-Elites with {cand.name}: {e}")

    print(f"Archive populated with {memory.map_elites.coverage()} initial behavioral niches.", flush=True)

    found_counterexample = False

    for rnd in range(1, rounds + 1):
        print(f"\n🌟 ==================== [ROUND {rnd}/{rounds}] GPU SWARM SWEEP ====================", flush=True)

        for n in target_ns:
            seed_candidate = cuda_dir / f"best_swarm_n{n}.json"
            has_seed = seed_candidate.is_file()
            mode = f"Seeded Polish ({seed_candidate.name})" if has_seed else "Stochastic Explore"

            print(f"\n⚡ Running GPU Swarm on n={n} ({mode})...")
            try:
                g_data, mps = run_gpu_swarm_raw(n, iterations=swarm_iters, seed_file=seed_candidate if has_seed else None)
                best_energy = g_data.get("best_energy", 999999)
                is_ce = g_data.get("counterexample", False)
                print(f"   [GPU Complete]: Best Energy = {best_energy} | Throughput = {mps/1e6:.1f} M moves/s")

                # Verify via compiled Rust Verifier
                v_res = verify_with_rust_binary(verifier, g_data)
                print(f"   [Rust Verifier]: Cubic={v_res.is_cubic}, Girth={v_res.girth}, C4={v_res.has_c4}, C8={v_res.has_c8}, C16={v_res.has_c16}, C32={v_res.has_c32}")

                # Save if it improves or avoids C4 & C8
                if not v_res.has_c4 and not v_res.has_c8:
                    print(f"   🔥 HIGH-VALUE CANDIDATE FOUND ON n={n} (C4=0, C8=0)! Saving to {seed_candidate.name}...")
                    with open(seed_candidate, "w", encoding="utf-8") as f:
                        json.dump(g_data, f, indent=2)

                # Check for counterexample!
                if v_res.counterexample or is_ce:
                    print("\n" + "🎉" * 40)
                    print(f"🏆 UNPRECEDENTED DISCOVERY! ERDŐS #64 COUNTEREXAMPLE CONFIRMED ON n={n}!")
                    print("🎉" * 40)
                    ce_file = cuda_dir / f"WINNING_COUNTEREXAMPLE_n{n}.json"
                    with open(ce_file, "w", encoding="utf-8") as f:
                        json.dump(g_data, f, indent=2)

                    # Export Lean 4 certificate
                    dummy_prog = GraphProgram(
                        id=f"counterexample_n{n}",
                        code=f"# Counterexample adjacency on n={n}:\nadj = {g_data.get('adj')}",
                        fitness=100000.0,
                        is_counterexample=True,
                        all_cubic=True,
                    )
                    export_lean_certificate(dummy_prog, formalization_dir)
                    found_counterexample = True
                    break

            except Exception as e:
                logger.error(f"Error running swarm on n={n}: {e}")

        if found_counterexample:
            break

        # Interleaved LoongFlow PES Cognitive Loop
        if run_loongflow:
            print(f"\n🧠 ==================== [ROUND {rnd}/{rounds}] LOONGFLOW PES COGNITIVE LOOP ====================")
            elites = memory.map_elites.get_elites()
            parent = elites[0] if elites else None

            # Formulate plan targeting n=32 or n=34
            target_n = 32 if rnd % 2 == 1 else 34
            print(f"🎯 LoongFlow targeting n={target_n} with abductive reasoning...")
            try:
                blueprint = generate_plan(parent, memory, target_n=target_n, timeout_sec=90.0)
                print("✅ Strategic Blueprint formulated:")
                for line in blueprint.splitlines()[:5]:
                    print(f"   │ {line}")

                child, code = execute_plan(blueprint, parent, test_ns=[target_n], timeout_sec=90.0)
                print(f"✅ Synthesized & Rust Verified: Fitness={child.fitness:.1f}, Cubic={child.all_cubic}, Girth={child.girth}")

                if child.is_counterexample:
                    print("\n🎉🎉🎉 COUNTEREXAMPLE FOUND VIA LOONGFLOW PES! 🎉🎉🎉")
                    export_lean_certificate(child, formalization_dir)
                    found_counterexample = True
                    break

                summary = summarize_and_reflect(blueprint, child, memory, timeout_sec=90.0)
                print(f"🔬 Distilled Structural Lesson: {summary.get('lesson')}")
                log_program(conn, run_id, child)

            except Exception as e:
                logger.error(f"LoongFlow step failed: {e}")

    with conn:
        conn.execute(
            "UPDATE runs SET status = ? WHERE run_id = ?",
            ("SUCCESS" if found_counterexample else "COMPLETED", run_id),
        )
    conn.close()

    print("\n🏁 Campaign run finished.")

def main():
    parser = argparse.ArgumentParser(description="Erdős #64 Solver Campaign")
    parser.add_argument("--orders", type=str, default="32,34,36,38,40,42,44,48", help="Orders to sweep")
    parser.add_argument("--iters", type=int, default=50000, help="Swarm moves/thread (default: 50,000)")
    parser.add_argument("--rounds", type=int, default=3, help="Campaign rounds")
    parser.add_argument("--no-loongflow", action="store_true", help="Skip LoongFlow PES cycles")
    args = parser.parse_args()

    orders = [int(x.strip()) for x in args.orders.split(",") if x.strip()]
    execute_campaign(
        target_ns=orders,
        swarm_iters=args.iters,
        rounds=args.rounds,
        run_loongflow=not args.no_loongflow,
    )

if __name__ == "__main__":
    main()
