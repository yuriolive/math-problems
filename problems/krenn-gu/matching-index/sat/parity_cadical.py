"""Parity (GF(2)) relaxation of the Krenn-Gu system, decided by SAT (CaDiCaL via python-sat).

    uv run python sat/parity_cadical.py 4 3 [outdir]

Plain CDCL with Tseitin XOR chains. Decides n = 4 instantly; at n = 6 it ran for 16 minutes
without an answer on 10 September 2026 and was stopped in favour of the XOR-native encoder in
parity_cryptominisat.py, which is the one to use.

For integer weights, amplitude(colouring) = #{perfect matchings using only odd-weight
slots} mod 2. So an integer-weight GHZ graph forces a *support* S in which every
monochromatic colouring has an odd number of matchings and every other colouring an even
number. This script asks whether such a support exists at all, for K_n with d colours.
"""
import itertools, json, sys, time
from pysat.solvers import Cadical153

n, d = int(sys.argv[1]), int(sys.argv[2])
verts = list(range(n))

def matchings(vs):
    if not vs: yield []; return
    u, rest = vs[0], vs[1:]
    for i, v in enumerate(rest):
        for m in matchings(rest[:i] + rest[i+1:]):
            yield [(u, v)] + m
PMS = list(matchings(verts))

slot = {}
def slot_var(u, v, cu, cv):
    key = (u, v, cu, cv) if u < v else (v, u, cv, cu)
    if key not in slot: slot[key] = len(slot) + 1
    return slot[key]
for u in range(n):
    for v in range(u+1, n):
        for cu in range(d):
            for cv in range(d):
                slot_var(u, v, cu, cv)
nv = len(slot)
clauses = []
def new():
    global nv; nv += 1; return nv
def xor_chain(lits, target):
    # returns clauses forcing XOR(lits) == target via a Tseitin chain
    acc = lits[0]
    for l in lits[1:]:
        z = new()  # z <-> acc xor l
        clauses.extend([[-z, acc, l], [-z, -acc, -l], [z, -acc, l], [z, acc, -l]])
        acc = z
    clauses.append([acc] if target else [-acc])

for col in itertools.product(range(d), repeat=n):
    mono_vars = []
    for pm in PMS:
        m = new()
        lits = [slot_var(u, v, col[u], col[v]) for (u, v) in pm]
        # m <-> AND(lits)
        clauses.append([m] + [-l for l in lits])
        for l in lits: clauses.append([-m, l])
        mono_vars.append(m)
    xor_chain(mono_vars, target=len(set(col)) == 1)

t0 = time.time()
with Cadical153(bootstrap_with=clauses) as s:
    sat = s.solve()
    model = s.get_model() if sat else None
print(json.dumps({"n": n, "d": d, "slots": len(slot), "vars": nv, "clauses": len(clauses),
                  "sat": sat, "seconds": round(time.time()-t0, 2)}))
if sat:
    on = [k for k, v in slot.items() if model[v-1] > 0]
    inst = {"name": f"parity-support-n{n}-d{d}", "n": n, "colours": d, "root_of_unity": 1,
            "edges": [{"u": u, "v": v, "cu": cu, "cv": cv} for (u, v, cu, cv) in on]}
    path = f"{sys.argv[3] if len(sys.argv) > 3 else '.'}/support-n{n}-d{d}.json"
    json.dump(inst, open(path, "w"), indent=1)
    print("support written:", path, "slots on:", len(on))
