//! Exact cycle verifier for Erdős Problem #64 (Erdős–Gyárfás conjecture).
//!
//! The conjecture: every finite graph with minimum degree >= 3 contains a simple cycle
//! whose length is a power of two (4, 8, 16, 32, 64, ...).
//!
//! Design notes (see `docs` in the project README):
//!
//! * Every power-of-two length `<= n` is checked **unconditionally**. An earlier version
//!   short-circuited (only testing C8 when C4 was absent, etc.) and serialized the
//!   untested tiers as `false`, which reads as "absent" but meant "not checked".
//! * `verify()` reports existence (`has_c*`) for every tier plus, on request,
//!   exact counts (`count_c*`) up to a caller-supplied cap.
//! * Connectivity is reported explicitly; `diameter` is only meaningful when connected.

use serde::{Deserialize, Serialize};

/// Powers of two that can occur as a cycle length in a simple graph on `n` vertices.
pub fn pow2_cycle_lengths(n: usize) -> Vec<usize> {
    let mut out = Vec::new();
    let mut len = 4usize;
    while len <= n {
        out.push(len);
        len *= 2;
    }
    out
}

/// Result of counting cycles of one fixed length.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub struct CycleCount {
    /// Cycle length that was searched.
    pub length: usize,
    /// Number of distinct simple cycles found (undirected, each counted once).
    pub count: u64,
    /// True when the search stopped at the cap, so `count` is a lower bound.
    pub capped: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GraphVerificationResult {
    /// True iff min degree >= 3 and **no** power-of-two cycle of any length <= n exists.
    pub counterexample: bool,
    pub n: usize,
    pub edges: usize,
    pub min_degree: usize,
    pub max_degree: usize,
    pub is_cubic: bool,
    pub girth: usize,
    /// Eccentricity-based diameter. Only meaningful when `connected` is true.
    pub diameter: usize,
    pub connected: bool,
    pub components: usize,
    pub bipartite: bool,
    /// Every power-of-two length that was searched (all powers of two <= n).
    pub checked_lengths: Vec<usize>,
    pub has_c4: bool,
    pub has_c8: bool,
    pub has_c16: bool,
    pub has_c32: bool,
    pub has_c64: bool,
    /// Exact counts, present only when counting was requested. Cycle lengths not
    /// listed here were tested for existence but not counted.
    pub counts: Vec<CycleCount>,
    /// Number of distinct power-of-two lengths that occur as a cycle length.
    pub power_of_two_cycle_count: usize,
    pub cycle_witness: Option<Vec<usize>>,
    pub diagnostic_trace: String,
}

#[derive(Debug, Clone)]
pub struct Graph64 {
    pub n: usize,
    pub adj: [u64; 64],
}

/// Bitmask of all vertices strictly greater than `v`, safe for `v == 63`.
#[inline]
fn mask_above(v: usize) -> u64 {
    if v >= 63 {
        0
    } else {
        !0u64 << (v + 1)
    }
}

impl Graph64 {
    pub fn new(n: usize) -> Self {
        assert!(n <= 64, "Graph size must be <= 64 vertices");
        Self { n, adj: [0u64; 64] }
    }

    pub fn from_adjacency_list(n: usize, adj_list: &[&[usize]]) -> Self {
        let mut g = Self::new(n);
        for (u, neighbors) in adj_list.iter().enumerate() {
            for &v in *neighbors {
                g.add_edge(u, v);
            }
        }
        g
    }

    pub fn add_edge(&mut self, u: usize, v: usize) {
        if u < self.n && v < self.n && u != v {
            self.adj[u] |= 1u64 << v;
            self.adj[v] |= 1u64 << u;
        }
    }

    pub fn remove_edge(&mut self, u: usize, v: usize) {
        if u < self.n && v < self.n {
            self.adj[u] &= !(1u64 << v);
            self.adj[v] &= !(1u64 << u);
        }
    }

    pub fn degree(&self, u: usize) -> usize {
        self.adj[u].count_ones() as usize
    }

    pub fn edge_count(&self) -> usize {
        (0..self.n).map(|i| self.degree(i)).sum::<usize>() / 2
    }

