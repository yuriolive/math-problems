//! Verify one family, read as JSON on stdin. Ground truth for anything a search reports.
//!
//!     echo '{"n":6,"k":3,"sets":[7,11,21,26,28,38,41,44,49,50]}' | check
//!
//! `k` in the input is ignored: the checker derives it and enforces uniformity itself, so a
//! caller cannot assert a `k` the family does not have. Exit 0 when the family is
//! admissible — uniform, distinct, in range, and 3-sunflower-free — and 1 otherwise, so it
//! can gate a script.

use std::io::{self, Read};

use verifier_857::Family;

#[derive(serde::Deserialize)]
struct Input {
    n: usize,
    sets: Vec<u64>,
}

fn main() {
    let mut buf = String::new();
    io::stdin()
        .read_to_string(&mut buf)
        .expect("failed to read stdin");
    let input: Input = serde_json::from_str(&buf).expect("stdin must be JSON {n, sets}");

    let family = Family::new(input.n, input.sets);
    match family.verify() {
        Ok(v) => {
            println!(
                "{{\"n\":{},\"size\":{},\"k\":{},\"sunflowers\":{},\"ratio\":{:.6},\"admissible\":{}}}",
                v.n, v.size, v.k, v.sunflowers, v.ratio, v.is_admissible()
            );
            std::process::exit(if v.is_admissible() { 0 } else { 1 });
        }
        Err(e) => {
            println!("{{\"invalid\":{:?}}}", e);
            std::process::exit(1);
        }
    }
}
