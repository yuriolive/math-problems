"""
Baseline Graph Generators and Templates for Erdős Problem #64.
"""

# Template 1: Generalized Petersen Graph generator GP(m, k) where n = 2*m
GENERALIZED_PETERSEN_CODE = '''def generate_graph(n: int) -> dict:
    """
    Generates a Generalized Petersen Graph GP(m, k) on n = 2*m vertices.
    Always 3-regular.
    """
    m = n // 2
    k = 2 if m >= 5 else 1
    adj = [[] for _ in range(n)]

    # Outer cycle (0..m-1)
    for i in range(m):
        adj[i].append((i + 1) % m)
        adj[i].append((i - 1 + m) % m)
        # Spoke to inner star
        adj[i].append(m + i)
        adj[m + i].append(i)

    # Inner star (m..2m-1)
    for i in range(m):
        u = m + i
        v1 = m + (i + k) % m
        v2 = m + (i - k + m) % m
        adj[u].append(v1)
        adj[u].append(v2)

    return {"n": n, "adj": adj}
'''

# Template 2: Ring with optimized chord matching avoiding small cycles
RING_CHORD_CODE = '''import random

def generate_graph(n: int) -> dict:
    """
    Generates a 3-regular graph on n vertices by constructing a Hamiltonian ring
    and computing an alternating chord matching designed to avoid short cycles.
    """
    adj = [[] for _ in range(n)]
    for i in range(n):
        adj[i].append((i + 1) % n)
        adj[i].append((i - 1 + n) % n)

    # Chords connecting i with (i + step) where step is odd and >= 5
    step = 5 if n >= 12 else 3
    used = [False] * n
    for i in range(n):
        if not used[i]:
            target = (i + step) % n
            # Search for available partner
            offset = 0
            while used[target] or target == (i + 1) % n or target == (i - 1 + n) % n or target == i:
                offset += 2
                target = (i + step + offset) % n
                if offset > n:
                    break
            if not used[target] and target != i:
                adj[i].append(target)
                adj[target].append(i)
                used[i] = True
                used[target] = True

    # Fallback to ensure degree 3
    for i in range(n):
        while len(adj[i]) < 3:
            for j in range(i + 1, n):
                if len(adj[j]) < 3 and j not in adj[i]:
                    adj[i].append(j)
                    adj[j].append(i)
                    break
            else:
                break

    return {"n": n, "adj": adj}
'''