    /// Fast O(n^2) bitwise check for 4-cycles, returning a witness if present.
    pub fn find_c4(&self) -> Option<Vec<usize>> {
        for u in 0..self.n {
            for w in (u + 1)..self.n {
                let common = self.adj[u] & self.adj[w];
                if common.count_ones() >= 2 {
                    let v1 = common.trailing_zeros() as usize;
                    let remaining = common & !(1u64 << v1);
                    let v2 = remaining.trailing_zeros() as usize;
                    return Some(vec![u, v1, w, v2]);
                }
            }
        }
        None
    }

    /// BFS distances within the subgraph induced on `allowed`, starting at `src`.
    /// Unreachable vertices get `usize::MAX`.
    fn distances_in(&self, src: usize, allowed: u64) -> [usize; 64] {
        let mut dist = [usize::MAX; 64];
        let mut frontier = 1u64 << src;
        let mut seen = frontier;
        dist[src] = 0;
        let mut d = 0usize;
        while frontier != 0 {
            d += 1;
            let mut next = 0u64;
            let mut f = frontier;
            while f != 0 {
                let u = f.trailing_zeros() as usize;
                f &= f - 1;
                next |= self.adj[u] & allowed & !seen;
            }
            let mut m = next;
            while m != 0 {
                let v = m.trailing_zeros() as usize;
                m &= m - 1;
                dist[v] = d;
            }
            seen |= next;
            frontier = next;
        }
        dist
    }

    /// Counts simple cycles of exactly `target_len` vertices.
    ///
    /// Each undirected cycle is counted once. Counting stops once `cap` cycles are
    /// found; the returned `capped` flag says whether the count is a lower bound.
    /// `cap == 1` therefore answers existence, which is what `verify()` uses.
    ///
    /// Canonical form: the cycle's minimum vertex is the search root, so every cycle is
    /// discovered exactly twice (once per traversal direction).
    pub fn count_cycles_of_length(&self, target_len: usize, cap: u64) -> CycleCount {
        let mut result = CycleCount { length: target_len, count: 0, capped: false };
        if target_len < 3 || target_len > self.n || cap == 0 {
            return result;
        }

        let mut directed_hits: u64 = 0;
        let directed_cap = cap.saturating_mul(2);

        // A cycle of length L whose minimum vertex is `start` needs L-1 further
        // vertices above `start`, so `start` cannot exceed n - L.
        for start in 0..=(self.n - target_len) {
            let allowed = mask_above(start) | (1u64 << start);
            // Lower bound on the number of edges still needed to get back to `start`.
            let dist = self.distances_in(start, allowed);
            let mut stack_v = [0usize; 64];
            let mut stack_cands = [0u64; 64];

            stack_v[0] = start;
            stack_cands[0] = self.adj[start] & mask_above(start);
            let mut visited = 1u64 << start;
            let mut depth = 0usize;

            loop {
                if stack_cands[depth] != 0 {
                    let nxt = stack_cands[depth].trailing_zeros() as usize;
                    stack_cands[depth] &= stack_cands[depth] - 1;

                    if depth + 2 == target_len {
                        // `nxt` would be the last vertex: it must close back to `start`.
                        if (self.adj[nxt] & (1u64 << start)) != 0 {
                            directed_hits += 1;
                            if directed_hits >= directed_cap {
                                result.count = directed_hits / 2;
                                result.capped = true;
                                return result;
                            }
                        }
                        continue;
                    }

                    // Prune: remaining steps must suffice to return to `start`.
                    let remaining = target_len - (depth + 2);
                    let back = dist[nxt];
                    if back == usize::MAX || back > remaining + 1 {
                        continue;
                    }

                    depth += 1;
                    stack_v[depth] = nxt;
                    visited |= 1u64 << nxt;
                    stack_cands[depth] = self.adj[nxt] & mask_above(start) & !visited;
                } else {
                    if depth == 0 {
                        break;
                    }
                    visited &= !(1u64 << stack_v[depth]);
                    depth -= 1;
                }
            }
        }

        result.count = directed_hits / 2;
        result
    }

