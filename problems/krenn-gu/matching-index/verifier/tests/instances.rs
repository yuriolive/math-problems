//! What the checker must get right, stated as assertions rather than as prose.
//!
//! The first case is the gate: `k4-d3` is the one published graph of matching index 3, and
//! any change to this crate that stops reproducing dimension 3 on it has broken the model,
//! not the instance.

use verifier_krenn_gu::*;

fn load(name: &str) -> Report {
    let path = format!("../instances/{name}.json");
    let text = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("{path}: {e}"));
    let inst = parse(&text).unwrap_or_else(|e| panic!("{path}: {e}"));
    check(&inst, DEFAULT_MATCHING_CAP).unwrap_or_else(|e| panic!("{path}: {e}"))
}

#[test]
fn k4_dimension_three_is_reproduced() {
    let r = load("k4-d3");
    assert!(r.ghz);
    assert_eq!(r.dimension, 3);
    assert_eq!(r.matchings, 3);
    assert_eq!(r.violations.len(), 0);
    // n = 4 is allowed to reach 3, so this is not a counterexample to the conjecture.
    assert!(!r.counterexample);
}

#[test]
fn six_cycle_reaches_dimension_two() {
    let r = load("c6-d2");
    assert!(r.ghz);
    assert_eq!(r.dimension, 2);
    assert_eq!(r.matchings, 2);
    assert_eq!(r.connectivity, 2);
}

#[test]
fn destructive_interference_is_accepted_when_it_cancels() {
    let r = load("k4-d2-interference");
    assert!(r.ghz);
    assert_eq!(r.dimension, 2);
    assert_eq!(r.matchings, 4);
    assert_eq!(r.cancelling_nonmono, 1);
    assert_eq!(r.cancelling_nonmono_zero, 1);
    assert_eq!(r.violations.len(), 0);
}

#[test]
fn roots_of_unity_cancel_exactly() {
    let r = load("cyc3-cancellation");
    assert_eq!(r.matchings, 3);
    assert_eq!(r.feasible, 1);
    assert_eq!(r.cancelling_nonmono_zero, 1);
    assert_eq!(r.violations.len(), 0);
    // No monochromatic colouring is feasible, so it is not a GHZ graph however well the
    // interference works.
    assert!(!r.ghz);
}

#[test]
fn a_near_miss_is_reported_with_its_exact_weight() {
    let r = load("cyc3-no-cancellation");
    assert_eq!(r.violations.len(), 1);
    let v = &r.violations[0];
    assert_eq!(v.matchings, 3);
    assert_eq!(v.colouring, vec![0, 0, 1, 1]);
    // 1 + 2z, in the basis 1, z of Q(zeta_3).
    assert_eq!(v.weight, vec![Rat::int(1), Rat::int(2)]);
}

#[test]
fn three_one_factors_of_k6_leave_a_matching_that_cannot_be_cancelled() {
    let r = load("k6-d3-factorisation");
    assert!(!r.ghz);
    // Bogdanov's lemma made concrete: a non-monochromatic colouring with exactly one
    // matching, which no assignment of weights to this support can zero out.
    assert_eq!(r.unique_pm_nonmono, 1);
}

// ---------------------------------------------------------------------------
// Arithmetic.
// ---------------------------------------------------------------------------

#[test]
fn cyclotomic_polynomials() {
    assert_eq!(cyclotomic(1).unwrap(), vec![-1, 1]);
    assert_eq!(cyclotomic(2).unwrap(), vec![1, 1]);
    assert_eq!(cyclotomic(3).unwrap(), vec![1, 1, 1]);
    assert_eq!(cyclotomic(4).unwrap(), vec![1, 0, 1]);
    assert_eq!(cyclotomic(6).unwrap(), vec![1, -1, 1]);
    assert_eq!(cyclotomic(12).unwrap(), vec![1, 0, -1, 0, 1]);
}

#[test]
fn sums_of_roots_of_unity_are_decided_exactly() {
    let phi = cyclotomic(3).unwrap();
    let mut s = Cyc::zero(3);
    for i in 0..3 {
        let mut t = Cyc::zero(3);
        t.c[i] = Rat::one();
        s = s.add(&t).unwrap();
    }
    assert!(s.is_zero_at_root(&phi).unwrap(), "1 + z + z^2 = 0");

    let mut two = Cyc::zero(3);
    two.c[0] = Rat::one();
    two.c[1] = Rat::one();
    assert!(!two.is_zero_at_root(&phi).unwrap(), "1 + z != 0");

    // z * z^2 = 1 in the group ring, and the one-test agrees.
    let mut z = Cyc::zero(3);
    z.c[1] = Rat::one();
    let mut z2 = Cyc::zero(3);
    z2.c[2] = Rat::one();
    assert!(z.mul(&z2).unwrap().is_one_at_root(&phi).unwrap());
}

