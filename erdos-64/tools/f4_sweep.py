"""Search for {C4, C8, C16}-free cubic graphs, i.e. the f(4) target.

f(k) is the order of the smallest cubic graph with no cycle of length 2^m for any
m <= k. f(2) = 10 (Petersen) and f(3) = 24 (Markstroem) are exact; f(4) is only known
to satisfy 54 <= f(4) <= 78, the lower bound an unpublished Markstroem computation and
the upper bound Exoo's 78-vertex graph. Any cubic graph on 54..77 vertices with no C4,
C8 or C16 improves that upper bound.

Note this target ALLOWS 32-cycles, so a hit here is NOT a counterexample to the
Erdos-Gyarfas conjecture. The verifier is still run on every result so the full cycle
profile is recorded either way.

The reachable window here is 54..64: verifier_64 is a 64-vertex bitmask engine.

    python tools/f4_sweep.py --orders 54,56,58,60,62,64 --iters 8000
"""

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POW2 = (4, 8, 16, 32, 64)
TARGET_LENGTHS = (4, 8, 16)

# Published bounds, for reporting context.
F4_LOWER, F4_UPPER = 54, 78


def verifier() -> Path:
    exe = ".exe" if sys.platform == "win32" else ""
    for p in [ROOT / "target" / "release" / f"verifier_64{exe}",
              ROOT / "verifier" / "target" / "release" / f"verifier_64{exe}"]:
        if p.is_file():
            return p
    raise FileNotFoundError("verifier_64 not built; run `make build-verifier`")


def verify(graph: dict, cap: int) -> dict:
    payload = json.dumps({"n": graph["n"], "adj": graph["adj"]})
    proc = subprocess.run([str(verifier()), "--full", "--cap", str(cap)],
                          input=payload, capture_output=True, text=True, timeout=3600)
    if not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "verifier produced no output")
    return json.loads(proc.stdout)


def profile(report: dict) -> dict[int, int]:
    return {c["length"]: c["count"] for c in report["counts"]}


def target_score(counts: dict[int, int]) -> tuple:
    """Lexicographic key over the f(4) target lengths only. Lower is better."""
    return tuple(counts.get(L, 0) for L in TARGET_LENGTHS)


def run_swarm(n: int, iters: int, threads: int, count_cap: int,
              seed_file: Path | None) -> dict:
    exe = ROOT / "cuda" / "swarm_64.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"{exe} not built (run cuda/build.bat)")
    cmd = [str(exe), str(n), str(iters),
           "--threads", str(threads),
           "--count-cap", str(count_cap),
           "--max-length", "16",
           "--json-only"]
    if seed_file and seed_file.is_file():
        cmd += ["--seed-file", str(seed_file)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"swarm exit {proc.returncode}: {proc.stderr.strip()[:300]}")
    out = proc.stdout.strip()
    start, end = out.find("{"), out.rfind("}") + 1
    if start == -1 or end <= start:
        raise RuntimeError(f"no JSON from swarm. stderr: {proc.stderr.strip()[:300]}")
    return json.loads(out[start:end])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", default="54,56,58,60,62,64")
    ap.add_argument("--iters", type=int, default=8000)
    ap.add_argument("--threads", type=int, default=10240)
    ap.add_argument("--count-cap", type=int, default=500,
                    help="cycle-count cap used by the kernel; keeps the early phase cheap "
                         "while preserving gradient in the range that matters")
    ap.add_argument("--verify-cap", type=int, default=100000)
    ap.add_argument("--rounds", type=int, default=1)
    args = ap.parse_args()

    orders = [int(x) for x in args.orders.split(",") if x.strip()]
    outdir = ROOT / "cuda"
    results = []

    print(f"f(4) sweep: target {{C4, C8, C16}}-free cubic graphs")
    print(f"Published: {F4_LOWER} <= f(4) <= {F4_UPPER}. Anything found on "
          f"{F4_LOWER}..{F4_UPPER - 1} vertices improves the upper bound.")
    print(f"Reachable here: n <= 64 (verifier is a 64-vertex engine).\n")

    for rnd in range(1, args.rounds + 1):
        for n in orders:
            if n < F4_LOWER:
                print(f"[n={n}] skipped: f(4) >= {F4_LOWER} makes this order provably empty.")
                continue
            if n > 64:
                print(f"[n={n}] skipped: beyond the 64-vertex verifier.")
                continue

            cand = outdir / f"f4_best_n{n}.json"
            seed = cand if cand.is_file() else None
            t0 = datetime.datetime.now()
            try:
                res = run_swarm(n, args.iters, args.threads, args.count_cap, seed)
            except Exception as e:
                print(f"[n={n}] swarm failed: {e}")
                continue
            secs = (datetime.datetime.now() - t0).total_seconds()

            report = verify({"n": res["n"], "adj": res["adj"]}, args.verify_cap)
            counts = profile(report)
            score = target_score(counts)
            hit = all(v == 0 for v in score)

            prev = None
            if cand.is_file():
                try:
                    prev = tuple(json.loads(cand.read_text(encoding="utf-8"))
                                 ["target_counts"][f"C{L}"] for L in TARGET_LENGTHS)
                except Exception:
                    prev = None

            improved = prev is None or score < prev
            if improved and report["is_cubic"]:
                cand.write_text(json.dumps({
                    "n": res["n"],
                    "adj": res["adj"],
                    "objective": "f(4): no C4, C8 or C16. 32-cycles are allowed and are NOT "
                                 "a failure for this target.",
                    "target_counts": {f"C{L}": counts.get(L, 0) for L in TARGET_LENGTHS},
                    "full_counts": {f"C{L}": counts[L] for L in sorted(counts)},
                    "capped": {f"C{L}": c["capped"] for c in report["counts"]
                               for L in [c["length"]]},
                    "is_cubic": report["is_cubic"],
                    "connected": report["connected"],
                    "girth": report["girth"],
                    "is_erdos_gyarfas_counterexample": report["counterexample"],
                    "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }, indent=2), encoding="utf-8")

            marker = "  <-- {4,8,16}-FREE" if hit else ""
            print(f"[n={n}] round {rnd}: C4={score[0]} C8={score[1]} C16={score[2]} "
                  f"(C32={counts.get(32, 0)}) cubic={report['is_cubic']} "
                  f"conn={report['connected']} {secs:.0f}s"
                  f"{' improved' if improved else ' no gain'}{marker}", flush=True)
            results.append({"n": n, "round": rnd, "target": score,
                            "c32": counts.get(32, 0), "seconds": secs, "hit": hit})

    print("\nSummary (best target profile per order):")
    best: dict[int, tuple] = {}
    for r in results:
        if r["n"] not in best or r["target"] < best[r["n"]]:
            best[r["n"]] = r["target"]
    for n in sorted(best):
        c4, c8, c16 = best[n]
        print(f"  n={n:>3}  C4={c4}  C8={c8}  C16={c16}")

    if any(r["hit"] for r in results):
        print("\nA {4,8,16}-free cubic graph was found. This improves the f(4) upper bound if")
        print("its order is below 78. It is NOT a counterexample to Erdos-Gyarfas: verify the")
        print("C32 count above, and re-verify the graph with an independent tool.")
    else:
        print("\nNo {4,8,16}-free graph found in this sweep. Nothing is concluded from that:")
        print("this is a heuristic search, so it is not evidence of non-existence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
