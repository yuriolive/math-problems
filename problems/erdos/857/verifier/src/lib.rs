//! Ground truth for Erdős 857: is a family of sets 3-sunflower-free, and is it uniform?
//!
//! A triple of distinct sets `A, B, C` is a **3-sunflower** when all three pairwise
//! intersections coincide: `A∩B = A∩C = B∩C`. That common value is the core, and the
//! **empty core is included** — three pairwise disjoint sets are a sunflower. A family is
//! 3-sunflower-free when it contains no such triple.
//!
//! Two invariants this checker enforces rather than scores, because getting either wrong
//! produces a number that looks like a record and is worth nothing:
//!
//! 1. **Uniformity.** The tensor-power argument that turns a finite family into a bound on
//!    the capacity `μ₃` needs every set to have the same size. Without it the direct sum
//!    does not preserve sunflower-freeness: for `A₁ = A₂ ≠ A₃` a product sunflower only
//!    needs `A₁ ⊆ A₃`, which uniformity rules out by equal cardinality. Non-uniform
//!    families give large ratios and no bound at all — the certified values
//!    `M(n,3) = 2,3,5,8,12,19,29` all exceed the standing record's ratio and none of them
//!    is a bound on `μ₃`.
//! 2. **Distinctness.** A repeated set would make a "triple" that is not three distinct
//!    sets. Duplicates are rejected, not deduplicated, so a caller cannot lose sets
//!    silently.
//!
//! Ground truth means exact. `count_sunflowers` counts every triple with no cap; the
//! search kernels may cap their own counters, but nothing published comes from those.

use serde::{Deserialize, Serialize};

/// A family of subsets of `[n]`, each set a bitmask over the low `n` bits.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Family {
    pub n: usize,
    pub sets: Vec<u64>,
}

/// Why a family is not admissible. `Ok` carries the verified facts instead.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum Invalid {
    /// `n` exceeds the 64-bit mask width.
    OrderTooLarge { n: usize },
    /// A set has a bit set at or above position `n`.
    BitOutOfRange { index: usize, mask: u64 },
    /// Two entries are the same set. Position of the later one.
    Duplicate { index: usize, mask: u64 },
    /// Sets of differing size: the family is not uniform.
    NotUniform { expected: u32, found: u32, index: usize },
}

/// The verified state of a family. `sunflowers == 0` is the only admissible case.
///
/// Not `Eq`: `ratio` is an `f64` convenience for reading, and the fields that decide
/// admissibility are the integers.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Verified {
    pub n: usize,
    /// Number of sets.
    pub size: usize,
    /// The common set size. Uniformity is checked, so this is exact.
    pub k: u32,
    /// Exact count of unordered 3-sunflower triples. Never capped.
    pub sunflowers: u64,
    /// First offending triple found, as indices into `sets`, if any.
    pub witness: Option<[usize; 3]>,
    /// `size^(1/n)`, the quantity the capacity bound is about. Only meaningful when
    /// `sunflowers == 0`.
    pub ratio: f64,
}

impl Verified {
    /// A family that actually witnesses a lower bound on `μ₃`.
    pub fn is_admissible(&self) -> bool {
        self.sunflowers == 0
    }
}

fn mask_width_ok(n: usize) -> bool {
    n <= 64
}

/// Bits at or above `n` must be clear.
fn out_of_range(mask: u64, n: usize) -> bool {
    if n >= 64 {
        false
    } else {
        mask >> n != 0
    }
}

impl Family {
    pub fn new(n: usize, sets: Vec<u64>) -> Self {
        Family { n, sets }
    }

    /// Check the structural invariants before any counting happens.
    ///
    /// Deliberately separate from sunflower counting: a caller that ignores this and
    /// counts anyway would be measuring a family it has not established is uniform, which
    /// is the exact mistake that makes a non-bound look like a bound.
    pub fn check_invariants(&self) -> Result<u32, Invalid> {
        if !mask_width_ok(self.n) {
            return Err(Invalid::OrderTooLarge { n: self.n });
        }
        if self.sets.is_empty() {
            return Ok(0);
        }
        for (i, &m) in self.sets.iter().enumerate() {
            if out_of_range(m, self.n) {
                return Err(Invalid::BitOutOfRange { index: i, mask: m });
            }
        }

        let k = self.sets[0].count_ones();
        for (i, &m) in self.sets.iter().enumerate().skip(1) {
            let c = m.count_ones();
            if c != k {
                return Err(Invalid::NotUniform {
                    expected: k,
                    found: c,
                    index: i,
                });
            }
        }

        // Distinctness, by sorting a copy: O(m log m) rather than O(m²).
        let mut sorted = self.sets.clone();
        sorted.sort_unstable();
        for w in sorted.windows(2) {
            if w[0] == w[1] {
                let index = self
                    .sets
                    .iter()
                    .enumerate()
                    .filter(|(_, &m)| m == w[0])
                    .map(|(i, _)| i)
                    .nth(1)
                    .expect("duplicate located by sort must appear twice");
                return Err(Invalid::Duplicate { index, mask: w[0] });
            }
        }

        Ok(k)
    }

