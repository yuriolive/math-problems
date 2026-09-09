//! Emit the `k`-subsets of `[n]` and every 3-sunflower triple among them.
//!
//! Split out from the solver so the `O(N³)` enumeration runs compiled: at `n = 12, k = 6`
//! that is 924 subsets and ~1.3·10⁸ candidate triples, which is a second here and minutes
//! in Python.
//!
//!     triples <n> <k>
//!
//! Output is two sections on stdout, both plain text:
//!
//!     sets <N>
//!     <mask> ...            one per line, ascending, so line i is variable i
//!     triples <T>
//!     <i> <j> <l>           one per line, indices into the set list
//!
//! The driver turns each triple into a clause forbidding all three at once, then re-verifies
//! whatever the solver returns with this crate's checker.

use std::env;
use std::io::{self, BufWriter, Write};

use verifier_857::all_k_subsets;

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() < 2 {
        eprintln!("usage: triples <n> <k>");
        std::process::exit(2);
    }
    let n: usize = args[0].parse().expect("n must be a number");
    let k: u32 = args[1].parse().expect("k must be a number");
    if n > 64 {
        eprintln!("n must be at most 64 (64-bit masks)");
        std::process::exit(2);
    }

    let sets = all_k_subsets(n, k);
    let num = sets.len();

    // Collected before printing so the count can head the section.
    let mut triples: Vec<[u32; 3]> = Vec::new();
    for i in 0..num {
        for j in (i + 1)..num {
            let ij = sets[i] & sets[j];
            for l in (j + 1)..num {
                if ij == (sets[i] & sets[l]) && ij == (sets[j] & sets[l]) {
                    triples.push([i as u32, j as u32, l as u32]);
                }
            }
        }
    }

    let stdout = io::stdout();
    let mut out = BufWriter::new(stdout.lock());
    writeln!(out, "sets {num}").unwrap();
    for m in &sets {
        writeln!(out, "{m}").unwrap();
    }
    writeln!(out, "triples {}", triples.len()).unwrap();
    for t in &triples {
        writeln!(out, "{} {} {}", t[0], t[1], t[2]).unwrap();
    }
    out.flush().unwrap();
}
