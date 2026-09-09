"""
Island-model orchestrator for Erdős Problem #64:
- MAP-Elites archive keyed on (girth, 2^k-cycle-count decade, bipartite).
- Artifact Side-Channel (passes exact failing cycle witnesses to LLM mutator).
- Multi-island migration topology.
- Non-interactive `agy -p` mutations with zero API keys.
- Lean 4 certificate generation on counterexample discovery.
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

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from engine.evaluator import evaluate_graph_candidate, find_verifier_binary, GraphEvaluationResult
    from engine.island import GraphIslandManager, GraphProgram
    from engine.map_elites import MapElitesArchive
    from engine.mutator import build_graph_mutation_prompt, mutate_with_agy
else:
    from .evaluator import evaluate_graph_candidate, find_verifier_binary, GraphEvaluationResult
    from .island import GraphIslandManager, GraphProgram
    from .map_elites import MapElitesArchive
    from .mutator import build_graph_mutation_prompt, mutate_with_agy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("islands_64")

def init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT,
                test_ns TEXT,
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
                is_counterexample INTEGER,
                all_cubic INTEGER,
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
                counterexample INTEGER,
                is_cubic INTEGER,
                girth INTEGER,
                diameter INTEGER,
                connected INTEGER,
                components INTEGER,
                bipartite INTEGER,
                checked_lengths TEXT,
                counts TEXT,
                has_c4 INTEGER,
                has_c8 INTEGER,
                has_c16 INTEGER,
                has_c32 INTEGER,
                has_c64 INTEGER,
                diagnostic TEXT,
                error TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS discoveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id TEXT,
                fitness REAL,
                is_counterexample INTEGER,
                timestamp TEXT,
                notes TEXT
            );
            """
        )
        # Self-healing migration for databases created by earlier versions.
        cur = conn.cursor()
        existing = [c[1] for c in cur.execute("PRAGMA table_info(evaluations)").fetchall()]
        for col, ctype in [
            ("girth", "INTEGER"),
            ("diameter", "INTEGER"),
            ("connected", "INTEGER"),
            ("components", "INTEGER"),
            ("bipartite", "INTEGER"),
            ("checked_lengths", "TEXT"),
            ("counts", "TEXT"),
            ("has_c64", "INTEGER"),
            ("diagnostic", "TEXT"),
        ]:
            if col not in existing:
                cur.execute(f"ALTER TABLE evaluations ADD COLUMN {col} {ctype}")
    return conn

