"""Emit the fully loaded instance: K_n carrying every colour slot, all weights 1.

    uv run python tools/full_support.py 6 3 > /tmp/k6-d3-full.json

This is the largest instance the enumeration ever has to handle for a given (n, d), so
running the checker on it measures the reach of the instrument rather than guessing it.
Its report is *not* a statement about the conjecture: all-ones weights are one point of a
135-dimensional weight space at (n, d) = (6, 3).
"""

import json
import sys


def full(n: int, d: int) -> dict:
    edges = [
        {"u": u, "v": v, "cu": cu, "cv": cv}
        for u in range(n)
        for v in range(u + 1, n)
        for cu in range(d)
        for cv in range(d)
    ]
    return {
        "name": f"k{n}-d{d}-full-support",
        "comment": "every colour slot present, all weights 1",
        "n": n,
        "colours": d,
        "root_of_unity": 1,
        "edges": edges,
    }


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    json.dump(full(n, d), sys.stdout, indent=1)
    print()
