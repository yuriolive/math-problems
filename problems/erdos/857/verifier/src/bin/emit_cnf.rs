//! Emit DIMACS asking: is there a `k`-uniform 3-sunflower-free family of size `>= s` on `[n]`?
//!
//! One variable per `k`-subset of `[n]`, in ascending mask order, so variable `i + 1`
//! corresponds to `all_k_subsets(n, k)[i]`. Two constraint groups:
//!
//! * **No sunflower.** One clause `(¬x_S ∨ ¬x_T ∨ ¬x_U)` per sunflower triple. The triples
//!   are enumerated here rather than in the driver because there are `O(N³)` candidate
//!   triples and at `n = 12, k = 6` that is already ~1.3·10⁸ checks.
//! * **At least `s` chosen**, as a Sinz sequential counter. "At least `s` of the `x`" is
//!   "at most `N - s` of the `¬x`", so the counter runs over negated literals.
//!
//! A SAT model is a *candidate*, never a result: the driver re-verifies every model with
//! the compiled checker in this crate, which shares no code with this encoder.
//!
//!     emit_cnf <n> <k> <s> [--stats]
//!
//! Writes DIMACS to stdout. `--stats` writes counts to stderr instead of solving.

use std::env;
use std::io::{self, BufWriter, Write};

use verifier_857::all_k_subsets;

fn usage() -> ! {
    eprintln!("usage: emit_cnf <n> <k> <s> [--stats]");
    std::process::exit(2);
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() < 3 {
        usage();
    }
    let n: usize = args[0].parse().unwrap_or_else(|_| usage());
    let k: u32 = args[1].parse().unwrap_or_else(|_| usage());
    let s: usize = args[2].parse().unwrap_or_else(|_| usage());
    let stats_only = args.iter().any(|a| a == "--stats");

    if n > 64 {
        eprintln!("n must be at most 64 (64-bit masks)");
        std::process::exit(2);
    }

    let sets = all_k_subsets(n, k);
    let num_sets = sets.len();

    if s > num_sets {
        // Asking for more sets than exist: trivially unsatisfiable, and say so in the
        // file rather than emitting something a solver would call SAT.
        println!("c n={n} k={k} s={s}: only {num_sets} k-subsets exist");
        println!("p cnf 1 2");
        println!("1 0");
        println!("-1 0");
        return;
    }

    // Sunflower triples. Same condition as the library's counter: the three pairwise
    // intersections being equal is the whole test.
    let mut triples: Vec<[usize; 3]> = Vec::new();
    for i in 0..num_sets {
        for j in (i + 1)..num_sets {
            let ij = sets[i] & sets[j];
            for l in (j + 1)..num_sets {
                if ij == (sets[i] & sets[l]) && ij == (sets[j] & sets[l]) {
                    triples.push([i, j, l]);
                }
            }
        }
    }

    // Sinz sequential counter over the negated literals, bound r = N - s.
    let r = num_sets - s;
    let counter_vars = if r == 0 || num_sets < 2 {
        0
    } else {
        (num_sets - 1) * r
    };
    // aux(i, j) is 1-indexed in both arguments: i in 1..=N-1, j in 1..=r.
    let aux = |i: usize, j: usize| -> i64 {
        (num_sets + (i - 1) * r + j) as i64
    };
    let lit = |i: usize| -> i64 { (i + 1) as i64 }; // x_i, 0-indexed set -> 1-indexed var

    let mut clauses: Vec<Vec<i64>> = Vec::new();

    for t in &triples {
        clauses.push(vec![-lit(t[0]), -lit(t[1]), -lit(t[2])]);
    }

    if r == 0 {
        // Every set must be chosen.
        for i in 0..num_sets {
            clauses.push(vec![lit(i)]);
        }
    } else if r < num_sets {
        // L_i = ¬x_i. At most r of the L_i may be true.
        let big_l = |i: usize| -> i64 { -lit(i) };

        clauses.push(vec![-big_l(0), aux(1, 1)]);
        for j in 2..=r {
            clauses.push(vec![-aux(1, j)]);
        }
        for i in 2..=(num_sets - 1) {
            clauses.push(vec![-big_l(i - 1), aux(i, 1)]);
            clauses.push(vec![-aux(i - 1, 1), aux(i, 1)]);
            for j in 2..=r {
                clauses.push(vec![-big_l(i - 1), -aux(i - 1, j - 1), aux(i, j)]);
                clauses.push(vec![-aux(i - 1, j), aux(i, j)]);
            }
            clauses.push(vec![-big_l(i - 1), -aux(i - 1, r)]);
        }
        clauses.push(vec![-big_l(num_sets - 1), -aux(num_sets - 1, r)]);
    }
    // r >= num_sets leaves the cardinality constraint vacuous, which is correct: s == 0.

    let num_vars = num_sets + counter_vars;

    if stats_only {
        eprintln!("n={n} k={k} s={s}");
        eprintln!("  k-subsets (vars)   {num_sets}");
        eprintln!("  sunflower triples  {}", triples.len());
        eprintln!("  counter vars       {counter_vars}");
        eprintln!("  total vars         {num_vars}");
        eprintln!("  total clauses      {}", clauses.len());
        return;
    }

    let stdout = io::stdout();
    let mut out = BufWriter::new(stdout.lock());
    writeln!(
        out,
        "c uniform 3-sunflower-free: n={n} k={k} size>={s}, {} triples",
        triples.len()
    )
    .unwrap();
    writeln!(out, "p cnf {} {}", num_vars, clauses.len()).unwrap();
    for c in &clauses {
        for l in c {
            write!(out, "{l} ").unwrap();
        }
        writeln!(out, "0").unwrap();
    }
    out.flush().unwrap();
}
