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

Each order keeps a small POPULATION of candidates (`cuda/f4_pool_n{n}_{i}.json`,
ranked by the verified (C4, C8, C16) tuple) instead of a single best graph. Every
attempt seeds from one pool member and passes a fresh `--rng-seed`, derived from
(order, attempt index, --base-seed). Seeding from one graph with one fixed RNG seed
was the old trap: the kernel is deterministic, so a second round re-ran the first one
move for move and could not improve. The whole sweep is still reproducible, because
the seeds are a pure function of the arguments.

Every number reported here comes from verifier_64. The kernel's own cycle counts are
capped and only used to drive the search, so they are never printed as results.

    python tools/f4_sweep.py --orders 54,56,58,60,62,64 --iters 8000 --attempts 4
"""

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POW2 = (4, 8, 16, 32, 64)
TARGET_LENGTHS = (4, 8, 16)

# Published bounds, for reporting context.
F4_LOWER, F4_UPPER = 54, 78

OBJECTIVE_NOTE = ("f(4): no C4, C8 or C16. 32-cycles are allowed and are NOT "
                  "a failure for this target.")

# Derived RNG seeds are spaced in blocks of 2^20. The kernel gives thread t the seed
# rng_seed + t, so blocks this wide keep the per-thread streams of two attempts from
# ever overlapping for any plausible thread count.
SEED_BLOCK_BITS = 20


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


def derive_seed(base_seed: int, n: int, index: int) -> int:
    """Deterministic per-attempt RNG seed for `--rng-seed`.

    A pure function of (base_seed, order, attempt index), so re-running the sweep with
    the same arguments replays the same seeds, while every attempt inside a sweep gets
    an independent restart.
    """
    digest = hashlib.blake2b(f"{base_seed}:{n}:{index}".encode("utf-8"),
                             digest_size=8).digest()
    block = int.from_bytes(digest, "big") % (1 << (63 - SEED_BLOCK_BITS))
    return block << SEED_BLOCK_BITS


def run_swarm(n: int, iters: int, threads: int, count_cap: int,
              seed_file: Path | None, rng_seed: int) -> dict:
    exe = ROOT / "cuda" / "swarm_64.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"{exe} not built (run cuda/build.bat)")
    cmd = [str(exe), str(n), str(iters),
           "--threads", str(threads),
           "--count-cap", str(count_cap),
           "--max-length", "16",
           "--rng-seed", str(rng_seed),
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


def canonical(adj: list) -> tuple:
    """Dedup key for a pool: the adjacency lists, order-insensitive per row."""
    return tuple(tuple(sorted(row)) for row in adj)


def build_record(res: dict, report: dict, counts: dict[int, int]) -> dict:
    """The `cuda/f4_best_n{n}.json` format. Kept as-is: the README and other tooling
    read these files. Every count comes from verifier_64, never from the kernel."""
    return {
        "n": res["n"],
        "adj": res["adj"],
        "objective": OBJECTIVE_NOTE,
        "target_counts": {f"C{L}": counts.get(L, 0) for L in TARGET_LENGTHS},
        "full_counts": {f"C{L}": counts[L] for L in sorted(counts)},
        "capped": {f"C{L}": c["capped"] for c in report["counts"]
                   for L in [c["length"]]},
        "is_cubic": report["is_cubic"],
        "connected": report["connected"],
        "girth": report["girth"],
        "is_erdos_gyarfas_counterexample": report["counterexample"],
        "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def pool_path(outdir: Path, n: int, i: int) -> Path:
    return outdir / f"f4_pool_n{n}_{i}.json"


def score_of(record: dict) -> tuple:
    """Verified target tuple recorded in a candidate file."""
    return tuple(int(record["target_counts"][f"C{L}"]) for L in TARGET_LENGTHS)


def load_pool(outdir: Path, n: int, size: int) -> list[dict]:
    """Read the existing population for this order, best first.

    Falls back to `f4_best_n{n}.json` so a first run with pools still starts from the
    candidates recorded by earlier sweeps.
    """
    def read(path: Path, records: list) -> None:
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
            score_of(rec)          # a candidate without verified counts is unusable
            canonical(rec["adj"])
        except Exception as e:
            print(f"[n={n}] ignoring unusable candidate file {path.name}: {e}")
            return
        records.append(rec)

    records: list[dict] = []
    for path in sorted(outdir.glob(f"f4_pool_n{n}_*.json")):
        read(path, records)
    if not records:
        best = outdir / f"f4_best_n{n}.json"
        if best.is_file():
            read(best, records)

    pool: list[dict] = []
    seen = set()
    for rec in sorted(records, key=score_of):
        key = canonical(rec["adj"])
        if key in seen:
            continue
        seen.add(key)
        pool.append(rec)
        if len(pool) == size:
            break
    return pool


def save_pool(outdir: Path, n: int, pool: list[dict]) -> None:
    for i, rec in enumerate(pool):
        pool_path(outdir, n, i).write_text(json.dumps(rec, indent=2), encoding="utf-8")
    # Drop files left over from a larger pool or a smaller --pool-size.
    for path in outdir.glob(f"f4_pool_n{n}_*.json"):
        try:
            idx = int(path.stem.rsplit("_", 1)[1])
        except ValueError:
            continue
        if idx >= len(pool):
            path.unlink()


def insert_into_pool(pool: list[dict], rec: dict, size: int) -> bool:
    """Add `rec` if the pool has room or it beats the worst member. Duplicates of a
    graph already in the pool are dropped."""
    key = canonical(rec["adj"])
    if any(canonical(m["adj"]) == key for m in pool):
        return False
    score = score_of(rec)
    if len(pool) < size:
        pool.append(rec)
    elif score < score_of(pool[-1]):
        pool[-1] = rec
    else:
        return False
    pool.sort(key=score_of)
    return True


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
    ap.add_argument("--attempts", type=int, default=4,
                    help="swarm launches per order per round; each one seeds from a "
                         "different pool member and uses a fresh --rng-seed")
    ap.add_argument("--pool-size", type=int, default=4,
                    help="candidates kept per order in cuda/f4_pool_n{n}_{i}.json")
    ap.add_argument("--base-seed", type=int, default=0,
                    help="base for the derived per-attempt RNG seeds; change it to get "
                         "a different but equally reproducible sweep")
    args = ap.parse_args()

    if args.attempts < 1 or args.pool_size < 1 or args.rounds < 1:
        print("--attempts, --pool-size and --rounds must be >= 1")
        return 2
    if args.base_seed < 0:
        print("--base-seed must be non-negative")
        return 2

    orders = [int(x) for x in args.orders.split(",") if x.strip()]
    outdir = ROOT / "cuda"
    results = []

    print(f"f(4) sweep: target {{C4, C8, C16}}-free cubic graphs")
    print(f"Published: {F4_LOWER} <= f(4) <= {F4_UPPER}. Anything found on "
          f"{F4_LOWER}..{F4_UPPER - 1} vertices improves the upper bound.")
    print(f"Reachable here: n <= 64 (verifier is a 64-vertex engine).")
    print(f"Population: {args.pool_size} per order, {args.attempts} attempts per order "
          f"per round, {args.rounds} round(s), base seed {args.base_seed}.")
    print("All reported counts come from verifier_64.\n")

    for rnd in range(1, args.rounds + 1):
        for n in orders:
            if n < F4_LOWER:
                print(f"[n={n}] skipped: f(4) >= {F4_LOWER} makes this order provably empty.")
                continue
            if n > 64:
                print(f"[n={n}] skipped: beyond the 64-vertex verifier.")
                continue

            pool = load_pool(outdir, n, args.pool_size)
            save_pool(outdir, n, pool)
            cand = outdir / f"f4_best_n{n}.json"
            best_score = None
            if cand.is_file():
                try:
                    best_score = score_of(json.loads(cand.read_text(encoding="utf-8")))
                except Exception:
                    best_score = None
            print(f"[n={n}] round {rnd}: pool loaded with {len(pool)} member(s)"
                  + (f", best so far C4={best_score[0]} C8={best_score[1]} "
                     f"C16={best_score[2]}" if best_score else ", nothing recorded yet"))

            for attempt in range(args.attempts):
                index = (rnd - 1) * args.attempts + attempt
                rng_seed = derive_seed(args.base_seed, n, index)

                seed_file = None
                seed_from = "stochastic"
                if pool:
                    rank = index % len(pool)
                    seed_file = pool_path(outdir, n, rank)
                    seed_from = f"pool[{rank}]"

                t0 = datetime.datetime.now()
                try:
                    res = run_swarm(n, args.iters, args.threads, args.count_cap,
                                    seed_file, rng_seed)
                except Exception as e:
                    print(f"[n={n}] r{rnd} a{attempt + 1} rng-seed={rng_seed} "
                          f"swarm failed: {e}", flush=True)
                    continue
                secs = (datetime.datetime.now() - t0).total_seconds()

                # Nothing below trusts the kernel's own counts: the graph is re-counted
                # by verifier_64 and only those numbers are scored, stored or printed.
                report = verify({"n": res["n"], "adj": res["adj"]}, args.verify_cap)
                counts = profile(report)
                score = target_score(counts)
                hit = all(v == 0 for v in score)

                rec = build_record(res, report, counts)
                # Pool members also carry the seed that produced them, so any member can
                # be regenerated from its own file. f4_best keeps the older format.
                rec["rng_seed"] = rng_seed
                improved = report["is_cubic"] and insert_into_pool(pool, rec,
                                                                   args.pool_size)
                if improved:
                    save_pool(outdir, n, pool)
                    if best_score is None or score_of(pool[0]) < best_score:
                        best_rec = {k: v for k, v in pool[0].items() if k != "rng_seed"}
                        cand.write_text(json.dumps(best_rec, indent=2), encoding="utf-8")
                        best_score = score_of(pool[0])

                marker = "  <-- {4,8,16}-FREE" if hit else ""
                print(f"[n={n}] r{rnd} a{attempt + 1} seed={rng_seed} from {seed_from}: "
                      f"C4={score[0]} C8={score[1]} C16={score[2]} "
                      f"(C32={counts.get(32, 0)}) cubic={report['is_cubic']} "
                      f"conn={report['connected']} {secs:.0f}s "
                      f"{'pool improved' if improved else 'pool unchanged'}"
                      f"{marker}", flush=True)
                results.append({"n": n, "round": rnd, "attempt": attempt + 1,
                                "rng_seed": rng_seed, "target": score,
                                "c32": counts.get(32, 0), "seconds": secs,
                                "hit": hit, "improved": improved})

            if pool:
                print(f"[n={n}] pool now: "
                      + ", ".join(f"#{i} {score_of(m)}" for i, m in enumerate(pool)))

    print("\nSummary (best target profile per order, verified):")
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
