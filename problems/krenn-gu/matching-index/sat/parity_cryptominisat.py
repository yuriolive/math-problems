"""GF(2) parity relaxation of Krenn-Gu at (n,d), decided with CryptoMiniSat's native XOR.

    uv pip install pycryptosat            # not a repository dependency; optional
    .venv/bin/python sat/parity_cryptominisat.py 6 3 [time_budget_s] [outdir]

Why this relaxation matters: for integer weights, amplitude(colouring) mod 2 equals the number
of perfect matchings of the odd-weight support mod 2, so an integer-weight GHZ graph forces a
support in which every constant colouring has an odd matching count and every other colouring
an even one. If no such support exists at n = 6, a GF(2) rank argument for all n becomes a live
route to the integer and {-1,0,1} versions of the conjecture (Formal Conjectures entries
eqSystem_no_solution_ge6_ge3_int and _trinary_int). If one exists, parity alone cannot prove
them. A satisfying support is written as a checker instance; verify its matching-count parities
with ghzcheck --dump-colourings before believing it (rule 1).

Symmetry breaking: the all-0 colouring needs an odd (hence >= 1) number of monochromatic
matchings, and S_n acts transitively on perfect matchings of K_n, so WLOG the colour-0 slots
of the matching {01,23,45,...} are present.
"""
import itertools, json, sys, time
from pycryptosat import Solver

n, d = int(sys.argv[1]), int(sys.argv[2])
budget = float(sys.argv[3]) if len(sys.argv) > 3 else 1800.0
verts = list(range(n))

def matchings(vs):
    if not vs: yield []; return
    u, rest = vs[0], vs[1:]
    for i, v in enumerate(rest):
        for m in matchings(rest[:i] + rest[i+1:]):
            yield [(u, v)] + m
PMS = list(matchings(verts))

slot = {}
for u in range(n):
    for v in range(u+1, n):
        for cu in range(d):
            for cv in range(d):
                slot[(u, v, cu, cv)] = len(slot) + 1
def sv(u, v, cu, cv):
    return slot[(u, v, cu, cv)] if u < v else slot[(v, u, cv, cu)]
nv = len(slot)
s = Solver(threads=2)
for col in itertools.product(range(d), repeat=n):
    mvars = []
    for pm in PMS:
        nv += 1; m = nv
        lits = [sv(u, v, col[u], col[v]) for (u, v) in pm]
        s.add_clause([m] + [-l for l in lits])
        for l in lits: s.add_clause([-m, l])
        mvars.append(m)
    s.add_xor_clause(mvars, len(set(col)) == 1)
# symmetry breaking
for i in range(0, n, 2):
    s.add_clause([sv(i, i+1, 0, 0)])
t0 = time.time()
sat, model = s.solve()
out = {"n": n, "d": d, "slots": len(slot), "vars": nv, "sat": sat, "seconds": round(time.time()-t0, 1)}
print(json.dumps(out), flush=True)
if sat:
    on = [k for k, v in slot.items() if model[v]]
    inst = {"name": f"parity-support-n{n}-d{d}", "n": n, "colours": d, "root_of_unity": 1,
            "edges": [{"u": u, "v": v, "cu": cu, "cv": cv} for (u, v, cu, cv) in on]}
    path = f"{sys.argv[4] if len(sys.argv) > 4 else '.'}/support-n{n}-d{d}.json"
    json.dump(inst, open(path, "w"), indent=1)
    print("support written:", path, "slots on:", len(on), flush=True)