    /// Returns a witness cycle of exactly `target_len` vertices, if one exists.
    pub fn find_cycle_of_length(&self, target_len: usize) -> Option<Vec<usize>> {
        if target_len < 3 || target_len > self.n {
            return None;
        }
        if target_len == 4 {
            return self.find_c4();
        }

        let mut path = Vec::with_capacity(target_len);
        for start in 0..=(self.n - target_len) {
            let visited = 1u64 << start;
            path.clear();
            path.push(start);
            let mut neighbors = self.adj[start] & mask_above(start);
            while neighbors != 0 {
                let v1 = neighbors.trailing_zeros() as usize;
                neighbors &= neighbors - 1;
                path.push(v1);
                if self.dfs_cycle(start, v1, 2, target_len, visited | (1u64 << v1), &mut path) {
                    return Some(path);
                }
                path.pop();
            }
        }
        None
    }

    fn dfs_cycle(
        &self,
        start: usize,
        curr: usize,
        depth: usize,
        target_len: usize,
        visited: u64,
        path: &mut Vec<usize>,
    ) -> bool {
        if depth == target_len {
            return (self.adj[curr] & (1u64 << start)) != 0;
        }

        let mut candidates = self.adj[curr] & !visited & mask_above(start);
        while candidates != 0 {
            let nxt = candidates.trailing_zeros() as usize;
            candidates &= candidates - 1;
            path.push(nxt);
            if self.dfs_cycle(start, nxt, depth + 1, target_len, visited | (1u64 << nxt), path) {
                return true;
            }
            path.pop();
        }
        false
    }

    /// Shortest cycle length, or 0 for a forest.
    pub fn compute_girth(&self) -> usize {
        let mut min_cycle = usize::MAX;
        for s in 0..self.n {
            let mut dist = vec![usize::MAX; self.n];
            let mut parent = vec![usize::MAX; self.n];
            let mut queue = std::collections::VecDeque::new();

            dist[s] = 0;
            queue.push_back(s);

            while let Some(u) = queue.pop_front() {
                let mut nbrs = self.adj[u];
                while nbrs != 0 {
                    let v = nbrs.trailing_zeros() as usize;
                    nbrs &= nbrs - 1;

                    if dist[v] == usize::MAX {
                        dist[v] = dist[u] + 1;
                        parent[v] = u;
                        queue.push_back(v);
                    } else if parent[u] != v && parent[v] != u {
                        min_cycle = min_cycle.min(dist[u] + dist[v] + 1);
                    }
                }
            }
        }
        if min_cycle == usize::MAX {
            0
        } else {
            min_cycle
        }
    }

    /// Number of connected components (isolated vertices included).
    pub fn component_count(&self) -> usize {
        let mut seen = 0u64;
        let mut comps = 0usize;
        for s in 0..self.n {
            if (seen >> s) & 1 == 1 {
                continue;
            }
            comps += 1;
            let mut frontier = 1u64 << s;
            seen |= frontier;
            while frontier != 0 {
                let mut next = 0u64;
                let mut f = frontier;
                while f != 0 {
                    let u = f.trailing_zeros() as usize;
                    f &= f - 1;
                    next |= self.adj[u] & !seen;
                }
                seen |= next;
                frontier = next;
            }
        }
        comps
    }

    /// `(diameter, bipartite)`. The diameter only counts reachable pairs, so callers
    /// must consult `component_count()` before interpreting it.
    pub fn compute_diameter(&self) -> (usize, bool) {
        let mut max_dist = 0;
        let mut is_bipartite = true;

        for s in 0..self.n {
            let mut dist = vec![usize::MAX; self.n];
            let mut queue = std::collections::VecDeque::new();
            dist[s] = 0;
            queue.push_back(s);

            while let Some(u) = queue.pop_front() {
                let mut nbrs = self.adj[u];
                while nbrs != 0 {
                    let v = nbrs.trailing_zeros() as usize;
                    nbrs &= nbrs - 1;

                    if dist[v] == usize::MAX {
                        dist[v] = dist[u] + 1;
                        max_dist = max_dist.max(dist[v]);
                        queue.push_back(v);
                    } else if dist[v] % 2 == dist[u] % 2 {
                        is_bipartite = false;
                    }
                }
            }
        }
        (max_dist, is_bipartite)
    }

    /// Existence-only verification: every power-of-two length <= n is searched.
    pub fn verify(&self) -> GraphVerificationResult {
        self.verify_with_cap(1)
    }

