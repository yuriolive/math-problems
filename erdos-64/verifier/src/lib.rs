use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GraphVerificationResult {
    pub counterexample: bool,
    pub n: usize,
    pub edges: usize,
    pub min_degree: usize,
    pub max_degree: usize,
    pub is_cubic: bool,
    pub girth: usize,
    pub diameter: usize,
    pub bipartite: bool,
    pub has_c4: bool,
    pub has_c8: bool,
    pub has_c16: bool,
    pub has_c32: bool,
    pub power_of_two_cycle_count: usize,
    pub cycle_witness: Option<Vec<usize>>,
    pub diagnostic_trace: String,
}

#[derive(Debug, Clone)]
pub struct Graph64 {
    pub n: usize,
    pub adj: [u64; 64],
}

impl Graph64 {
    pub fn new(n: usize) -> Self {
        assert!(n <= 64, "Graph size must be <= 64 vertices");
        Self {
            n,
            adj: [0u64; 64],
        }
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
        let mut sum = 0;
        for i in 0..self.n {
            sum += self.degree(i);
        }
        sum / 2
    }

    /// Fast O(n^2) bitwise check for 4-cycles returning witness if present.
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

    /// Depth-first search with 64-bit visited bitmask to detect simple cycle of exact length L.
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
            let mut neighbors = self.adj[start] & !((1u64 << (start + 1)) - 1);
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

        let mut candidates = self.adj[curr] & !visited & !((1u64 << (start + 1)) - 1);
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

    /// Computes shortest cycle length (girth) via BFS
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
                        let cycle_len = dist[u] + dist[v] + 1;
                        min_cycle = min_cycle.min(cycle_len);
                    }
                }
            }
        }
        if min_cycle == usize::MAX { 0 } else { min_cycle }
    }

    /// Computes graph diameter via all-pairs shortest paths
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

    /// Complete verification of the Erdős-Gyárfás condition
    pub fn verify(&self) -> GraphVerificationResult {
        let mut min_deg = usize::MAX;
        let mut max_deg = 0;
        for i in 0..self.n {
            let d = self.degree(i);
            min_deg = min_deg.min(d);
            max_deg = max_deg.max(d);
        }

        let is_cubic = min_deg == 3 && max_deg == 3;
        let girth = self.compute_girth();
        let (diameter, bipartite) = self.compute_diameter();

        let c4_wit = self.find_c4();
        let has_c4 = c4_wit.is_some();

        let c8_wit = if !has_c4 && self.n >= 8 {
            self.find_cycle_of_length(8)
        } else if has_c4 {
            None
        } else {
            None
        };
        let has_c8 = c8_wit.is_some();

        let c16_wit = if !has_c4 && !has_c8 && self.n >= 16 {
            self.find_cycle_of_length(16)
        } else {
            None
        };
        let has_c16 = c16_wit.is_some();

        let c32_wit = if !has_c4 && !has_c8 && !has_c16 && self.n >= 32 {
            self.find_cycle_of_length(32)
        } else {
            None
        };
        let has_c32 = c32_wit.is_some();

        let mut power_of_two_cycle_count = 0;
        if has_c4 { power_of_two_cycle_count += 1; }
        if has_c8 { power_of_two_cycle_count += 1; }
        if has_c16 { power_of_two_cycle_count += 1; }
        if has_c32 { power_of_two_cycle_count += 1; }

        let cycle_witness = c4_wit.or(c8_wit).or(c16_wit).or(c32_wit);

        let mut diagnostic = String::new();
        if !is_cubic {
            diagnostic.push_str(&format!("Degree violation: min_degree={}, max_degree={}. Must be strictly 3. ", min_deg, max_deg));
        }
        if let Some(ref wit) = cycle_witness {
            diagnostic.push_str(&format!("Collision: Found cycle of length {} on vertices {:?}. ", wit.len(), wit));
        } else if is_cubic {
            diagnostic.push_str("SUCCESS: No 2^k cycles (C4, C8, C16, C32) detected!");
        }

        let is_counterexample = (min_deg >= 3) && (power_of_two_cycle_count == 0);

        GraphVerificationResult {
            counterexample: is_counterexample,
            n: self.n,
            edges: self.edge_count(),
            min_degree: if self.n == 0 { 0 } else { min_deg },
            max_degree: max_deg,
            is_cubic,
            girth,
            diameter,
            bipartite,
            has_c4,
            has_c8,
            has_c16,
            has_c32,
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

    #[test]
    fn test_k4() {
        let k4 = make_k4();
        let res = k4.verify();
        assert!(res.is_cubic);
        assert_eq!(res.girth, 3);
        assert!(res.has_c4);
        assert!(res.cycle_witness.is_some());
    }

    #[test]
    fn test_petersen() {
        let pet = make_petersen();
        let res = pet.verify();
        assert!(res.is_cubic);
        assert_eq!(res.girth, 5);
        assert_eq!(res.diameter, 2);
        assert!(!res.has_c4);
        assert!(res.has_c8);
        assert!(res.cycle_witness.is_some());
    }

    #[test]
    fn test_markstrom_24() {
        let mark = make_markstrom();
        let res = mark.verify();
        assert!(res.is_cubic);
        assert_eq!(res.n, 24);
        assert!(!res.has_c4);
        assert!(!res.has_c8);
        assert!(res.has_c16);
        assert!(res.cycle_witness.is_some());
    }
}
