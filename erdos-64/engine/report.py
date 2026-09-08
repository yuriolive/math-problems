"""
Progress Report for Erdős Problem #64 Search.
"""

import sqlite3
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def generate_report(db_path: Path | None = None):
    if db_path is None:
        db_path = Path(__file__).resolve().parent.parent / "results.db"

    if not db_path.is_file():
        print(f"No results database found at {db_path}.")
        return

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    print("=" * 70)
    print("        ERDOS PROBLEM #64 (ERDOS-GYARFAS) SEARCH REPORT")
    print("=" * 70)

    runs = conn.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT 5").fetchall()
    print(f"\n[Recent Runs: {len(runs)}]")
    for r in runs:
        print(f" - Run ID: {r['run_id']} | Started: {r['started_at']} | test_ns: {r['test_ns']} | Status: {r['status']}")

    prog_count = conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    cubic_count = conn.execute("SELECT COUNT(*) FROM programs WHERE all_cubic = 1").fetchone()[0]
    counter_count = conn.execute("SELECT COUNT(*) FROM programs WHERE is_counterexample = 1").fetchone()[0]

    print(f"\n[Statistics]")
    print(f" - Total Graph Programs Evaluated: {prog_count}")
    print(f" - Valid Cubic Programs: {cubic_count}")
    print(f" - Counterexamples Found: {counter_count}")

    top_progs = conn.execute(
        """
        SELECT id, generation, island_id, fitness, all_cubic, is_counterexample, created_at
        FROM programs
        ORDER BY is_counterexample DESC, all_cubic DESC, fitness DESC
        LIMIT 10
        """
    ).fetchall()

    print(f"\n[Top 10 Ranked Programs]")
    print(f"{'Rank':<5} {'Program ID':<28} {'Fitness':<10} {'Cubic':<8} {'Counterexample':<16} {'Island':<8}")
    print("-" * 75)
    for idx, p in enumerate(top_progs, 1):
        ce = "YES 🎉" if p['is_counterexample'] else "No"
        cubic = "Yes" if p['all_cubic'] else "No"
        print(f"{idx:<5} {p['id']:<28} {p['fitness']:<10.1f} {cubic:<8} {ce:<16} {p['island_id']:<8}")

    print("\n" + "=" * 70)
    conn.close()

if __name__ == "__main__":
    generate_report()
