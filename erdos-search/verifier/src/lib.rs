use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub const BOHMAN_CONSTANT: f64 = 0.22002;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VerificationResult {
    pub valid: bool,
    pub n: usize,
    pub max_val: u64,
    pub ratio: f64,
    pub beats_bohman: bool,
    pub collision: Option<[u64; 2]>,
}

/// Verifies whether all 2^n subset sums of the given set are strictly distinct.
/// If valid, returns exit code info and metrics.
/// If invalid, returns the collision (e.g., the two colliding subset masks or colliding sums).
pub fn verify_subset_sums(elements: &[u64]) -> VerificationResult {
    let n = elements.len();
    if n == 0 {
        return VerificationResult {
            valid: true,
            n: 0,
            max_val: 0,
            ratio: 0.0,
            beats_bohman: false,
            collision: None,
        };
    }

    // Check for positive integers
    for &x in elements {
        if x == 0 {
            return VerificationResult {
                valid: false,
                n,
                max_val: *elements.iter().max().unwrap_or(&0),
                ratio: (*elements.iter().max().unwrap_or(&0) as f64) / (2.0f64.powi(n as i32)),
                beats_bohman: false,
                collision: Some([0, 0]),
            };
        }
    }

    let mut sorted = elements.to_vec();
    sorted.sort_unstable();

    // Check for duplicates in the input set (immediate collision a_i == a_j)
    for i in 1..n {
        if sorted[i] == sorted[i - 1] {
            return VerificationResult {
                valid: false,
                n,
                max_val: sorted[n - 1],
                ratio: (sorted[n - 1] as f64) / (2.0f64.powi(n as i32)),
                beats_bohman: false,
                collision: Some([1 << (i - 1), 1 << i]),
            };
        }
    }

    let max_val = sorted[n - 1];
    let ratio = (max_val as f64) / (2.0f64.powi(n as i32));
    let beats_bohman = ratio < BOHMAN_CONSTANT;

    // Filter 1: Pair difference check (fast O(n^2) necessary filter)
    // If a_j - a_i == a_l - a_k with {i, j} and {k, l} disjoint, then a_j + a_k == a_l + a_i.
    if let Some((m1, m2)) = check_pair_differences(&sorted) {
        return VerificationResult {
            valid: false,
            n,
            max_val,
            ratio,
            beats_bohman,
            collision: Some([m1, m2]),
        };
    }

    // For n <= 24 (or if total sum fits in memory <= 64 MB), use ultra-fast bit-parallel shifts
    let total_sum: u64 = sorted.iter().sum();
    let max_words = (total_sum as usize / 64) + 2;

    if max_words <= 8_000_000 {
        // Bit-parallel shift verification
        match verify_bitset_shifts(&sorted, total_sum) {
            Ok(()) => VerificationResult {
                valid: true,
                n,
                max_val,
                ratio,
                beats_bohman,
                collision: None,
            },
            Err((m1, m2)) => VerificationResult {
                valid: false,
                n,
                max_val,
                ratio,
                beats_bohman,
                collision: Some([m1, m2]),
            },
        }
    } else {
        // Meet-in-the-middle verification for very large sum cases
        match verify_meet_in_middle(&sorted) {
            Ok(()) => VerificationResult {
                valid: true,
                n,
                max_val,
                ratio,
                beats_bohman,
                collision: None,
            },
            Err((m1, m2)) => VerificationResult {
                valid: false,
                n,
                max_val,
                ratio,
                beats_bohman,
                collision: Some([m1, m2]),
            },
        }
    }
}

/// Fast necessary filter: checks if any two pairs of elements have the same difference.
/// a_j - a_i = a_l - a_k  =>  a_j + a_k = a_l + a_i
fn check_pair_differences(sorted: &[u64]) -> Option<(u64, u64)> {
    let n = sorted.len();
    let mut diffs: HashMap<u64, (usize, usize)> = HashMap::with_capacity(n * (n - 1) / 2);

    for j in 0..n {
        for i in 0..j {
            let diff = sorted[j] - sorted[i];
            if let Some(&(k, l)) = diffs.get(&diff) {
                // If disjoint indices: {i, j} and {k, l}
                if i != k && i != l && j != k && j != l {
                    // a_j + a_k = a_l + a_i
                    let mask1 = (1u64 << j) | (1u64 << k);
                    let mask2 = (1u64 << l) | (1u64 << i);
                    return Some((mask1, mask2));
                }
            } else {
                diffs.insert(diff, (i, j));
            }
        }
    }
    None
}

