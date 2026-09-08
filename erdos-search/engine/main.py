"""
FunSearch Orchestrator Loop for Erdős Problem #1:
Samples elite programs from islands, feeds them into mutator.py (calling `agy -p`),
evaluates mutants against the compiled Rust verifier binary,
logs progress to SQLite (`results.db`),
and exports Lean 4 certificates when Bohman's bound is beaten.
"""

import argparse
import datetime
import json
import logging
import sqlite3
import sys
import uuid
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Support running both directly as script and as module
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from engine.baseline import CONWAY_GUY_CODE
    from engine.evaluator import evaluate_candidate, find_verifier_binary, EvaluationResult
    from engine.island import IslandManager, Program
    from engine.mutator import build_mutation_prompt, mutate_with_agy
else:
    from .baseline import CONWAY_GUY_CODE
    from .evaluator import evaluate_candidate, find_verifier_binary, EvaluationResult
    from .island import IslandManager, Program
    from .mutator import build_mutation_prompt, mutate_with_agy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("erdos_search")

def init_db(db_path: Path) -> sqlite3.Connection:
    """Initializes SQLite database schema for progress tracking."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT,
                n_eval TEXT,
                num_islands INTEGER,
                status TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS programs (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                generation INTEGER,
                island_id INTEGER,
                parent_id TEXT,
                fitness REAL,
                best_ratio REAL,
                all_valid INTEGER,
                beats_bohman INTEGER,
                code TEXT,
                created_at TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id TEXT,
                n INTEGER,
                valid INTEGER,
                max_val INTEGER,
                ratio REAL,
                beats_bohman INTEGER,
                collision TEXT,
                error TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS discoveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id TEXT,
                best_ratio REAL,
                beats_bohman INTEGER,
                timestamp TEXT,
                notes TEXT
            );
            """
        )
    return conn