    /// Full verification. `count_cap` is the maximum number of cycles counted per
    /// length; `1` means "existence only", larger values produce exact counts up to
    /// the cap (marked `capped` when the cap is hit).
    pub fn verify_with_cap(&self, count_cap: u64) -> GraphVerificationResult {
        let mut min_deg = usize::MAX;
        let mut max_deg = 0;
        for i in 0..self.n {
            let d = self.degree(i);
            min_deg = min_deg.min(d);
            max_deg = max_deg.max(d);
        }
        if self.n == 0 {
            min_deg = 0;
        }

        let is_cubic = self.n > 0 && min_deg == 3 && max_deg == 3;
        let girth = self.compute_girth();
        let (diameter, bipartite) = self.compute_diameter();
        let components = self.component_count();
        let connected = components <= 1;

        let checked_lengths = pow2_cycle_lengths(self.n);
        let mut counts: Vec<CycleCount> = Vec::new();
        for &len in &checked_lengths {
            counts.push(self.count_cycles_of_length(len, count_cap));
        }

        let present = |len: usize| counts.iter().any(|c| c.length == len && c.count > 0);
        let has_c4 = present(4);
        let has_c8 = present(8);
        let has_c16 = present(16);
        let has_c32 = present(32);
        let has_c64 = present(64);

        let power_of_two_cycle_count = counts.iter().filter(|c| c.count > 0).count();

        // Witness for the shortest violated length, for solver feedback.
        let cycle_witness = counts
            .iter()
            .find(|c| c.count > 0)
            .and_then(|c| self.find_cycle_of_length(c.length));

        let mut diagnostic = String::new();
        if !is_cubic {
            diagnostic.push_str(&format!(
                "Degree profile: min_degree={}, max_degree={} (not strictly 3-regular). ",
                min_deg, max_deg
            ));
        }
        if !connected {
            diagnostic.push_str(&format!("Graph has {} components. ", components));
        }
        if let Some(ref wit) = cycle_witness {
            diagnostic.push_str(&format!(
                "Collision: cycle of length {} on vertices {:?}. ",
                wit.len(), wit
            ));
        }
        let summary: Vec<String> = counts
            .iter()
            .map(|c| {
                format!(
                    "C{}={}{}",
                    c.length,
                    c.count,
                    if c.capped { "+" } else { "" }
                )
            })
            .collect();
        diagnostic.push_str(&format!("Counts [{}]. ", summary.join(", ")));
        if min_deg >= 3 && power_of_two_cycle_count == 0 {
            diagnostic.push_str(&format!(
                "COUNTEREXAMPLE: min degree {} and no cycle of any length in {:?}.",
                min_deg, checked_lengths
            ));
        }

        // A counterexample needs min degree >= 3 and no cycle at ANY power-of-two
        // length that fits in n vertices, C64 at n == 64 included.
        let counterexample = self.n > 0 && min_deg >= 3 && power_of_two_cycle_count == 0;

        GraphVerificationResult {
            counterexample,
            n: self.n,
            edges: self.edge_count(),
            min_degree: min_deg,
            max_degree: max_deg,
            is_cubic,
            girth,
            diameter,
            connected,
            components,
            bipartite,
            checked_lengths,
            has_c4,
            has_c8,
            has_c16,
            has_c32,
            has_c64,
            counts,
            power_of_two_cycle_count,
            cycle_witness,
            diagnostic_trace: diagnostic,
        }
    }
}

pub fn make_k4() -> Graph64 {
    let mut g = Graph64::new(4);
    for u in 0..4 {
        for v in (u + 1)..4 {
            g.add_edge(u, v);
        }
    }
    g
}

pub fn make_petersen() -> Graph64 {
    let mut g = Graph64::new(10);
    for i in 0..5 {
        g.add_edge(i, (i + 1) % 5);
    }
    g.add_edge(5, 7);
    g.add_edge(7, 9);
    g.add_edge(9, 6);
    g.add_edge(6, 8);
    g.add_edge(8, 5);
    for i in 0..5 {
        g.add_edge(i, i + 5);
    }
    g
}