/// Ultra-fast bit-parallel shift verifier using dynamic u64 bitset.
/// At each step k with element x = sorted[k], we check if (bitset & (bitset << x)) != 0.
/// If non-zero, a subset collision exists and is reported immediately.
fn verify_bitset_shifts(sorted: &[u64], total_sum: u64) -> Result<(), (u64, u64)> {
    let word_count = (total_sum as usize / 64) + 2;
    let mut bitset = vec![0u64; word_count];
    bitset[0] = 1u64; // Sum 0 is reachable

    let mut current_max_sum = 0usize;

    for (k, &val) in sorted.iter().enumerate() {
        let x = val as usize;
        let word_shift = x / 64;
        let bit_shift = x % 64;
        let old_words = (current_max_sum / 64) + 1;
        let new_words = ((current_max_sum + x) / 64) + 1;

        // Check for collision
        let mut collision_found = false;
        let mut collision_sum = 0usize;

        for w in word_shift..new_words {
            let src_high = if w >= word_shift && (w - word_shift) < old_words {
                bitset[w - word_shift]
            } else {
                0
            };
            let src_low = if bit_shift > 0 && w >= (word_shift + 1) && (w - word_shift - 1) < old_words {
                bitset[w - word_shift - 1]
            } else {
                0
            };

            let shifted_w = if bit_shift == 0 {
                src_high
            } else {
                (src_high << bit_shift) | (src_low >> (64 - bit_shift))
            };

            let overlap = bitset[w] & shifted_w;
            if overlap != 0 {
                collision_found = true;
                let tz = overlap.trailing_zeros() as usize;
                collision_sum = w * 64 + tz;
                break;
            }
        }

        if collision_found {
            // Find the colliding subset masks:
            // One subset in sorted[0..k] sums to collision_sum.
            // Another subset in sorted[0..k] sums to (collision_sum - x).
            let target1 = collision_sum as u64;
            let target2 = (collision_sum - x) as u64;

            let m1 = find_subset_mask(&sorted[0..k], target1).unwrap_or(0);
            let m2 = find_subset_mask(&sorted[0..k], target2).unwrap_or(0) | (1u64 << k);
            return Err((m1, m2));
        }

        // Apply shift: bitset |= (bitset << x)
        // Iterate backwards from top word down to word_shift to update safely
        for w in (word_shift..new_words).rev() {
            let src_high = if w >= word_shift && (w - word_shift) < old_words {
                bitset[w - word_shift]
            } else {
                0
            };
            let src_low = if bit_shift > 0 && w >= (word_shift + 1) && (w - word_shift - 1) < old_words {
                bitset[w - word_shift - 1]
            } else {
                0
            };

            let shifted_w = if bit_shift == 0 {
                src_high
            } else {
                (src_high << bit_shift) | (src_low >> (64 - bit_shift))
            };

            bitset[w] |= shifted_w;
        }

        current_max_sum += x;
    }

    Ok(())
}

/// Backtracking solver to reconstruct the subset mask for a known unique sum
fn find_subset_mask(slice: &[u64], target: u64) -> Option<u64> {
    if target == 0 {
        return Some(0);
    }
    if slice.is_empty() {
        return None;
    }

    fn dfs(slice: &[u64], idx: usize, remaining: u64, current_mask: u64) -> Option<u64> {
        if remaining == 0 {
            return Some(current_mask);
        }
        if idx == 0 {
            return None;
        }
        let next_idx = idx - 1;
        let val = slice[next_idx];
        if val <= remaining {
            if let Some(m) = dfs(slice, next_idx, remaining - val, current_mask | (1u64 << next_idx)) {
                return Some(m);
            }
        }
        dfs(slice, next_idx, remaining, current_mask)
    }

    dfs(slice, slice.len(), target, 0)
}

