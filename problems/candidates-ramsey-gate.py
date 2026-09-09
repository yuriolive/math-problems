"""Check the published Ramsey multiplicity records are consistent with an n^t denominator.

Part of the go/no-go gate. Before writing any checker, confirm that the two records really
are rationals of the shape (integer) / n^t for the stated graph orders. If they are not,
Lemma 3.2 has been misread and no amount of correct code will reproduce them.

    c_4 <= 4551721 * 2^-24 * 3^-2   from a Cayley graph of order 768 in Z_3 x Z_2^8
    c_5 <= 2320651 * 2^-24 * 3^-4   from a Cayley graph of order 192 in Z_3 x Z_2^6
"""

from fractions import Fraction

CASES = [
    # (t, n, record numerator, record denominator, published decimal bound)
    (4, 768, 4551721, 2**24 * 3**2, "0.030145"),
    (5, 192, 2320651, 2**24 * 3**4, "0.001708"),
]

print(f"{'t':>2} {'n':>5} {'n^t factorisation':>22} {'record':>14} "
      f"{'numerator over n^t':>22} {'integer?':>9}")
print("-" * 84)

ok = True
for t, n, num, den, bound in CASES:
    rec = Fraction(num, den)

    # n = 2^a * 3^b for both cases, so n^t factors as a power of 2 times a power of 3.
    a = 0
    m = n
    while m % 2 == 0:
        m //= 2
        a += 1
    b = 0
    while m % 3 == 0:
        m //= 3
        b += 1
    assert m == 1, f"n = {n} is not of the form 2^a * 3^b"
    fact = f"2^{a * t} * 3^{b * t}"
    n_t = n**t
    assert n_t == 2**(a * t) * 3**(b * t)

    # If the record is (some integer) / n^t, then record * n^t must be an integer.
    scaled = rec * n_t
    is_int = scaled.denominator == 1
    ok = ok and is_int

    print(f"{t:>2} {n:>5} {fact:>22} {num}/{den} "
          f"{str(scaled):>22} {str(is_int):>9}")

    # And the decimal must match the published bound.
    assert float(rec) < float(bound), f"record not below published bound {bound}"
    print(f"      record = {float(rec):.9f}  < {bound}  (published)")
    print(f"      so the Lemma 3.2 numerator to reproduce is {scaled}")
    print()

print("CONSISTENT with an n^t denominator" if ok else "NOT consistent -- Lemma 3.2 misread")
raise SystemExit(0 if ok else 1)
