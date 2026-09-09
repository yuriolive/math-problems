"""Record an f(4) search result and regenerate the f(4) table in README.md.

Usage:
    python tools/f4_report.py --record <swarm-output.json>   # save if better
    python tools/f4_report.py                                # just refresh the table

Every count printed comes from verifier_64, never from the search kernel.
"""

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_LENGTHS = (4, 8, 16)
OBJECTIVE_NOTE = ("f(4): no C4, C8 or C16. 32-cycles are allowed and are NOT "
                  "a failure for this target.")


def verifier() -> Path:
    exe = ".exe" if sys.platform == "win32" else ""
    for p in [ROOT / "target" / "release" / f"verifier_64{exe}",
              ROOT / "verifier" / "target" / "release" / f"verifier_64{exe}"]:
        if p.is_file():
            return p
    raise FileNotFoundError("verifier_64 not built; run `make build-verifier`")


def verify(graph: dict, cap: int = 100000) -> dict:
    payload = json.dumps({"n": graph["n"], "adj": graph["adj"]})
    proc = subprocess.run([str(verifier()), "--full", "--cap", str(cap)],
                          input=payload, capture_output=True, text=True, timeout=3600)
    if not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "verifier produced no output")
    return json.loads(proc.stdout)


def target_of(counts: dict[int, int]) -> tuple:
    return tuple(counts.get(L, 0) for L in TARGET_LENGTHS)


def record(path: Path) -> None:
    src = json.loads(path.read_text(encoding="utf-8"))
    report = verify(src)
    counts = {c["length"]: c["count"] for c in report["counts"]}
    score = target_of(counts)
    dest = ROOT / "cuda" / f"f4_best_n{src['n']}.json"

    if dest.is_file():
        old = json.loads(dest.read_text(encoding="utf-8"))
        old_score = tuple(int(old["target_counts"][f"C{L}"]) for L in TARGET_LENGTHS)
        if score >= old_score:
            print(f"n={src['n']}: keeping existing {old_score}, new {score} is not better")
            return
        print(f"n={src['n']}: improving {old_score} -> {score}")
    else:
        print(f"n={src['n']}: recording {score}")

    dest.write_text(json.dumps({
        "n": src["n"],
        "adj": src["adj"],
        "objective": OBJECTIVE_NOTE,
        "target_counts": {f"C{L}": counts.get(L, 0) for L in TARGET_LENGTHS},
        "full_counts": {f"C{L}": counts[L] for L in sorted(counts)},
        "capped": {f"C{c['length']}": c["capped"] for c in report["counts"]},
        "is_cubic": report["is_cubic"],
        "connected": report["connected"],
        "girth": report["girth"],
        "is_erdos_gyarfas_counterexample": report["counterexample"],
        "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }, indent=2), encoding="utf-8")


def table_rows() -> list[str]:
    rows = []
    for path in sorted((ROOT / "cuda").glob("f4_best_n*.json"),
                       key=lambda p: int("".join(c for c in p.stem if c.isdigit()))):
        rec = json.loads(path.read_text(encoding="utf-8"))
        t = rec["target_counts"]
        c32 = rec.get("full_counts", {}).get("C32", "?")
        capped32 = rec.get("capped", {}).get("C32", False)
        rows.append("| {n} | {c4} | {c8} | **{c16}** | {c32}{plus} |".format(
            n=rec["n"], c4=t["C4"], c8=t["C8"], c16=t["C16"],
            c32=c32, plus="+" if capped32 else ""))
    return rows


def refresh_readme() -> None:
    readme = ROOT / "README.md"
    lines = readme.read_text(encoding="utf-8").splitlines(keepends=True)
    header = "| Order $n$ | $C_4$ | $C_8$ | $C_{16}$ | $C_{32}$ (allowed) |\n"
    sep = "| :---: | :---: | :---: | :---: | :---: |\n"

    start = next((i for i, l in enumerate(lines) if l.startswith("| Order $n$ | $C_4$")), None)
    if start is None:
        print("f(4) table not found in README.md; not refreshed")
        return
    end = start
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1
    lines[start:end] = [header, sep] + [r + "\n" for r in table_rows()]
    readme.write_text("".join(lines), encoding="utf-8")
    print(f"README f(4) table refreshed ({len(table_rows())} rows)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", type=str, default=None,
                    help="swarm output JSON to record if it beats the stored candidate")
    args = ap.parse_args()
    if args.record:
        record(Path(args.record))
    refresh_readme()
    return 0


if __name__ == "__main__":
    sys.exit(main())