/// Meet-in-the-middle verification for sets with large sum
fn verify_meet_in_middle(sorted: &[u64]) -> Result<(), (u64, u64)> {
    let n = sorted.len();
    let m = n / 2;
    let (left, right) = sorted.split_at(m);

    // Generate left sums
    let left_count = 1usize << m;
    let mut left_sums: Vec<(u64, u64)> = Vec::with_capacity(left_count);
    for mask in 0..left_count {
        let mut sum = 0u64;
        for i in 0..m {
            if (mask & (1 << i)) != 0 {
                sum += left[i];
            }
        }
        left_sums.push((sum, mask as u64));
    }
    left_sums.sort_unstable_by_key(|&(s, _)| s);

    // Check duplicates in left
    for i in 1..left_sums.len() {
        if left_sums[i].0 == left_sums[i - 1].0 {
            return Err((left_sums[i - 1].1, left_sums[i].1));
        }
    }

    // Generate right sums
    let right_count = 1usize << (n - m);
    let mut right_sums: Vec<(u64, u64)> = Vec::with_capacity(right_count);
    for mask in 0..right_count {
        let mut sum = 0u64;
        for i in 0..(n - m) {
            if (mask & (1 << i)) != 0 {
                sum += right[i];
            }
        }
        right_sums.push((sum, (mask as u64) << m));
    }
    right_sums.sort_unstable_by_key(|&(s, _)| s);

    // Check duplicates in right
    for i in 1..right_sums.len() {
        if right_sums[i].0 == right_sums[i - 1].0 {
            return Err((right_sums[i - 1].1, right_sums[i].1));
        }
    }

    // Merge and check all 2^n sums
    let mut total_sums: Vec<(u64, u64)> = Vec::with_capacity(1usize << n.min(24));
    for &(sl, ml) in &left_sums {
        for &(sr, mr) in &right_sums {
            total_sums.push((sl + sr, ml | mr));
        }
    }
    total_sums.sort_unstable_by_key(|&(s, _)| s);

    for i in 1..total_sums.len() {
        if total_sums[i].0 == total_sums[i - 1].0 {
            return Err((total_sums[i - 1].1, total_sums[i].1));
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_powers_of_two() {
        // {1, 2, 4, 8} -> valid, n=4, max=8, ratio=0.5
        let res = verify_subset_sums(&[1, 2, 4, 8]);
        assert!(res.valid);
        assert_eq!(res.n, 4);
        assert_eq!(res.max_val, 8);
        assert!((res.ratio - 0.5).abs() < 1e-9);
        assert_eq!(res.collision, None);
    }

    #[test]
    fn test_valid_conway_guy_n4() {
        // {3, 5, 6, 7} -> valid, n=4, max=7, ratio=0.4375
        let res = verify_subset_sums(&[3, 5, 6, 7]);
        assert!(res.valid);
        assert_eq!(res.n, 4);
        assert_eq!(res.max_val, 7);
        assert!((res.ratio - 0.4375).abs() < 1e-9);
        assert_eq!(res.collision, None);
    }

    #[test]
    fn test_invalid_collision() {
        // {1, 2, 3} -> invalid (collision: 1+2 = 3)
        let res = verify_subset_sums(&[1, 2, 3]);
        assert!(!res.valid);
        assert_eq!(res.n, 3);
        assert!(res.collision.is_some());
    }

    #[test]
    fn test_larger_set_conway_guy_n7() {
        // Conway-Guy for n=7:
        // u = [0, 1, 2, 4, 7, 13, 24, 44]
        // S = [44-24, 44-13, 44-7, 44-4, 44-2, 44-1, 44-0] = [20, 31, 37, 40, 42, 43, 44]
        let s7 = [20, 31, 37, 40, 42, 43, 44];
        let res = verify_subset_sums(&s7);
        assert!(res.valid);
        assert_eq!(res.n, 7);
        assert_eq!(res.max_val, 44);
        assert!((res.ratio - (44.0 / 128.0)).abs() < 1e-9);
    }
}
