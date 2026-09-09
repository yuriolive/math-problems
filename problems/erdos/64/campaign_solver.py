"""Multi-order search campaign for Erdős Problem #64.

Sweeps a list of vertex counts with the CUDA swarm, verifies every result with the
compiled Rust verifier, keeps a candidate file per order, and optionally interleaves
PES (Plan-Execute-Summarize) cycles driven by the local `agy` CLI.

Two rules this runner enforces, both of which the earlier version broke:

* A candidate file is only replaced when the new graph is LEXICOGRAPHICALLY better on
  the verified cycle profile (C4, C8, C16, C32, C64). The old code overwrote whenever
  C4 = C8 = 0, so saved candidates drifted sideways instead of improving.
* Throughput comes from the kernel's own count of evaluated moves, not from
  threads * iterations, which counted loop turns that never proposed a move.
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

from engine.agy_client import AgyError
from engine.evaluator import verify_with_rust_binary, find_verifier_binary
from engine.executor import execute_plan
from engine.planner import generate_plan
from engine.summarizer import summarize_and_reflect
from engine.pes_memory import EvolutionaryMemory
from engine.seeding import seed_archive_from_candidates, seed_archive_from_generators
from engine.main import init_db, log_program, export_lean_certificate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("CampaignSolver")

POW2_LENGTHS = (4, 8, 16, 32, 64)

# f(4) >= 54 means no cubic graph below 54 vertices avoids C4, C8 and C16 together, so
# no counterexample exists below 54. The campaign starts at that floor.
DEFAULT_ORDERS = [54, 56, 58, 60, 62]

# The CUDA kernel refuses n > 62 because it has no C64 tier.
MAX_GPU_ORDER = 62


def cycle_profile(detail) -> tuple:
    """Verified cycle counts as a comparable tuple, shortest length first."""
    return tuple(detail.counts.get(L, 0) for L in POW2_LENGTHS)


def run_gpu_swarm(
    n: int,
    iterations: int,
    seed_file: Path | None = None,
    threads: int = 10240,
    count_cap: int = 1000000,
) -> tuple[dict, float]:
    """Runs swarm_64 and returns (result, evaluated moves per second)."""
    exe = root_dir / "cuda" / "swarm_64.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"CUDA binary not found at {exe} (run cuda/build.bat)")

    cmd = [
        str(exe), str(n), str(iterations),
        "--threads", str(threads),
        "--count-cap", str(count_cap),
        "--json-only",
    ]
    if seed_file and seed_file.is_file():
        cmd.extend(["--seed-file", str(seed_file)])

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root_dir))
    # Exit 1 just means "no counterexample", which is the normal outcome.
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"swarm_64 failed (exit {proc.returncode}): {proc.stderr.strip()[:300]}")

    out = proc.stdout.strip()
    start, end = out.find("{"), out.rfind("}") + 1
    if start == -1 or end <= start:
        raise RuntimeError(f"swarm_64 emitted no JSON. stderr: {proc.stderr.strip()[:300]}")

    data = json.loads(out[start:end])
    moves = data.get("evaluated_moves", 0)
    duration_s = max(1e-3, data.get("duration_ms", 0.0) / 1000.0)
    return data, moves / duration_s


def save_if_better(candidate_path: Path, graph: dict, detail) -> bool:
    """Writes the candidate only if its verified profile is strictly better."""
    new_profile = cycle_profile(detail)

    if candidate_path.is_file():
        try:
            old = json.loads(candidate_path.read_text(encoding="utf-8"))
            old_profile = tuple(old.get("verified", {}).get(f"C{L}", 0) for L in POW2_LENGTHS)
            if "verified" not in old:
                # Older files carry no verified profile; re-verify before comparing.
                old_detail = verify_with_rust_binary(
                    find_verifier_binary(), {"n": old["n"], "adj": old["adj"]}, count_cap=1000
                )
                old_profile = cycle_profile(old_detail)
            if new_profile >= old_profile:
                logger.info(
                    "n=%d: keeping the existing candidate %s (new %s is not better)",
                    detail.n, old_profile, new_profile
                )
                return False
            logger.info("n=%d: improving candidate %s -> %s", detail.n, old_profile, new_profile)
        except Exception as e:
            logger.warning("Could not compare against %s (%s); overwriting.", candidate_path.name, e)

    payload = {
        "n": graph["n"],
        "adj": graph["adj"],
        "verified": {f"C{L}": detail.counts.get(L, 0) for L in POW2_LENGTHS if L <= graph["n"]},
        "capped": {f"C{L}": detail.capped.get(L, False) for L in POW2_LENGTHS if L <= graph["n"]},
        "is_cubic": detail.is_cubic,
        "connected": detail.connected,
        "girth": detail.girth,
        "counterexample": detail.counterexample,
        "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    candidate_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return True


def execute_campaign(
    target_ns: list[int] | None = None,
    swarm_iters: int = 50000,
    rounds: int = 3,
    run_pes: bool = True,
    threads: int = 10240,
    count_cap: int = 1000,
):
    target_ns = target_ns or list(DEFAULT_ORDERS)

    print("=" * 78)
    print("ERDOS PROBLEM #64 SEARCH CAMPAIGN")
    print(f"Orders: {target_ns} | Swarm iterations/thread: {swarm_iters} | Threads: {threads}")
    print("=" * 78)

    settled = [n for n in target_ns if n < 54]
    if settled:
        logger.warning(
            "Orders %s are below the f(4) >= 54 floor; no cubic counterexample can exist "
            "there.", settled
        )
    too_big = [n for n in target_ns if n > MAX_GPU_ORDER]
    if too_big:
        logger.warning("Orders %s exceed the kernel limit of %d and will be skipped.",
                       too_big, MAX_GPU_ORDER)
        target_ns = [n for n in target_ns if n <= MAX_GPU_ORDER]

    db_path = root_dir / "results.db"
    conn = init_db(db_path)
    run_id = f"campaign_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    with conn:
        conn.execute(
            "INSERT INTO runs (run_id, started_at, test_ns, num_islands, status) VALUES (?, ?, ?, ?, ?)",
            (run_id, datetime.datetime.now(datetime.timezone.utc).isoformat(),
             str(target_ns), len(target_ns), "RUNNING"),
        )

    verifier = find_verifier_binary()
    memory = EvolutionaryMemory()
    cuda_dir = root_dir / "cuda"
    formalization_dir = root_dir / "formalization"

    seed_archive_from_generators(memory, target_ns[:2], count_cap=count_cap)
    seed_archive_from_candidates(memory, cuda_dir, count_cap=count_cap)
    print(f"Archive holds {memory.map_elites.coverage()} behavioural niches.", flush=True)

    found_counterexample = False

    for rnd in range(1, rounds + 1):
        print(f"\n===== ROUND {rnd}/{rounds}: GPU SWARM SWEEP =====", flush=True)

        for n in target_ns:
            candidate_path = cuda_dir / f"best_swarm_n{n}.json"
            has_seed = candidate_path.is_file()
            mode = f"seeded from {candidate_path.name}" if has_seed else "stochastic start"

            print(f"\n[n={n}] running the swarm ({mode})...")
            try:
                g_data, mps = run_gpu_swarm(
                    n, iterations=swarm_iters,
                    seed_file=candidate_path if has_seed else None,
                    threads=threads,
                )
            except Exception as e:
                logger.error("Swarm failed at n=%d: %s", n, e)
                continue

            print(f"   GPU: best energy {g_data.get('best_energy')} | "
                  f"{mps / 1e6:.2f}M evaluated moves/s")

            detail = verify_with_rust_binary(
                verifier, {"n": g_data["n"], "adj": g_data["adj"]}, count_cap=count_cap
            )
            counts_str = ", ".join(
                f"C{L}={detail.counts[L]}{'+' if detail.capped.get(L) else ''}"
                for L in sorted(detail.counts)
            )
            print(f"   verifier: cubic={detail.is_cubic} connected={detail.connected} "
                  f"girth={detail.girth} | {counts_str}")

            if detail.is_cubic:
                save_if_better(candidate_path, g_data, detail)

            if detail.counterexample:
                print("\n" + "=" * 78)
                print(f"VERIFIER REPORTS A COUNTEREXAMPLE AT n={n}")
                print("Min degree >= 3 and no cycle at any power-of-two length <= n.")
                print("Re-verify independently before making any claim.")
                print("=" * 78)
                ce_file = cuda_dir / f"CANDIDATE_COUNTEREXAMPLE_n{n}.json"
                ce_file.write_text(json.dumps(g_data, indent=2), encoding="utf-8")

                from engine.island import GraphProgram
                prog = GraphProgram(
                    id=f"counterexample_n{n}",
                    code=f"# Counterexample adjacency at n={n}:\nadj = {g_data.get('adj')}",
                    fitness=100000.0,
                    is_counterexample=True,
                    all_cubic=detail.is_cubic,
                    connected=detail.connected,
                )
                export_lean_certificate(prog, formalization_dir, graph=g_data)
                found_counterexample = True
                break

        if found_counterexample:
            break

        if run_pes:
            print(f"\n===== ROUND {rnd}/{rounds}: PES COGNITIVE CYCLE =====")
            target_n = target_ns[(rnd - 1) % len(target_ns)]
            print(f"Targeting n={target_n}...")
            try:
                elites = memory.map_elites.get_elites()
                parent = max(elites, key=lambda p: p.fitness) if elites else None
                blueprint = generate_plan(parent, memory, target_n=target_n, timeout_sec=90.0)
                print("Blueprint:")
                for line in blueprint.splitlines()[:5]:
                    print(f"   | {line}")

                child, code = execute_plan(
                    blueprint, parent, test_ns=[target_n], timeout_sec=90.0, count_cap=count_cap
                )
                print(f"Synthesized: fitness {child.fitness:.1f} | cubic {child.all_cubic} | "
                      f"girth {child.girth}")

                if child.is_counterexample:
                    print("\nPES produced a graph the verifier calls a counterexample.")
                    export_lean_certificate(child, formalization_dir)
                    found_counterexample = True
                    break

                summary = summarize_and_reflect(blueprint, child, memory, timeout_sec=90.0)
                if summary.get("lesson"):
                    print(f"Lesson: {summary['lesson']}")
                log_program(conn, run_id, child)
            except AgyError as e:
                logger.warning("PES stage skipped, LLM unavailable: %s", e)
                run_pes = False
            except Exception as e:
                logger.error("PES stage failed: %s", e)

    with conn:
        conn.execute(
            "UPDATE runs SET status = ? WHERE run_id = ?",
            ("CANDIDATE_FOUND" if found_counterexample else "COMPLETED", run_id),
        )
    conn.close()
    print("\nCampaign finished.")


def main():
    parser = argparse.ArgumentParser(description="Erdos #64 search campaign")
    parser.add_argument("--orders", type=str, default=",".join(str(n) for n in DEFAULT_ORDERS),
                        help="orders to sweep; n <= 52 is provably empty (f(4) >= 54)")
    parser.add_argument("--iters", type=int, default=50000, help="swarm steps per thread")
    parser.add_argument("--rounds", type=int, default=3, help="campaign rounds")
    parser.add_argument("--threads", type=int, default=10240, help="CUDA threads")
    parser.add_argument("--count-cap", type=int, default=1000,
                        help="max cycles counted per length during verification")
    parser.add_argument("--no-pes", action="store_true", help="skip the LLM cycles")
    args = parser.parse_args()

    orders = [int(x.strip()) for x in args.orders.split(",") if x.strip()]
    execute_campaign(
        target_ns=orders,
        swarm_iters=args.iters,
        rounds=args.rounds,
        run_pes=not args.no_pes,
        threads=args.threads,
        count_cap=args.count_cap,
    )


if __name__ == "__main__":
    main()
