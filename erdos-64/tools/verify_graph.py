"""Verify a graph JSON with the compiled Rust verifier and print a one-line summary.

Accepts either a plain graph ({"n":.., "adj":[..]}) or a swarm output file (which
carries extra fields such as best_energy). Use this instead of trusting the GPU's
own energy: the kernel caps its counts and has no C64 tier, the verifier does not.

    python tools/verify_graph.py cuda/best_swarm_n32.json [--cap 100000]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_verifier() -> Path:
    exe = ".exe" if sys.platform == "win32" else ""
    for p in [
        ROOT / "target" / "release" / f"verifier_64{exe}",
        ROOT / "verifier" / "target" / "release" / f"verifier_64{exe}",
    ]:
        if p.is_file():
            return p
    raise FileNotFoundError("verifier_64 not built; run `make build-verifier`")


def verify(graph: dict, cap: int) -> dict:
    payload = json.dumps({"n": graph["n"], "adj": graph["adj"]})
    args = [str(find_verifier())]
    if cap > 1:
        args += ["--full", "--cap", str(cap)]
    proc = subprocess.run(args, input=payload, capture_output=True, text=True, timeout=3600)
    if not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "verifier produced no output")
    return json.loads(proc.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--cap", type=int, default=100000)
    ap.add_argument("--json", action="store_true", help="print the full verifier JSON")
    args = ap.parse_args()

    graph = json.loads(Path(args.path).read_text(encoding="utf-8"))
    res = verify(graph, args.cap)

    if args.json:
        print(json.dumps(res, indent=2))
        return 0 if res["counterexample"] else 1

    counts = ", ".join(
        f"C{c['length']}={c['count']}{'+' if c['capped'] else ''}" for c in res["counts"]
    )
    print(
        f"n={res['n']} edges={res['edges']} cubic={res['is_cubic']} "
        f"connected={res['connected']} girth={res['girth']} | {counts} | "
        f"COUNTEREXAMPLE={res['counterexample']}"
    )
    return 0 if res["counterexample"] else 1


if __name__ == "__main__":
    sys.exit(main())
