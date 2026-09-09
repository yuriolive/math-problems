//! Exact maximum `k`-uniform 3-sunflower-free family on `[n]`, by exhaustive branch and bound.
//!
//! Exists to be the independent reference the SAT sweep is checked against. Slow by
//! construction and shares no code with the encoder: it walks the `k`-subsets in order,
//! keeping a set only if it forms no sunflower with two already kept, and prunes when even
//! taking every remaining set could not beat the best found. That makes it a genuinely
//! different algorithm from "encode and ask a solver", which is the point — a differential
//! test against a reimplementation of the same idea would prove nothing.
//!
//!     brute <n> <k>
//!
//! Prints the maximum size, the ratio, and one witnessing family as JSON.

use std::env;

use verifier_857::{all_k_subsets, Family};

/// Does `cand` complete a sunflower with any two members of `chosen`?
fn makes_sunflower(chosen: &[u64], cand: u64) -> bool {
    for a in 0..chosen.len() {
        let ca = chosen[a] & cand;
        for b in (a + 1)..chosen.len() {
            if ca == (chosen[b] & cand) && ca == (chosen[a] & chosen[b]) {
                return true;
            }
        }
    }
    false
}

struct Search<'a> {
    sets: &'a [u64],
    best: usize,
    best_family: Vec<u64>,
}

impl<'a> Search<'a> {
    fn run(&mut self, start: usize, chosen: &mut Vec<u64>) {
        // Bound: everything still unconsidered, taken at once, cannot beat `best`.
        if chosen.len() + (self.sets.len() - start) <= self.best {
            return;
        }
        if chosen.len() > self.best {
            self.best = chosen.len();
            self.best_family = chosen.clone();
        }
        for i in start..self.sets.len() {
            let cand = self.sets[i];
            if makes_sunflower(chosen, cand) {
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
    if args.len() < 2 {
        eprintln!("usage: brute <n> <k>");
        std::process::exit(2);
    }
    let n: usize = args[0].parse().expect("n must be a number");
    let k: u32 = args[1].parse().expect("k must be a number");

    let sets = all_k_subsets(n, k);
    let mut search = Search {
        sets: &sets,
        best: 0,
        best_family: Vec::new(),
    };
    search.run(0, &mut Vec::new());

    // Re-verify the witness with the library checker rather than trusting the search.
    let family = Family::new(n, search.best_family.clone());
    let verified = family.verify().expect("brute-force witness must be admissible");
    assert_eq!(verified.size, search.best, "witness size disagrees with search");
    assert_eq!(verified.sunflowers, 0, "brute-force witness has a sunflower");

    println!(
        "{{\"n\":{},\"k\":{},\"candidates\":{},\"max\":{},\"ratio\":{:.6},\"family\":{:?}}}",
        n,
        k,
        sets.len(),
        verified.size,
        verified.ratio,
        search.best_family
    );
}