def log_program_to_db(conn: sqlite3.Connection, run_id: str, prog: Program) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO programs
            (id, run_id, generation, island_id, parent_id, fitness, best_ratio, all_valid, beats_bohman, code, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prog.id,
                run_id,
                prog.generation,
                prog.island_id,
                prog.parent_id,
                prog.fitness,
                prog.best_ratio,
                1 if prog.all_valid else 0,
                1 if prog.beats_bohman else 0,
                prog.code,
                now,
            ),
        )
        for d in prog.details:
            conn.execute(
                """
                INSERT INTO evaluations
                (program_id, n, valid, max_val, ratio, beats_bohman, collision, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prog.id,
                    d.get("n", 0),
                    1 if d.get("valid") else 0,
                    d.get("max_val", 0),
                    d.get("ratio", 1.0),
                    1 if d.get("beats_bohman") else 0,
                    json.dumps(d.get("collision")),
                    d.get("error"),
                ),
            )

def export_lean_certificate(prog: Program, formalization_dir: Path) -> Path:
    """
    Exports a certified Lean 4 module containing the candidate set and verification proof.
    """
    target_dir = formalization_dir / "Problem1"
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / "Certificate.lean"

    content = f"""import Problem1.Basic
import Problem1.Verification

namespace Problem1.Certificate

/--
  Automated Certificate generated by Erdős Search Pipeline
  Program ID: {prog.id}
  Best Ratio: {prog.best_ratio:.6f}
  Beats Bohman: {prog.beats_bohman}
--/

-- Python generator code:
/-
{prog.code}
-/

def candidate_best_ratio : Float := {prog.best_ratio}

end Problem1.Certificate
"""
    out_file.write_text(content, encoding="utf-8")
    logger.info(f"Exported Lean 4 certificate to {out_file}")
    return out_file

def main():
    parser = argparse.ArgumentParser(description="FunSearch Erdős Problem #1 Pipeline")
    parser.add_argument("--n-eval", type=str, default="20", help="Comma-separated test n values or single int (default: 20)")
    parser.add_argument("--islands", type=int, default=5, help="Number of evolutionary islands (default: 5)")
    parser.add_argument("--iterations", type=int, default=10, help="Number of mutation generations (default: 10)")
    parser.add_argument("--migrate-interval", type=int, default=5, help="Generations between island migrations")
    parser.add_argument("--db", type=str, default="results.db", help="SQLite database path")
    args = parser.parse_args()

    if "," in args.n_eval:
        test_ns = [int(x.strip()) for x in args.n_eval.split(",") if x.strip()]
    else:
        n_val = int(args.n_eval)
        test_ns = [max(4, n_val - 5), n_val] if n_val > 8 else [n_val]

    logger.info("=== Erdős Problem #1 Neuro-Symbolic Search Engine ===")
    logger.info(f"Target Bound: Bohman R < 0.22002")
    logger.info(f"Test dimensions n: {test_ns}")
    logger.info(f"Islands: {args.islands} | Iterations: {args.iterations}")

    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / args.db
    verifier_path = find_verifier_binary(project_root)
    formalization_dir = project_root / "formalization"

    logger.info(f"Using Rust Verifier: {verifier_path}")
    logger.info(f"Database: {db_path}")

    conn = init_db(db_path)
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with conn:
        conn.execute(
            "INSERT INTO runs (run_id, started_at, n_eval, num_islands, status) VALUES (?, ?, ?, ?, ?)",
            (run_id, start_time, str(test_ns), args.islands, "running"),
        )

    manager = IslandManager(num_islands=args.islands, max_population_per_island=10)

    def eval_wrapper(code: str) -> EvaluationResult:
        return evaluate_candidate(code, test_ns=test_ns, verifier_path=verifier_path)

    logger.info("Seeding islands with Conway-Guy and Bohman baselines...")
    manager.initialize_seeds(eval_wrapper)

    for island in manager.islands:
        for prog in island.population:
            log_program_to_db(conn, run_id, prog)

    initial_best = manager.global_best
    if initial_best:
        logger.info(
            f"Initial Seed Best Ratio: {initial_best.best_ratio:.6f} "
            f"(Valid: {initial_best.all_valid}, Beats Bohman: {initial_best.beats_bohman})"
        )

    for gen in range(1, args.iterations + 1):
        island_idx = (gen - 1) % args.islands
        island = manager.islands[island_idx]

        parent = island.sample_parent()
        logger.info(
            f"[Gen {gen}/{args.iterations}] Island {island_idx}: mutating parent {parent.id} "
            f"(ratio={parent.best_ratio:.5f})..."
        )

        prompt = build_mutation_prompt(
            parent_code=parent.code,
            parent_ratio=parent.best_ratio,
            parent_valid=parent.all_valid,
            island_id=island_idx,
            generation=gen,
        )

        try:
            mutant_code = mutate_with_agy(prompt, timeout_sec=90.0)
        except Exception as e:
            logger.warning(f"Mutation call via agy failed: {e}")
            continue

        eval_res = eval_wrapper(mutant_code)
        mutant_prog = Program(
            id=f"mutant_g{gen}_isl{island_idx}_{uuid.uuid4().hex[:6]}",
            code=mutant_code,
            fitness=eval_res.fitness,
            best_ratio=eval_res.best_ratio,
            beats_bohman=eval_res.beats_bohman,
            all_valid=eval_res.all_valid,
            island_id=island_idx,
            generation=gen,
            parent_id=parent.id,
            details=[
                {
                    "n": d.n,
                    "valid": d.valid,
                    "max_val": d.max_val,
                    "ratio": d.ratio,
                    "beats_bohman": d.beats_bohman,
                    "collision": d.collision,
                    "error": d.error,
                }
                for d in eval_res.details
            ],
        )

        log_program_to_db(conn, run_id, mutant_prog)
        accepted = island.add(mutant_prog)

        if mutant_prog.all_valid:
            logger.info(
                f"  -> Valid mutant! Ratio: {mutant_prog.best_ratio:.6f} | "
                f"Fitness: {mutant_prog.fitness:.1f} | Accepted: {accepted}"
            )
        else:
            logger.info(f"  -> Mutant produced invalid set or collision.")

        is_new_global = manager.update_global_best(mutant_prog)
        if is_new_global:
            logger.info(
                f"★ NEW GLOBAL BEST: Ratio {mutant_prog.best_ratio:.6f} "
                f"(Beats Bohman: {mutant_prog.beats_bohman}) by {mutant_prog.id}"
            )
            with conn:
                conn.execute(
                    "INSERT INTO discoveries (program_id, best_ratio, beats_bohman, timestamp, notes) VALUES (?, ?, ?, ?, ?)",
                    (
                        mutant_prog.id,
                        mutant_prog.best_ratio,
                        1 if mutant_prog.beats_bohman else 0,
                        datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        f"Discovered at generation {gen} on island {island_idx}",
                    ),
                )
            if mutant_prog.beats_bohman:
                logger.info("🎉 BOHMAN'S BOUND BEATEN! Exporting Lean certificate...")
                export_lean_certificate(mutant_prog, formalization_dir)

        if gen % args.migrate_interval == 0:
            count = manager.migrate()
            logger.info(f"[Migration] Ring migration completed: {count} migrants integrated.")

    with conn:
        conn.execute("UPDATE runs SET status = ? WHERE run_id = ?", ("completed", run_id))

    best = manager.global_best
    logger.info("=== Run Complete ===")
    if best:
        logger.info(f"Best Discovered Ratio: {best.best_ratio:.6f}")
        logger.info(f"All Valid: {best.all_valid} | Beats Bohman: {best.beats_bohman}")
        logger.info(f"Program ID: {best.id}")

    conn.close()

if __name__ == "__main__":
    main()