#[test]
fn overflow_is_a_fault_not_a_zero() {
    let big = Rat::int(i128::MAX);
    assert_eq!(big.add(Rat::one()).unwrap_err(), Fault::Overflow);
    assert_eq!(big.mul(Rat::int(2)).unwrap_err(), Fault::Overflow);
    // Denominators overflow too, and the common-denominator path has to notice.
    let tiny = Rat::new(1, i128::MAX).unwrap();
    let tiny2 = Rat::new(1, i128::MAX - 1).unwrap();
    assert_eq!(tiny.add(tiny2).unwrap_err(), Fault::Overflow);
}

// ---------------------------------------------------------------------------
// The input contract. Each of these would otherwise become a quiet wrong answer.
// ---------------------------------------------------------------------------

fn refuses(json: &str, needle: &str) {
    let inst = parse(json).and_then(|i| check(&i, DEFAULT_MATCHING_CAP).map(|_| ()));
    match inst {
        Ok(()) => panic!("accepted an instance it should refuse: {json}"),
        Err(f) => assert!(
            f.to_string().contains(needle),
            "wrong complaint for {json}: {f}"
        ),
    }
}

#[test]
fn malformed_instances_are_refused() {
    refuses(
        r#"{"n":3,"colours":1,"edges":[{"u":0,"v":1,"cu":0,"cv":0}]}"#,
        "n must be even",
    );
    refuses(
        r#"{"n":18,"colours":1,"edges":[]}"#,
        "outside the checker's range",
    );
    refuses(
        r#"{"n":4,"colours":1,"edges":[{"u":0,"v":1,"cu":0,"cv":0},{"u":0,"v":1,"cu":0,"cv":0}]}"#,
        "duplicate slot",
    );
    refuses(
        r#"{"n":4,"colours":1,"edges":[{"u":0,"v":1,"cu":0,"cv":0,"w":[[0,1]]}]}"#,
        "weight zero",
    );
    refuses(
        r#"{"n":4,"colours":1,"edges":[{"u":0,"v":0,"cu":0,"cv":0}]}"#,
        "self-loop",
    );
}

#[test]
fn the_matching_cap_reports_unknown_rather_than_a_count() {
    // K6 with every colour pair present on every edge has far more than four matchings.
    let mut edges = String::new();
    for u in 0..6 {
        for v in (u + 1)..6 {
            for cu in 0..2 {
                for cv in 0..2 {
                    if !edges.is_empty() {
                        edges.push(',');
                    }
                    edges.push_str(&format!(
                        r#"{{"u":{u},"v":{v},"cu":{cu},"cv":{cv}}}"#
                    ));
                }
            }
        }
    }
    let json = format!(r#"{{"n":6,"colours":2,"edges":[{edges}]}}"#);
    let inst = parse(&json).unwrap();
    let err = check(&inst, 4).unwrap_err();
    assert!(matches!(err, Fault::LimitExceeded(_)), "{err}");
}

#[test]
fn every_violation_is_reported_not_just_the_first() {
    // Two monochromatic colour classes, each with one matching, and two bichromatic edges
    // that give two distinct non-monochromatic colourings a single matching apiece.
    let json = r#"{"n":4,"colours":2,"edges":[
        {"u":0,"v":1,"cu":0,"cv":0},{"u":2,"v":3,"cu":0,"cv":0},
        {"u":0,"v":2,"cu":1,"cv":1},{"u":1,"v":3,"cu":1,"cv":1},
        {"u":0,"v":3,"cu":0,"cv":1},{"u":1,"v":2,"cu":0,"cv":1},
        {"u":0,"v":3,"cu":1,"cv":0},{"u":1,"v":2,"cu":1,"cv":0}]}"#;
    let r = check(&parse(json).unwrap(), DEFAULT_MATCHING_CAP).unwrap();
    assert!(r.violations.len() >= 2, "{:?}", r.violations);
    assert!(r.unique_pm_nonmono >= 2);
}