/// One of Markström's 24-vertex cubic graphs with no C4 and no C8 (it does have C16).
pub fn make_markstrom() -> Graph64 {
    let adj_list: [&[usize]; 24] = [
        &[1, 2, 3],
        &[0, 18, 19],
        &[0, 21, 22],
        &[0, 20, 23],
        &[6, 10, 12],
        &[6, 9, 11],
        &[4, 5, 12],
        &[8, 13, 14],
        &[7, 10, 17],
        &[5, 11, 15],
        &[4, 8, 17],
        &[5, 9, 16],
        &[4, 6, 16],
        &[7, 14, 15],
        &[7, 13, 19],
        &[9, 13, 18],
        &[11, 12, 21],
        &[8, 10, 20],
        &[1, 15, 19],
        &[1, 14, 18],
        &[3, 17, 23],
        &[2, 16, 22],
        &[2, 21, 23],
        &[3, 20, 22],
    ];
    Graph64::from_adjacency_list(24, &adj_list)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Independent O(n * n!) reference counter: plain recursive enumeration with no
    /// canonical-form tricks and no pruning. Used to cross-check the fast counter.
    fn reference_count(g: &Graph64, target_len: usize) -> u64 {
        fn walk(
            g: &Graph64,
            start: usize,
            curr: usize,
            depth: usize,
            target_len: usize,
            visited: &mut Vec<usize>,
            hits: &mut u64,
        ) {
            if depth == target_len {
                if (g.adj[curr] & (1u64 << start)) != 0 {
                    *hits += 1;
                }
                return;
            }
            for nxt in 0..g.n {
                if nxt <= start || visited.contains(&nxt) {
                    continue;
                }
                if (g.adj[curr] & (1u64 << nxt)) == 0 {
                    continue;
                }
                visited.push(nxt);
                walk(g, start, nxt, depth + 1, target_len, visited, hits);
                visited.pop();
            }
        }

        let mut hits = 0u64;
        for start in 0..g.n {
            let mut visited = vec![start];
            walk(g, start, start, 1, target_len, &mut visited, &mut hits);
        }
        hits / 2
    }

    /// Deterministic pseudo-random cubic graph via repeated 2-opt swaps on a Möbius
    /// ladder, mirroring how the CUDA kernel initializes.
    fn random_cubic(n: usize, seed: u64) -> Graph64 {
        let mut g = Graph64::new(n);
        for i in 0..n {
            g.add_edge(i, (i + 1) % n);
        }
        for i in 0..(n / 2) {
            g.add_edge(i, i + n / 2);
        }
        let mut state = seed | 1;
        let mut next = || {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            state
        };
        for _ in 0..(40 * n) {
            let u = (next() % n as u64) as usize;
            let x = (next() % n as u64) as usize;
            if u == x {
                continue;
            }
            let pick = |g: &Graph64, v: usize, k: u64| -> usize {
                let mut m = g.adj[v];
                let mut chosen = v;
                for _ in 0..=(k % 3) {
                    chosen = m.trailing_zeros() as usize;
                    m &= m - 1;
                }
                chosen
            };
            let v = pick(&g, u, next());
            let y = pick(&g, x, next());
            if v == x || y == u || v == y || u == x {
                continue;
            }
            if (g.adj[u] >> x) & 1 == 1 || (g.adj[v] >> y) & 1 == 1 {
                continue;
            }
            g.remove_edge(u, v);
            g.remove_edge(x, y);
            g.add_edge(u, x);
            g.add_edge(v, y);
        }
        g
    }

    #[test]
    fn test_k4() {
        let k4 = make_k4();
        let res = k4.verify();
        assert!(res.is_cubic);
        assert_eq!(res.girth, 3);
        assert!(res.has_c4);
        assert!(!res.counterexample);
        assert_eq!(res.checked_lengths, vec![4]);
        assert!(res.cycle_witness.is_some());
    }

    #[test]
    fn test_k4_c4_count_is_three() {
        // K4 has exactly three 4-cycles.
        let k4 = make_k4();
        let c = k4.count_cycles_of_length(4, 1000);
        assert_eq!(c.count, 3);
        assert!(!c.capped);
    }

    #[test]
    fn test_petersen() {
        let pet = make_petersen();
        let res = pet.verify_with_cap(10_000);
        assert!(res.is_cubic);
        assert_eq!(res.girth, 5);
        assert_eq!(res.diameter, 2);
        assert!(res.connected);
        assert!(!res.has_c4);
        assert!(res.has_c8);
        // The Petersen graph has exactly 15 eight-cycles.
        let c8 = res.counts.iter().find(|c| c.length == 8).unwrap();
        assert_eq!(c8.count, 15);
        assert!(!res.counterexample);
    }

    #[test]
    fn test_markstrom_24_counts_all_tiers() {
        let mark = make_markstrom();
        let res = mark.verify_with_cap(100_000);
        assert!(res.is_cubic);
        assert_eq!(res.n, 24);
        assert!(res.connected);
        assert!(!res.has_c4);
        assert!(!res.has_c8);
        assert!(res.has_c16);
        // Regression for the short-circuit bug: C16 presence must not suppress the
        // C16 count, and lengths above n must not be reported as checked.
        assert_eq!(res.checked_lengths, vec![4, 8, 16]);
        let c16 = res.counts.iter().find(|c| c.length == 16).unwrap();
        assert!(c16.count > 1, "expected many 16-cycles, got {}", c16.count);
        assert!(res.cycle_witness.is_some());
    }

    #[test]
    fn test_counts_match_reference_on_known_graphs() {
        for g in [make_k4(), make_petersen(), make_markstrom()] {
            for len in [3usize, 4, 5, 6, 8] {
                if len > g.n {
                    continue;
                }
                let fast = g.count_cycles_of_length(len, u64::MAX);
                let slow = reference_count(&g, len);
                assert_eq!(
                    fast.count, slow,
                    "n={} length={} fast={} reference={}",
                    g.n, len, fast.count, slow
                );
            }
        }
    }

    #[test]
    fn test_counts_match_reference_on_random_cubic() {
        for seed in 1..6u64 {
            let g = random_cubic(14, seed);
            for len in [4usize, 6, 8] {
                let fast = g.count_cycles_of_length(len, u64::MAX);
                let slow = reference_count(&g, len);
                assert_eq!(fast.count, slow, "seed={} length={}", seed, len);
            }
        }
    }

    #[test]
    fn test_cap_semantics() {
        let pet = make_petersen();
        let capped = pet.count_cycles_of_length(8, 3);
        assert!(capped.capped);
        assert!(capped.count >= 3);
        let exact = pet.count_cycles_of_length(8, u64::MAX);
        assert!(!exact.capped);
        assert_eq!(exact.count, 15);
    }

    #[test]
    fn test_existence_cap_one_agrees_with_full_count() {
        let g = random_cubic(16, 7);
        for len in [4usize, 8, 16] {
            let exists = g.count_cycles_of_length(len, 1).count > 0;
            let full = g.count_cycles_of_length(len, u64::MAX).count > 0;
            assert_eq!(exists, full, "length={}", len);
        }
    }

    #[test]
    fn test_disconnected_is_reported() {
        // Two disjoint K4s: cubic, but two components.
        let mut g = Graph64::new(8);
        for u in 0..4 {
            for v in (u + 1)..4 {
                g.add_edge(u, v);
                g.add_edge(u + 4, v + 4);
            }
        }
        let res = g.verify();
        assert!(res.is_cubic);
        assert!(!res.connected);
        assert_eq!(res.components, 2);
        assert!(res.has_c4);
        assert!(!res.counterexample);
    }

    #[test]
    fn test_c64_is_checked_at_n_64() {
        // C64 (a Hamiltonian cycle here) must be detected at n = 64, otherwise a
        // cubic graph with a 64-cycle would be misreported as a counterexample.
        let mut g = Graph64::new(64);
        for i in 0..64 {
            g.add_edge(i, (i + 1) % 64);
        }
        for i in 0..32 {
            g.add_edge(i, i + 32);
        }
        assert_eq!(pow2_cycle_lengths(64), vec![4, 8, 16, 32, 64]);
        let c64 = g.count_cycles_of_length(64, 1);
        assert!(c64.count > 0, "the Möbius ladder on 64 vertices has a 64-cycle");
    }

    #[test]
    fn test_no_cycle_longer_than_n_is_claimed() {
        let pet = make_petersen();
        assert_eq!(pet.count_cycles_of_length(16, 100).count, 0);
        assert_eq!(pow2_cycle_lengths(10), vec![4, 8]);
    }
}
