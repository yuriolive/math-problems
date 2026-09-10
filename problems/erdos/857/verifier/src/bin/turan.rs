//! Exact `ex(n, K_4^-)`: largest 3-uniform hypergraph on `[n]` with no 4 vertices
//! spanning 3 or more edges.
//!
//! This exists to test an identity, not to be fast. By complementation,
//! `(A ∩ B)^c = A^c ∪ B^c`, a family of `(n-3)`-sets with no 3-sunflower corresponds to a
//! family of triples with no three members having equal pairwise *unions*. Working out
//! which configurations that forbids: with `U` the common union, `|U| = 4` is three
//! distinct triples inside a 4-set, `|U| = 5` is impossible, and `|U| = 6` would force the
//! three to be pairwise disjoint, which in turn forces two of them to coincide. So the
//! only obstruction is three triples in a common 4-set -- a copy of `K_4^-` -- and
//!
//!     Munif(n, n-3) = ex(n, K_4^-).
//!
//! That identity is what makes this repository's sweep relevant to the Frankl-Füredi
//! problem, so it is checked here by computing the right-hand side directly, in terms of
//! vertices and edges, sharing no code with the sunflower path.
//!
//!     turan <n>

use std::env;

/// All 3-subsets of `[n]` as (a, b, c) with a < b < c.
fn triples(n: usize) -> Vec<[usize; 3]> {
    let mut out = Vec::new();
    for a in 0..n {
        for b in (a + 1)..n {
            for c in (b + 1)..n {
                out.push([a, b, c]);
            }
        }
    }
    out
}

/// Would adding `cand` put 3 edges inside some 4-set?
///
/// Two triples sharing exactly two vertices span a 4-set; a third edge inside that same
/// 4-set completes the copy. Checking pairs of chosen edges against the candidate covers
/// every case, because any 3 edges in a 4-set pairwise share exactly two vertices.
fn makes_k4minus(chosen: &[[usize; 3]], cand: [usize; 3]) -> bool {
    for i in 0..chosen.len() {
        for j in (i + 1)..chosen.len() {
            // Union of the three must be a 4-set.
            let mut seen = [false; 64];
            let mut count = 0;
            for e in [chosen[i], chosen[j], cand] {
                for v in e {
                    if !seen[v] {
                        seen[v] = true;
                        count += 1;
                    }
                }
            }
            if count == 4 {
                return true;
            }
        }
    }
    false
}

struct Search {
    edges: Vec<[usize; 3]>,
    best: usize,
    best_set: Vec<[usize; 3]>,
}

impl Search {
    fn run(&mut self, start: usize, chosen: &mut Vec<[usize; 3]>) {
        if chosen.len() + (self.edges.len() - start) <= self.best {
            return;
        }
        if chosen.len() > self.best {
            self.best = chosen.len();
            self.best_set = chosen.clone();
        }
        for i in start..self.edges.len() {
            let cand = self.edges[i];
            if makes_k4minus(chosen, cand) {
                continue;
            }
            chosen.push(cand);
            self.run(i + 1, chosen);
            chosen.pop();
        }
    }
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: turan <n>");
        std::process::exit(2);
    }
    let n: usize = args[0].parse().expect("n must be a number");
    if n > 60 {
        eprintln!("n is capped at 60 by the vertex-seen array");
        std::process::exit(2);
    }

    let edges = triples(n);
    let total = edges.len();
    let mut search = Search {
        edges,
        best: 0,
        best_set: Vec::new(),
    };
    search.run(0, &mut Vec::new());

    // Re-check the winner from scratch: no 4 vertices may span 3 edges.
    let found = &search.best_set;
    for a in 0..n {
        for b in (a + 1)..n {
            for c in (b + 1)..n {
                for d in (c + 1)..n {
                    let quad = [a, b, c, d];
                    let inside = found
                        .iter()
                        .filter(|e| e.iter().all(|v| quad.contains(v)))
                        .count();
                    assert!(inside <= 2, "witness has {inside} edges inside {quad:?}");
                }
            }
        }
    }

    println!(
        "{{\"n\":{},\"triples\":{},\"ex_K4minus\":{},\"edges\":{:?}}}",
        n, total, search.best, search.best_set
    );
}
