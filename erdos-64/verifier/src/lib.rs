use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GraphVerificationResult {
    pub counterexample: bool,
    pub n: usize,
    pub edges: usize,
    pub min_degree: usize,
    pub max_degree: usize,
    pub is_cubic: bool,
    pub has_c4: bool,
    pub has_c8: bool,
    pub has_c16: bool,
    pub has_c32: bool,
    pub power_of_two_cycle_count: usize,
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

    /// Fast O(n^2) bitwise check for 4-cycles.
    /// A 4-cycle exists iff two vertices have at least 2 common neighbors.
    pub fn has_c4(&self) -> bool {
        for u in 0..self.n {
            for w in (u + 1)..self.n {
                let common = self.adj[u] & self.adj[w];
                if common.count_ones() >= 2 {
                    return true;
                }
            }
        }
        false
    }

    /// Depth-first search with 64-bit visited bitmask to detect simple cycle of exact length L.
    pub fn has_cycle_of_length(&self, target_len: usize) -> bool {
        if target_len < 3 || target_len > self.n {
            return false;
        }

        if target_len == 4 {
            return self.has_c4();
        }

        // Search starting from each vertex v0
        for start in 0..=(self.n - target_len) {
            let visited = 1u64 << start;
            let mut neighbors = self.adj[start] & !((1u64 << (start + 1)) - 1);
            while neighbors != 0 {
                let v1 = neighbors.trailing_zeros() as usize;
                neighbors &= neighbors - 1;
                if self.dfs_cycle(start, v1, 2, target_len, visited | (1u64 << v1)) {
                    return true;
                }
            }
        }
        false
    }

    fn dfs_cycle(&self, start: usize, curr: usize, depth: usize, target_len: usize, visited: u64) -> bool {
        if depth == target_len {
            // Check if current vertex is connected back to start
            return (self.adj[curr] & (1u64 << start)) != 0;
        }

        // Restrict vertices to > start to prevent symmetry duplications
        let mut candidates = self.adj[curr] & !visited & !((1u64 << (start + 1)) - 1);
        while candidates != 0 {
            let nxt = candidates.trailing_zeros() as usize;
            candidates &= candidates - 1;
            if self.dfs_cycle(start, nxt, depth + 1, target_len, visited | (1u64 << nxt)) {
                return true;
            }
        }
        false
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
        let has_c4 = self.has_c4();
        let has_c8 = if self.n >= 8 { self.has_cycle_of_length(8) } else { false };
        let has_c16 = if self.n >= 16 { self.has_cycle_of_length(16) } else { false };
        let has_c32 = if self.n >= 32 { self.has_cycle_of_length(32) } else { false };

        let mut power_of_two_cycle_count = 0;
        if has_c4 { power_of_two_cycle_count += 1; }
        if has_c8 { power_of_two_cycle_count += 1; }
        if has_c16 { power_of_two_cycle_count += 1; }
        if has_c32 { power_of_two_cycle_count += 1; }

        let is_counterexample = (min_deg >= 3) && (power_of_two_cycle_count == 0);

        GraphVerificationResult {
            counterexample: is_counterexample,
            n: self.n,
            edges: self.edge_count(),
            min_degree: if self.n == 0 { 0 } else { min_deg },
            max_degree: max_deg,
            is_cubic,
            has_c4,
            has_c8,
            has_c16,
            has_c32,
            power_of_two_cycle_count,
        }
    }
}

/// Constructs the complete graph K_4
pub fn make_k4() -> Graph64 {
    let mut g = Graph64::new(4);
    for u in 0..4 {
        for v in (u + 1)..4 {
            g.add_edge(u, v);
        }
    }
    g
}

/// Constructs the Petersen graph (10 vertices, 3-regular, girth 5)
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

/// Constructs the official Markström graph (24 vertices, 3-regular, planar, House of Graphs #51419)
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
        assert_eq!(res.n, 4);
        assert_eq!(res.edges, 6);
        assert!(res.has_c4); // K4 has 4-cycles
        assert!(!res.counterexample);
    }

    #[test]
    fn test_petersen() {
        let pet = make_petersen();
        let res = pet.verify();
        assert!(res.is_cubic);
        assert_eq!(res.n, 10);
        assert_eq!(res.edges, 15);
        assert!(!res.has_c4); // Petersen has girth 5 (no C4)
        assert!(res.has_c8);  // Petersen HAS 8-cycles!
        assert!(!res.counterexample);
    }

    #[test]
    fn test_markstrom_24() {
        let mark = make_markstrom();
        let res = mark.verify();
        assert!(res.is_cubic);
        assert_eq!(res.n, 24);
        assert_eq!(res.edges, 36);
        assert!(!res.has_c4, "Markstrom graph must NOT have C4");
        assert!(!res.has_c8, "Markstrom graph must NOT have C8");
        assert!(res.has_c16, "Markstrom graph HAS C16");
        assert!(!res.counterexample);
    }
}