    /// Exact count of unordered 3-sunflower triples, with the first one found.
    ///
    /// `O(m³)` word operations: three ANDs and two comparisons per triple. Equality of the
    /// three pairwise intersections is the whole condition — it forces each to equal
    /// `A∩B∩C`, so the core never has to be computed.
    pub fn count_sunflowers(&self) -> (u64, Option<[usize; 3]>) {
        let s = &self.sets;
        let m = s.len();
        let mut count = 0u64;
        let mut witness = None;

        for i in 0..m {
            for j in (i + 1)..m {
                let ij = s[i] & s[j];
                for l in (j + 1)..m {
                    if ij == (s[i] & s[l]) && ij == (s[j] & s[l]) {
                        count += 1;
                        if witness.is_none() {
                            witness = Some([i, j, l]);
                        }
                    }
                }
            }
        }
        (count, witness)
    }

    /// Full verification: invariants, then the exact sunflower count.
    pub fn verify(&self) -> Result<Verified, Invalid> {
        let k = self.check_invariants()?;
        let (sunflowers, witness) = self.count_sunflowers();
        let size = self.sets.len();
        let ratio = if self.n == 0 || size == 0 {
            0.0
        } else {
            (size as f64).powf(1.0 / self.n as f64)
        };
        Ok(Verified {
            n: self.n,
            size,
            k,
            sunflowers,
            witness,
            ratio,
        })
    }

    /// Direct sum with another family, on disjoint ground sets.
    ///
    /// This is the operation the capacity bound rests on: if both families are uniform and
    /// sunflower-free, so is the result, and `|F ⊕ G| = |F|·|G|` on `n₁ + n₂` points. Used
    /// by the tests to confirm the argument holds on real families rather than on paper.
    pub fn direct_sum(&self, other: &Family) -> Family {
        let mut sets = Vec::with_capacity(self.sets.len() * other.sets.len());
        for &a in &self.sets {
            for &b in &other.sets {
                sets.push(a | (b << self.n));
            }
        }
        Family {
            n: self.n + other.n,
            sets,
        }
    }
}

/// Independent reference count, written for obviousness rather than speed.
///
/// Materializes each set as a sorted vector of elements and compares intersections as
/// vectors. Shares no code with the bitmask path, so the differential test in this crate
/// compares two genuinely different implementations.
pub fn reference_count_sunflowers(n: usize, sets: &[u64]) -> u64 {
    fn elements(mask: u64, n: usize) -> Vec<usize> {
        (0..n).filter(|&b| mask >> b & 1 == 1).collect()
    }
    fn meet(a: &[usize], b: &[usize]) -> Vec<usize> {
        a.iter().copied().filter(|x| b.contains(x)).collect()
    }

    let e: Vec<Vec<usize>> = sets.iter().map(|&m| elements(m, n)).collect();
    let m = e.len();
    let mut count = 0u64;
    for i in 0..m {
        for j in (i + 1)..m {
            let ij = meet(&e[i], &e[j]);
            for l in (j + 1)..m {
                if ij == meet(&e[i], &e[l]) && ij == meet(&e[j], &e[l]) {
                    count += 1;
                }
            }
        }
    }
    count
}

