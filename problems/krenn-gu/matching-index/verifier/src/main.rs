//! `ghzcheck`: exact ground-truth checker for one coloured, weighted multi-graph.
//!
//!     ghzcheck instances/k4-d3.json [--max-matchings N]
//!
//! Exit codes follow the repository convention:
//!   0  a GHZ graph on more than 4 vertices with dimension >= 3, a Krenn-Gu counterexample
//!   1  fully evaluated, and not a counterexample
//!   2  unknown: malformed input, a limit hit, or an integer overflow
//!
//! Exit code 1 is a statement about *this weighting only*. Refuting a support (a colouring
//! with the weights left free) is an algebraic question, not a matching-enumeration one;
//! `unique_pm_nonmono` in the report is the part of that question this program can answer.

use std::io::Read;
use verifier_krenn_gu::*;

fn rat_json(r: &[Rat]) -> serde_json::Value {
    serde_json::Value::Array(r.iter().map(|q| serde_json::json!([q.num, q.den])).collect())
}

fn unknown(reason: String) -> ! {
    let out = serde_json::json!({"status": "unknown", "reason": reason});
    println!("{}", serde_json::to_string_pretty(&out).unwrap());
    std::process::exit(2);
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut path: Option<String> = None;
    let mut cap = DEFAULT_MATCHING_CAP;
    let mut dump = false;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--max-matchings" => {
                i += 1;
                cap = args
                    .get(i)
                    .and_then(|s| s.parse().ok())
                    .unwrap_or_else(|| unknown("--max-matchings needs a number".into()));
            }
            "--dump-colourings" => dump = true,
            other => path = Some(other.to_string()),
        }
        i += 1;
    }

    let mut text = String::new();
    match &path {
        Some(p) => match std::fs::read_to_string(p) {
            Ok(t) => text = t,
            Err(e) => unknown(format!("cannot read {p}: {e}")),
        },
        None => {
            if std::io::stdin().read_to_string(&mut text).is_err() {
                unknown("cannot read stdin".into());
            }
        }
    }

    let inst = match parse(&text) {
        Ok(i) => i,
        Err(f) => unknown(f.to_string()),
    };

    let report = match check(&inst, cap) {
        Ok(r) => r,
        Err(f) => unknown(f.to_string()),
    };

    const SHOWN: usize = 32;
    let shown: Vec<serde_json::Value> = report
        .violations
        .iter()
        .take(SHOWN)
        .map(|v| {
            serde_json::json!({
                "colouring": v.colouring,
                "matchings": v.matchings,
                "kind": match v.kind {
                    Kind::NonMonoNonZero => "non-monochromatic colouring with non-zero weight",
                    Kind::MonoNotOne => "monochromatic colouring whose weight is not 1",
                },
                "weight": rat_json(&v.weight),
            })
        })
        .collect();

    let colourings: Vec<serde_json::Value> = if dump {
        report
            .colourings
            .iter()
            .map(|c| {
                serde_json::json!({
                    "colouring": c.colouring,
                    "matchings": c.matchings,
                    "monochromatic": c.monochromatic,
                    "weight": rat_json(&c.weight),
                })
            })
            .collect()
    } else {
        Vec::new()
    };

    let mut out = serde_json::json!({
        "instance": inst.name,
        "status": "evaluated",
        "n": report.n,
        "colours": report.colours,
        "root_of_unity": report.root,
        "ghz": report.ghz,
        "dimension": report.dimension,
        "counterexample": report.counterexample,
        "matchings": report.matchings,
        "feasible_colourings": report.feasible,
        "feasible_monochromatic": report.feasible_mono,
        "monochromatic_matchings": report.mono_matchings,
        "violations_total": report.violations.len(),
        "violations_listed": shown.len(),
        "violations_truncated": report.violations.len() > shown.len(),
        "violations": shown,
        "support": {
            "unique_pm_nonmono": report.unique_pm_nonmono,
            "cancelling_nonmono": report.cancelling_nonmono,
            "cancelling_nonmono_zero": report.cancelling_nonmono_zero,
        },
        "invariants": {
            "skeleton_edges": report.skeleton_edges,
            "coloured_edges": inst.edges.len(),
            "degrees": report.degrees,
            "min_degree": report.degrees.iter().min(),
            "max_degree": report.degrees.iter().max(),
            "vertex_connectivity": report.connectivity,
            "matching_covered": report.matching_covered,
        },
    });
    if dump {
        out["colourings"] = serde_json::Value::Array(colourings);
    }
    println!("{}", serde_json::to_string_pretty(&out).unwrap());
    std::process::exit(if report.counterexample { 0 } else { 1 });
}