def log_program(conn: sqlite3.Connection, run_id: str, prog: GraphProgram):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO programs
            (id, run_id, generation, island_id, parent_id, fitness, is_counterexample, all_cubic, code, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prog.id,
                run_id,
                prog.generation,
                prog.island_id,
                prog.parent_id,
                prog.fitness,
                1 if prog.is_counterexample else 0,
                1 if prog.all_cubic else 0,
                prog.code,
                now,
            ),
        )
        for d in prog.details:
            conn.execute(
                """
                INSERT INTO evaluations
                (program_id, n, counterexample, is_cubic, girth, diameter, connected,
                 components, bipartite, checked_lengths, counts,
                 has_c4, has_c8, has_c16, has_c32, has_c64, diagnostic, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prog.id,
                    d.get("n", 0),
                    1 if d.get("counterexample") else 0,
                    1 if d.get("is_cubic") else 0,
                    d.get("girth", 0),
                    d.get("diameter", 0),
                    1 if d.get("connected", True) else 0,
                    d.get("components", 1),
                    1 if d.get("bipartite") else 0,
                    json.dumps(d.get("checked_lengths", [])),
                    # Exact counts per length. Storing these is what makes it possible
                    # to tell "absent" from "never checked" after the fact.
                    json.dumps({str(k): v for k, v in (d.get("counts") or {}).items()}),
                    1 if d.get("has_c4") else 0,
                    1 if d.get("has_c8") else 0,
                    1 if d.get("has_c16") else 0,
                    1 if d.get("has_c32") else 0,
                    1 if d.get("has_c64") else 0,
                    d.get("diagnostic_trace", ""),
                    d.get("error"),
                ),
            )

def export_lean_certificate(
    prog: GraphProgram,
    formalization_dir: Path,
    graph: dict | None = None,
) -> Path:
    """Writes a Lean file that actually checks something.

    The old version emitted the generator source inside a Lean comment and called it a
    certificate; nothing was stated, so nothing could be checked. This writes the
    adjacency data as a `GraphData` term plus `by decide` goals for the structural
    facts and the short cycle lengths, and lists the remaining lengths as explicit
    obligations discharged by the Rust verifier. It never writes `sorry`.

    Written next to `Certificate.lean` (which holds the self-tests) as
    `Candidate.lean`, so a generated file can never clobber the template.
    """
    target_dir = formalization_dir / "Problem64"
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / "Candidate.lean"

    if graph is None:
        graph = {}
    n = graph.get("n")
    adj = graph.get("adj")

    if not n or not adj:
        # No adjacency available: record the provenance honestly instead of
        # pretending to certify a graph nobody passed in.
        content = f"""import Problem64.Basic

/-!
# Candidate record for {prog.id}

No adjacency list was supplied to `export_lean_certificate`, so there is nothing to
check here. This file records provenance only.

Fitness: {prog.fitness}
Cubic: {prog.all_cubic} | Counterexample per verifier: {prog.is_counterexample}

Generator source:
{prog.code}
-/
"""
        out_file.write_text(content, encoding="utf-8")
        logger.warning("Exported a provenance-only Lean record (no graph given): %s", out_file)
        return out_file

    pow2 = [L for L in (4, 8, 16, 32, 64) if L <= n]
    # Lengths the kernel can realistically evaluate by path enumeration.
    lean_checked = [L for L in pow2 if L <= 8]
    delegated = [L for L in pow2 if L > 8]

    adj_lean = "[" + ",\n            ".join(
        "[" + ", ".join(str(v) for v in neighbours) + "]" for neighbours in adj
    ) + "]"

    checked_thms = "\n".join(
        f"theorem candidate_no_c{L} : hasCycleOfLength candidate {L} = false := by decide"
        for L in lean_checked
    )
    delegated_lines = "\n".join(f"--   hasCycleOfLength candidate {L} = false" for L in delegated)

    content = f"""import Problem64.Basic

/-!
# Candidate for Erdős Problem #64

Program: {prog.id}
Reported by the Rust verifier as a counterexample: {prog.is_counterexample}

Kernel-checked below: well-formedness, 3-regularity, minimum degree, and the absence
of cycles of length {lean_checked}.

NOT checked in Lean: {delegated}. `hasCycleOfLength` enumerates simple paths, which is
infeasible in the kernel at these lengths for n = {n}. Those were checked by
`verifier_64 --full`, which is a trusted (not verified) component. Closing that gap is
required before this can be called a proof.
-/

namespace Problem64.Candidate

open Problem64

def candidate : GraphData :=
  {{ n := {n},
    adj := {adj_lean} }}

theorem candidate_wellFormed : candidate.wellFormed = true := by decide
theorem candidate_cubic : candidate.isCubic = true := by decide
theorem candidate_minDegree : candidate.minDegreeAtLeast 3 = true := by decide

{checked_thms}

-- Remaining obligations, discharged by verifier_64 and NOT by Lean:
{delegated_lines or "--   (none: every relevant length was checked above)"}
--
-- With those in hand, `Problem64.IsCounterexample candidate` follows and
-- `Problem64.not_conjecture_of_counterexample` converts it into a refutation.

end Problem64.Candidate
"""
    out_file.write_text(content, encoding="utf-8")
    logger.info("Exported Lean candidate certificate to %s", out_file)
    logger.info("Lean checks lengths %s; %s remain delegated to verifier_64.", lean_checked, delegated)
    return out_file

def main():
    parser = argparse.ArgumentParser(description="Island evolution engine for Erdos #64")
    parser.add_argument("--test-ns", type=str, default="36,38",
                        help="Comma-separated orders n to test (n <= 34 is already settled by exhaustive search)")
    parser.add_argument("--islands", type=int, default=5, help="Number of evolutionary islands")
    parser.add_argument("--iterations", type=int, default=10, help="Number of generations")
    parser.add_argument("--db", type=str, default="results.db", help="SQLite database path")
    args = parser.parse_args()

    test_ns = [int(x.strip()) for x in args.test_ns.split(",") if x.strip()]

    logger.info("=== Island evolution engine for Erdos Problem #64 ===")
    logger.info(f"Test dimensions n: {test_ns}")
    logger.info(f"Islands: {args.islands} | Iterations: {args.iterations}")

    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / args.db
    verifier_path = find_verifier_binary(project_root)
    formalization_dir = project_root / "formalization"

    conn = init_db(db_path)
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with conn:
        conn.execute(
            "INSERT INTO runs (run_id, started_at, test_ns, num_islands, status) VALUES (?, ?, ?, ?, ?)",
            (run_id, start_time, str(test_ns), args.islands, "running"),
        )

    # Initialize MAP-Elites Archive and Island Manager
    map_elites = MapElitesArchive()
    manager = GraphIslandManager(num_islands=args.islands, max_population_per_island=10)

    def eval_wrapper(code: str) -> GraphEvaluationResult:
        return evaluate_graph_candidate(code, test_ns=test_ns, verifier_path=verifier_path)

    logger.info("Seeding islands with baseline graph generators...")
    manager.initialize_seeds(eval_wrapper)

    for island in manager.islands:
        for p in island.population:
            log_program(conn, run_id, p)
            # Register in MAP-Elites
            for d in p.details:
                map_elites.add(p)

    initial_best = manager.global_best
    if initial_best:
        logger.info(f"Initial Best Fitness: {initial_best.fitness:.1f} (Cubic: {initial_best.all_cubic})")
        logger.info(f"Initial MAP-Elites Coverage: {map_elites.coverage()} niches.")

    last_diagnostic = ""

    for gen in range(1, args.iterations + 1):
        island_idx = (gen - 1) % args.islands
        island = manager.islands[island_idx]

        parent = island.sample_parent()
        logger.info(f"[Gen {gen}/{args.iterations}] Island {island_idx}: mutating parent {parent.id}...")

        # AlphaEvolve trace-reflective mutation prompt
        prompt = build_graph_mutation_prompt(
            parent_code=parent.code,
            parent_fitness=parent.fitness,
            island_id=island_idx,
            generation=gen,
            diagnostic_trace=last_diagnostic,
            target_ns=test_ns,
        )

        try:
            mutant_code = mutate_with_agy(prompt, timeout_sec=90.0)
        except Exception as e:
            logger.warning(f"Mutation call via agy failed: {e}")
            continue

        eval_res = eval_wrapper(mutant_code)
        last_diagnostic = eval_res.best_diagnostic

        mutant_prog = GraphProgram(
            id=f"mutant_g{gen}_isl{island_idx}_{uuid.uuid4().hex[:6]}",
            code=mutant_code,
            fitness=eval_res.fitness,
            is_counterexample=eval_res.is_counterexample,
            all_cubic=eval_res.all_cubic,
            island_id=island_idx,
            generation=gen,
            parent_id=parent.id,
            details=[
                {
                    "n": d.n,
                    "counterexample": d.counterexample,
                    "is_cubic": d.is_cubic,
                    "min_degree": d.min_degree,
                    "max_degree": d.max_degree,
                    "edges": d.edges,
                    "girth": d.girth,
                    "diameter": d.diameter,
                    "connected": d.connected,
                    "components": d.components,
                    "bipartite": d.bipartite,
                    "checked_lengths": d.checked_lengths,
                    "counts": d.counts,
                    "has_c4": d.has_c4,
                    "has_c8": d.has_c8,
                    "has_c16": d.has_c16,
                    "has_c32": d.has_c32,
                    "has_c64": d.has_c64,
                    "power_of_two_cycle_count": d.power_of_two_cycle_count,
                    "diagnostic_trace": d.diagnostic_trace,
                    "error": d.error,
                }
                for d in eval_res.details
            ],
        )

        log_program(conn, run_id, mutant_prog)
        accepted = island.add(mutant_prog)

        # Register in MAP-Elites
        niche_improved = False
        for d in eval_res.details:
            if map_elites.add(mutant_prog):
                niche_improved = True

        logger.info(
            f"  -> Mutant fitness: {mutant_prog.fitness:.1f} | Cubic: {mutant_prog.all_cubic} | "
            f"Niche improved: {niche_improved} | Diagnostic: {eval_res.best_diagnostic[:60]}"
        )

        is_new_global = manager.update_global_best(mutant_prog)
        if is_new_global:
            logger.info(f"★ NEW GLOBAL BEST: Fitness {mutant_prog.fitness:.1f} by {mutant_prog.id}")
            with conn:
                conn.execute(
                    "INSERT INTO discoveries (program_id, fitness, is_counterexample, timestamp, notes) VALUES (?, ?, ?, ?, ?)",
                    (
                        mutant_prog.id,
                        mutant_prog.fitness,
                        1 if mutant_prog.is_counterexample else 0,
                        datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        f"Discovered at generation {gen} on island {island_idx}",
                    ),
                )
            if mutant_prog.is_counterexample:
                logger.info(
                    "Verifier reports no power-of-two cycle. Exporting the Lean candidate; "
                    "re-verify independently before making any claim."
                )
                graph = None
                try:
                    from engine.evaluator import run_candidate_for_n
                    graph = run_candidate_for_n(mutant_prog.code, test_ns[0])
                except Exception as e:
                    logger.warning("Could not regenerate the graph for the certificate: %s", e)
                export_lean_certificate(mutant_prog, formalization_dir, graph=graph)

        if gen % 5 == 0:
            count = manager.migrate()
            logger.info(f"[Migration] Ring migration integrated {count} programs. MAP-Elites niches: {map_elites.coverage()}")

    with conn:
        conn.execute("UPDATE runs SET status = ? WHERE run_id = ?", ("completed", run_id))

    best = manager.global_best
    logger.info("=== Run Complete ===")
    if best:
        logger.info(f"Best Discovered Fitness: {best.fitness:.1f}")
        logger.info(f"Cubic: {best.all_cubic} | Counterexample: {best.is_counterexample}")
    logger.info(map_elites.summary())

    conn.close()

if __name__ == "__main__":
    main()
