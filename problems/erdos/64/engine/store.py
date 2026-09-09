"""The run log and the Lean certificate export.

Both outlived the LLM synthesis loop they were written for: the SQLite tables record
whatever produced a candidate, and the certificate export turns a verified graph into a
Lean file. Neither calls a model.

`runs`, `programs`, `evaluations` and `discoveries` are created on demand, and
`init_db` migrates columns added after a database was first written, so an older
`results.db` keeps working.
"""

import datetime
import json
import logging
import sqlite3
from pathlib import Path

from .program import GraphProgram

logger = logging.getLogger("store")


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
