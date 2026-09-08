"""
Progress & Discovery Report Generator for Erdős Problem #1 Pipeline.
Queries SQLite results.db and prints a structured summary.
"""

import io
import sqlite3
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
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
        print(f"No results database found at {db_path}. Run a search first using 'make run'.")
        return

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    print("=" * 70)
    print("           ERDOS PROBLEM #1 DISCOVERY REPORT")
    print("=" * 70)

    # 1. Runs summary
    runs = conn.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT 5").fetchall()
    print(f"\n[Recent Runs: {len(runs)}]")
    for r in runs:
        print(f" - Run ID: {r['run_id']} | Started: {r['started_at']} | n_eval: {r['n_eval']} | Status: {r['status']}")

    # 2. Overall counts
    prog_count = conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    valid_count = conn.execute("SELECT COUNT(*) FROM programs WHERE all_valid = 1").fetchone()[0]
    bohman_count = conn.execute("SELECT COUNT(*) FROM programs WHERE beats_bohman = 1").fetchone()[0]

    print(f"\n[Search Statistics]")
    print(f" - Total Programs Evaluated: {prog_count}")
    print(f" - Valid Candidate Programs: {valid_count}")
    print(f" - Programs Beating Bohman's Bound (R < 0.22002): {bohman_count}")

    # 3. Top 10 Best Valid Programs
    top_progs = conn.execute(
        """
        SELECT id, generation, island_id, best_ratio, fitness, beats_bohman, created_at
        FROM programs
        WHERE all_valid = 1
        ORDER BY best_ratio ASC
        LIMIT 10
        """
    ).fetchall()

    print(f"\n[Top 10 Ranked Valid Programs]")
    print(f"{'Rank':<5} {'Program ID':<26} {'Ratio R':<12} {'Beats Bohman':<14} {'Island':<8} {'Fitness':<10}")
    print("-" * 75)
    for idx, p in enumerate(top_progs, 1):
        beats = "YES (*)" if p['beats_bohman'] else "No"
        print(f"{idx:<5} {p['id']:<26} {p['best_ratio']:<12.6f} {beats:<14} {p['island_id']:<8} {p['fitness']:<10.1f}")

    # 4. Discoveries
    discoveries = conn.execute("SELECT * FROM discoveries ORDER BY timestamp DESC LIMIT 5").fetchall()
    if discoveries:
        print(f"\n[Key Discoveries & Milestones]")
        for d in discoveries:
            beats = "YES (< 0.22002)!" if d['beats_bohman'] else "No"
            print(f" - [{d['timestamp']}] Program: {d['program_id']} | Ratio: {d['best_ratio']:.6f} | Beats Bohman: {beats}")
            if d['notes']:
                print(f"   Notes: {d['notes']}")

    print("\n" + "=" * 70)
    conn.close()

if __name__ == "__main__":
    generate_report()
