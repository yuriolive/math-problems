"""
Baseline Seed Generators for Erdős Problem #1 (Distinct Subset Sums).
Implements:
1. Conway-Guy sequence (OEIS A005318)
2. Bohman's randomized construction
"""

import math
import random

def conway_guy_sequence(n: int) -> list[int]:
    """
    Generates an n-element set with distinct subset sums using the Conway-Guy recurrence.
    u_0 = 0, u_1 = 1
    u_{k+1} = 2*u_k - u_{k-r}, where r = floor(sqrt(2*k) + 0.5)
    The set is {u_n - u_{n-1}, u_n - u_{n-2}, ..., u_n - u_0}.
    """
    if n <= 0:
        return []
    if n == 1:
        return [1]
    if n == 2:
        return [1, 2]

    u = [0, 1]
    for k in range(1, n):
        r = int(math.floor(math.sqrt(2 * k) + 0.5))
        idx = max(0, k - r)
        u_next = 2 * u[k] - u[idx]
        u.append(u_next)

    un = u[n]
    s = [un - u[i] for i in range(n - 1, -1, -1)]
    return sorted(s)

def bohman_randomized(n: int, seed: int | None = None) -> list[int]:
    """
    Bohman's randomized heuristic construction:
    Extends the Conway-Guy recurrence by perturbing step indices r_k and offsets,
    exploring the local neighborhood around Bohman's asymptotic construction.
    """
    if n <= 0:
        return []
    if n == 1:
        return [1]
    if n == 2:
        return [1, 2]

    rng = random.Random(seed)
    u = [0, 1]
    for k in range(1, n):
        base_r = int(math.floor(math.sqrt(2 * k) + 0.5))
        # Small stochastic adjustment for exploration
        jitter = rng.choice([-1, 0, 0, 1]) if k > 5 else 0
        r = max(1, min(k, base_r + jitter))
        idx = max(0, k - r)
        u_next = 2 * u[k] - u[idx]
        u.append(u_next)

    un = u[n]
    s = [un - u[i] for i in range(n - 1, -1, -1)]
    return sorted(s)

# Exact executable code templates for the evolutionary engine
CONWAY_GUY_CODE = '''import math

def generate_set(n: int) -> list[int]:
    if n <= 0:
        return []
    if n == 1:
        return [1]
    u = [0, 1]
    for k in range(1, n):
        r = int(math.floor(math.sqrt(2 * k) + 0.5))
        idx = max(0, k - r)
        u_next = 2 * u[k] - u[idx]
        u.append(u_next)
    un = u[n]
    return sorted([un - u[i] for i in range(n - 1, -1, -1)])
'''

BOHMAN_RANDOMIZED_CODE = '''import math

def generate_set(n: int) -> list[int]:
    if n <= 0:
        return []
    if n == 1:
        return [1]
    u = [0, 1]
    for k in range(1, n):
        r = int(math.floor(math.sqrt(2 * k) + 0.5))
        # Compress terms when k is even
        offset = 1 if (k > 4 and k % 3 == 0) else 0
        idx = max(0, k - (r + offset))
        u_next = 2 * u[k] - u[idx]
        u.append(u_next)
    un = u[n]
    return sorted([un - u[i] for i in range(n - 1, -1, -1)])
'''