/// All `k`-subsets of `[n]` as bitmasks, ascending.
pub fn all_k_subsets(n: usize, k: u32) -> Vec<u64> {
    (0u64..(1u64 << n)).filter(|m| m.count_ones() == k).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn three_pairwise_disjoint_sets_are_a_sunflower() {
        // The empty core counts. This is the convention that makes the problem what it is,
        // and getting it wrong would silently admit families that are not sunflower-free.
        let f = Family::new(6, vec![0b000_011, 0b001_100, 0b110_000]);
        let v = f.verify().unwrap();
        assert_eq!(v.sunflowers, 1);
        assert!(!v.is_admissible());
    }

    #[test]
    fn equal_pairwise_intersections_with_nonempty_core() {
        // {1,2}, {1,3}, {1,4}: every pairwise intersection is {1}.
        let f = Family::new(5, vec![0b00011, 0b00101, 0b01001]);
        assert_eq!(f.verify().unwrap().sunflowers, 1);
    }

    #[test]
    fn unequal_intersections_are_not_a_sunflower() {
        // {1,2}, {1,3}, {2,3}: intersections {1}, {2}, {3} all differ.
        let f = Family::new(4, vec![0b0011, 0b0101, 0b0110]);
        let v = f.verify().unwrap();
        assert_eq!(v.sunflowers, 0);
        assert!(v.is_admissible());
        assert_eq!(v.k, 2);
    }

    #[test]
    fn non_uniform_family_is_rejected_not_scored() {
        let f = Family::new(4, vec![0b0011, 0b0111]);
        assert_eq!(
            f.verify(),
            Err(Invalid::NotUniform { expected: 2, found: 3, index: 1 })
        );
    }

    #[test]
    fn duplicates_are_rejected_not_deduplicated() {
        let f = Family::new(4, vec![0b0011, 0b0101, 0b0011]);
        assert_eq!(
            f.verify(),
            Err(Invalid::Duplicate { index: 2, mask: 0b0011 })
        );
    }

    #[test]
    fn bits_above_n_are_rejected() {
        let f = Family::new(3, vec![0b0011, 0b1001]);
        assert_eq!(
            f.verify(),
            Err(Invalid::BitOutOfRange { index: 1, mask: 0b1001 })
        );
    }

    #[test]
    fn order_above_64_is_refused() {
        let f = Family::new(65, vec![]);
        assert_eq!(f.verify(), Err(Invalid::OrderTooLarge { n: 65 }));
    }

    #[test]
    fn differential_against_reference_on_all_k_subsets() {
        // The bitmask path and the vector-of-elements path must agree exactly. This is the
        // highest-value test here: it compares two independent implementations.
        for n in 4..=7usize {
            for k in 1..=3u32 {
                let sets = all_k_subsets(n, k);
                let f = Family::new(n, sets.clone());
                let (fast, _) = f.count_sunflowers();
                let slow = reference_count_sunflowers(n, &sets);
                assert_eq!(fast, slow, "mismatch at n={n} k={k}");
            }
        }
    }

    #[test]
    fn all_pairs_on_four_points_is_not_sunflower_free() {
        // Worth pinning: the six 2-subsets of [4] are NOT admissible, because
        // {1,2}, {1,3}, {1,4} all meet in {1}. A star of three or more sets through a
        // common point is always a sunflower, which is the basic obstruction any
        // construction has to dodge.
        let f = Family::new(4, all_k_subsets(4, 2));
        let v = f.verify().unwrap();
        assert_eq!(v.size, 6);
        assert!(v.sunflowers > 0);
        assert!(!v.is_admissible());
    }

    #[test]
    fn the_triangle_is_the_admissible_family_on_three_points() {
        // {1,2}, {1,3}, {2,3}: intersections {1}, {2}, {3} all differ.
        let f = Family::new(3, all_k_subsets(3, 2));
        let v = f.verify().unwrap();
        assert_eq!(v.size, 3);
        assert_eq!(v.k, 2);
        assert_eq!(v.sunflowers, 0);
        assert!((v.ratio - 3f64.powf(1.0 / 3.0)).abs() < 1e-12);
    }

    #[test]
    fn direct_sum_preserves_uniformity_and_freeness() {
        // The tensor-power argument, checked on a real family rather than on paper: the
        // sum of two uniform sunflower-free families is uniform, sunflower-free, and has
        // exactly the product size.
        let f = Family::new(3, all_k_subsets(3, 2)); // the triangle
        assert!(f.verify().unwrap().is_admissible());

        let sum = f.direct_sum(&f);
        let v = sum.verify().unwrap();
        assert_eq!(v.n, 6);
        assert_eq!(v.size, 9);
        assert_eq!(v.k, 4);
        assert_eq!(v.sunflowers, 0, "direct sum introduced a sunflower");

        // And the ratio is preserved exactly, which is what makes it a capacity bound.
        assert!((v.ratio - f.verify().unwrap().ratio).abs() < 1e-12);
    }

    #[test]
    fn direct_sum_of_non_uniform_families_can_break_freeness() {
        // Why uniformity is an invariant and not a preference. Take a NON-uniform
        // sunflower-free family; its direct sum with itself need not stay sunflower-free,
        // which is exactly why the certified non-uniform M(n,3) values give no bound.
        let a = Family::new(3, vec![0b001, 0b011]); // {1}, {1,2}: not uniform
        assert_eq!(a.count_sunflowers().0, 0, "two sets cannot form a triple");

        let sum = a.direct_sum(&a);
        // Sets: {1}|{1}', {1}|{1,2}', {1,2}|{1}', {1,2}|{1,2}'
        let (count, _) = sum.count_sunflowers();
        assert!(
            count > 0,
            "expected the non-uniform direct sum to admit a sunflower; got {count}"
        );
    }
}
