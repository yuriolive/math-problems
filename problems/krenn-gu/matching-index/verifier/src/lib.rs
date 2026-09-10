//! Exact ground-truth checker for GHZ graphs (Krenn-Gu conjecture).
//!
//! An input is an edge-coloured, edge-weighted multi-graph: every edge carries a colour
//! at each of its two half-edges and a weight in the cyclotomic field `Q(zeta_m)`. The
//! checker enumerates **every** perfect matching of the multi-graph exactly once, buckets
//! the matchings by the vertex colouring each one induces, and adds the weights in exact
//! arithmetic. There is no floating point anywhere in this file and no short-circuiting:
//! a violation does not stop the evaluation of the remaining colourings.
//!
//! Three states, end to end (working rule 2). Every vertex colouring is `satisfied`,
//! `violated`, or the whole run is `unknown`, the last one when an input is malformed,
//! a limit is hit, or an integer overflows. A colouring that is not in the matching map
//! has been *evaluated*: it has zero perfect matchings, hence weight exactly zero,
//! because the enumeration is over all matchings of the graph.
//!
//! Arithmetic. Weights live in `Q[z]/(z^m - 1)`; multiplication is cyclic convolution.
//! Zero- and one-testing reduce modulo the cyclotomic polynomial `Phi_m`, which is the
//! minimal polynomial of `zeta_m`, so `f(zeta_m) = 0` iff `Phi_m | f`. Coefficients are
//! `i128` rationals with checked arithmetic: an overflow is reported as `unknown`, never
//! as a zero.

use serde::Deserialize;
use std::collections::BTreeMap;

pub const MAX_N: usize = 16;
pub const MAX_COLOURS: usize = 16;
pub const MAX_ROOT: usize = 64;
pub const DEFAULT_MATCHING_CAP: u64 = 20_000_000;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Fault {
    Overflow,
    Input(String),
    LimitExceeded(String),
}

impl std::fmt::Display for Fault {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Fault::Overflow => write!(f, "integer overflow in exact arithmetic"),
            Fault::Input(s) => write!(f, "invalid input: {s}"),
            Fault::LimitExceeded(s) => write!(f, "limit exceeded: {s}"),
        }
    }
}

type R<T> = Result<T, Fault>;

// ---------------------------------------------------------------------------
// Exact rationals over i128, checked.
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Rat {
    pub num: i128,
    pub den: i128, // always > 0, gcd(|num|, den) == 1
}

fn gcd(a: i128, b: i128) -> i128 {
    let (mut a, mut b) = (a.abs(), b.abs());
    while b != 0 {
        let t = a % b;
        a = b;
        b = t;
    }
    a
}

impl Rat {
    pub fn new(num: i128, den: i128) -> R<Rat> {
        if den == 0 {
            return Err(Fault::Input("zero denominator".into()));
        }
        let sign = if den < 0 { -1 } else { 1 };
        let g = gcd(num, den).max(1);
        Ok(Rat { num: sign * (num / g), den: (den / g).abs() })
    }
    pub fn int(n: i128) -> Rat {
        Rat { num: n, den: 1 }
    }
    pub fn zero() -> Rat {
        Rat { num: 0, den: 1 }
    }
    pub fn one() -> Rat {
        Rat { num: 1, den: 1 }
    }
    pub fn is_zero(&self) -> bool {
        self.num == 0
    }
    pub fn add(self, o: Rat) -> R<Rat> {
        let g = gcd(self.den, o.den).max(1);
        let lcm = self
            .den
            .checked_div(g)
            .and_then(|q| q.checked_mul(o.den))
            .ok_or(Fault::Overflow)?;
        let a = self
            .num
            .checked_mul(lcm / self.den)
            .ok_or(Fault::Overflow)?;
        let b = o.num.checked_mul(lcm / o.den).ok_or(Fault::Overflow)?;
        Rat::new(a.checked_add(b).ok_or(Fault::Overflow)?, lcm)
    }
    pub fn sub(self, o: Rat) -> R<Rat> {
        self.add(Rat { num: -o.num, den: o.den })
    }
    pub fn mul(self, o: Rat) -> R<Rat> {
        let g1 = gcd(self.num, o.den).max(1);
        let g2 = gcd(o.num, self.den).max(1);
        let n = (self.num / g1)
            .checked_mul(o.num / g2)
            .ok_or(Fault::Overflow)?;
        let d = (self.den / g2)
            .checked_mul(o.den / g1)
            .ok_or(Fault::Overflow)?;
        Rat::new(n, d)
    }
}

// ---------------------------------------------------------------------------
// Cyclotomic integers/rationals: Q[z]/(z^m - 1), tested modulo Phi_m.
// ---------------------------------------------------------------------------

/// Coefficients of the m-th cyclotomic polynomial, ascending, monic, degree phi(m).
pub fn cyclotomic(m: usize) -> R<Vec<i128>> {
    if m == 0 || m > MAX_ROOT {
        return Err(Fault::Input(format!("root_of_unity {m} outside 1..={MAX_ROOT}")));
    }
    // x^m - 1 = prod_{d | m} Phi_d, so Phi_m is that quotient. Exact integer division.
    let mut num = vec![0i128; m + 1];
    num[0] = -1;
    num[m] = 1;
    for d in 1..m {
        if m % d == 0 {
            let phi_d = cyclotomic(d)?;
            num = poly_div_exact(&num, &phi_d)?;
        }
    }
    Ok(num)
}

fn poly_div_exact(a: &[i128], b: &[i128]) -> R<Vec<i128>> {
    let bd = b.len() - 1;
    if b[bd] != 1 {
        return Err(Fault::Input("non-monic divisor".into()));
    }
    let mut rem = a.to_vec();
    let mut quo = vec![0i128; a.len().saturating_sub(bd)];
    for i in (bd..rem.len()).rev() {
        let lead = rem[i];
        if lead == 0 {
            continue;
        }
        quo[i - bd] = lead;
        for j in 0..=bd {
            rem[i - bd + j] = rem[i - bd + j]
                .checked_sub(lead.checked_mul(b[j]).ok_or(Fault::Overflow)?)
                .ok_or(Fault::Overflow)?;
        }
    }
    if rem.iter().any(|&c| c != 0) {
        return Err(Fault::Input("inexact polynomial division".into()));
    }
    Ok(quo)
}

/// An element of Q[z]/(z^m - 1). `m == 1` is the rational field.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Cyc {
    pub m: usize,
    pub c: Vec<Rat>,
}

impl Cyc {
    pub fn zero(m: usize) -> Cyc {
        Cyc { m, c: vec![Rat::zero(); m] }
    }
    pub fn one(m: usize) -> Cyc {
        let mut c = vec![Rat::zero(); m];
        c[0] = Rat::one();
        Cyc { m, c }
    }
    pub fn add(&self, o: &Cyc) -> R<Cyc> {
        let mut c = Vec::with_capacity(self.m);
        for i in 0..self.m {
            c.push(self.c[i].add(o.c[i])?);
        }
        Ok(Cyc { m: self.m, c })
    }
    pub fn mul(&self, o: &Cyc) -> R<Cyc> {
        let m = self.m;
        let mut c = vec![Rat::zero(); m];
        for i in 0..m {
            if self.c[i].is_zero() {
                continue;
            }
            for j in 0..m {
                if o.c[j].is_zero() {
                    continue;
                }
                let k = (i + j) % m;
                c[k] = c[k].add(self.c[i].mul(o.c[j])?)?;
            }
        }
        Ok(Cyc { m, c })
    }
    /// Remainder modulo Phi_m: the canonical form of the complex number f(zeta_m).
    pub fn reduced(&self, phi: &[i128]) -> R<Vec<Rat>> {
        let k = phi.len() - 1;
        let mut r = self.c.clone();
        for i in (k..r.len()).rev() {
            let lead = r[i];
            if lead.is_zero() {
                continue;
            }
            for j in 0..=k {
                let t = lead.mul(Rat::int(phi[j]))?;
                r[i - k + j] = r[i - k + j].sub(t)?;
            }
        }
        r.truncate(k);
        Ok(r)
    }
    pub fn is_zero_at_root(&self, phi: &[i128]) -> R<bool> {
        Ok(self.reduced(phi)?.iter().all(|c| c.is_zero()))
    }
    pub fn is_one_at_root(&self, phi: &[i128]) -> R<bool> {
        let mut d = self.clone();
        d.c[0] = d.c[0].sub(Rat::one())?;
        d.is_zero_at_root(phi)
    }
}

// ---------------------------------------------------------------------------
// The coloured, weighted multi-graph.
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct Edge {
    pub u: usize,
    pub v: usize,
    /// colour of the half-edge at `u`
    pub cu: usize,
    /// colour of the half-edge at `v`
    pub cv: usize,
    pub w: Cyc,
}

#[derive(Debug, Clone)]
pub struct Instance {
    pub name: String,
    pub n: usize,
    pub colours: usize,
    pub root: usize,
    pub edges: Vec<Edge>,
}

impl Instance {
    /// Validates the contract the rest of the checker relies on. Rejecting is the honest
    /// answer to a malformed instance; silently normalising one is how a checker starts
    /// lying about what it checked.
    pub fn validate(&self) -> R<Vec<i128>> {
        if self.n < 2 || self.n > MAX_N {
            return Err(Fault::LimitExceeded(format!(
                "n = {} outside the checker's range 2..={MAX_N}",
                self.n
            )));
        }
        if self.n % 2 != 0 {
            return Err(Fault::Input("n must be even: no perfect matching otherwise".into()));
        }
        if self.colours == 0 || self.colours > MAX_COLOURS {
            return Err(Fault::Input(format!(
                "colours = {} outside 1..={MAX_COLOURS}",
                self.colours
            )));
        }
        let phi = cyclotomic(self.root)?;
        let mut seen = std::collections::HashSet::new();
        for e in &self.edges {
            if e.u >= self.n || e.v >= self.n {
                return Err(Fault::Input(format!("edge endpoint out of range: {}-{}", e.u, e.v)));
            }
            if e.u == e.v {
                return Err(Fault::Input("self-loops are not part of the model".into()));
            }
            if e.cu >= self.colours || e.cv >= self.colours {
                return Err(Fault::Input(format!("colour out of range on edge {}-{}", e.u, e.v)));
            }
            if e.w.is_zero_at_root(&phi)? {
                return Err(Fault::Input(format!(
                    "edge {}-{} has weight zero; a zero-weight edge is an absent edge, so \
                     delete it rather than declaring it",
                    e.u, e.v
                )));
            }
            // Reduced multi-graph (Chandran-Gajjala-Illickan section 1.1): at most one
            // edge per (pair, ordered colour pair). Parallel slots must be merged by
            // adding their weights, which changes the instance, so the checker refuses.
            if !seen.insert((e.u, e.v, e.cu, e.cv)) {
                return Err(Fault::Input(format!(
                    "duplicate slot ({},{},{},{}): merge parallel edges by adding weights",
                    e.u, e.v, e.cu, e.cv
                )));
            }
        }
        Ok(phi)
    }
}

// ---------------------------------------------------------------------------
// Report.
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Kind {
    /// A non-monochromatic colouring whose weight is not zero.
    NonMonoNonZero,
    /// A feasible monochromatic colouring whose weight is not one.
    MonoNotOne,
}

#[derive(Debug, Clone)]
pub struct Violation {
    pub colouring: Vec<usize>,
    pub matchings: u64,
    pub kind: Kind,
    pub weight: Vec<Rat>,
}

/// One feasible vertex colouring: how many perfect matchings induce it, and their exact
/// summed weight in canonical form (reduced modulo `Phi_m`).
#[derive(Debug, Clone)]
pub struct ColourWeight {
    pub colouring: Vec<usize>,
    pub matchings: u64,
    pub monochromatic: bool,
    pub weight: Vec<Rat>,
}

#[derive(Debug, Clone)]
pub struct Report {
    pub n: usize,
    pub colours: usize,
    pub root: usize,
    /// Total number of perfect matchings of the coloured multi-graph. Exact: the
    /// enumeration either finished or the run is `unknown`.
    pub matchings: u64,
    pub feasible: usize,
    pub feasible_mono: Vec<usize>,
    pub dimension: usize,
    pub ghz: bool,
    pub counterexample: bool,
    pub violations: Vec<Violation>,
    /// Every feasible colouring, in colouring order. A colouring absent from this list has
    /// been evaluated and has zero matchings, hence weight exactly zero.
    pub colourings: Vec<ColourWeight>,
    /// Non-monochromatic colourings with exactly one perfect matching. Each one is fatal
    /// for *every* weighting of this support: a single non-zero product cannot cancel.
    pub unique_pm_nonmono: usize,
    /// Non-monochromatic colourings with at least two matchings, the colourings where
    /// destructive interference has to do the work.
    pub cancelling_nonmono: usize,
    /// ...of which actually cancel under the weights supplied.
    pub cancelling_nonmono_zero: usize,
    pub skeleton_edges: usize,
    pub degrees: Vec<usize>,
    pub connectivity: usize,
    pub matching_covered: bool,
    pub mono_matchings: Vec<u64>,
}

struct Walker<'a> {
    inst: &'a Instance,
    adj: Vec<Vec<usize>>,
    cap: u64,
    count: u64,
    colour: Vec<usize>,
    used_edges: Vec<bool>,
    buckets: BTreeMap<Vec<usize>, (u64, Cyc)>,
}

impl<'a> Walker<'a> {
    fn walk(&mut self, matched: u32, weight: Cyc, chosen: &mut Vec<usize>) -> R<()> {
        let n = self.inst.n;
        let u = match (0..n).find(|&v| matched & (1 << v) == 0) {
            None => {
                self.count += 1;
                if self.count > self.cap {
                    return Err(Fault::LimitExceeded(format!(
                        "more than {} perfect matchings; raise --max-matchings if this is \
                         intended",
                        self.cap
                    )));
                }
                for &ei in chosen.iter() {
                    self.used_edges[ei] = true;
                }
                let key = self.colour.clone();
                match self.buckets.get_mut(&key) {
                    Some(slot) => {
                        slot.0 += 1;
                        slot.1 = slot.1.add(&weight)?;
                    }
                    None => {
                        self.buckets.insert(key, (1, weight));
                    }
                }
                return Ok(());
            }
            Some(u) => u,
        };
        for idx in 0..self.adj[u].len() {
            let ei = self.adj[u][idx];
            let e = &self.inst.edges[ei];
            let (other, cu, cother) = if e.u == u { (e.v, e.cu, e.cv) } else { (e.u, e.cv, e.cu) };
            if matched & (1 << other) != 0 {
                continue;
            }
            self.colour[u] = cu;
            self.colour[other] = cother;
            chosen.push(ei);
            let w = weight.mul(&e.w)?;
            self.walk(matched | (1 << u) | (1 << other), w, chosen)?;
            chosen.pop();
        }
        Ok(())
    }
}

fn connectivity(n: usize, adj: &[Vec<usize>]) -> usize {
    // Brute force over vertex cuts; n <= MAX_N so 2^n subsets is affordable and exact.
    let complete = (0..n).all(|v| adj[v].len() == n - 1);
    if complete {
        return n - 1;
    }
    for k in 0..n {
        for mask in 0u32..(1 << n) {
            if (mask.count_ones() as usize) != k {
                continue;
            }
            let remaining: Vec<usize> = (0..n).filter(|&v| mask & (1 << v) == 0).collect();
            if remaining.len() < 2 {
                continue;
            }
            let mut seen = vec![false; n];
            let mut stack = vec![remaining[0]];
            seen[remaining[0]] = true;
            let mut reached = 1;
            while let Some(v) = stack.pop() {
                for &w in &adj[v] {
                    if mask & (1 << w) == 0 && !seen[w] {
                        seen[w] = true;
                        reached += 1;
                        stack.push(w);
                    }
                }
            }
            if reached < remaining.len() {
                return k;
            }
        }
    }
    n - 1
}

pub fn check(inst: &Instance, cap: u64) -> R<Report> {
    let phi = inst.validate()?;
    let n = inst.n;

    let mut incident = vec![Vec::new(); n];
    for (i, e) in inst.edges.iter().enumerate() {
        incident[e.u].push(i);
        incident[e.v].push(i);
    }

    let mut walker = Walker {
        inst,
        adj: incident,
        cap,
        count: 0,
        colour: vec![0; n],
        used_edges: vec![false; inst.edges.len()],
        buckets: BTreeMap::new(),
    };
    walker.walk(0, Cyc::one(inst.root), &mut Vec::new())?;

    let mut violations = Vec::new();
    let mut colourings = Vec::new();
    let mut feasible_mono = Vec::new();
    let mut unique_pm_nonmono = 0usize;
    let mut cancelling_nonmono = 0usize;
    let mut cancelling_nonmono_zero = 0usize;
    let mut all_mono_one = true;
    let mut all_nonmono_zero = true;
    let mut mono_matchings = vec![0u64; inst.colours];

    // Every bucket is inspected, every time. No early exit: the report is the ground
    // truth, so it states the whole picture rather than the first thing that went wrong.
    for (colouring, (count, weight)) in walker.buckets.iter() {
        let mono = colouring.iter().all(|&c| c == colouring[0]);
        colourings.push(ColourWeight {
            colouring: colouring.clone(),
            matchings: *count,
            monochromatic: mono,
            weight: weight.reduced(&phi)?,
        });
        if mono {
            let i = colouring[0];
            mono_matchings[i] = *count;
            if weight.is_one_at_root(&phi)? {
                feasible_mono.push(i);
            } else {
                all_mono_one = false;
                violations.push(Violation {
                    colouring: colouring.clone(),
                    matchings: *count,
                    kind: Kind::MonoNotOne,
                    weight: weight.reduced(&phi)?,
                });
            }
        } else {
            if *count == 1 {
                unique_pm_nonmono += 1;
            } else {
                cancelling_nonmono += 1;
            }
            if weight.is_zero_at_root(&phi)? {
                if *count > 1 {
                    cancelling_nonmono_zero += 1;
                }
            } else {
                all_nonmono_zero = false;
                violations.push(Violation {
                    colouring: colouring.clone(),
                    matchings: *count,
                    kind: Kind::NonMonoNonZero,
                    weight: weight.reduced(&phi)?,
                });
            }
        }
    }

    let ghz = all_mono_one && all_nonmono_zero && !feasible_mono.is_empty();
    let dimension = if ghz { feasible_mono.len() } else { 0 };

    let mut skeleton: std::collections::HashSet<(usize, usize)> = std::collections::HashSet::new();
    for e in &inst.edges {
        skeleton.insert((e.u.min(e.v), e.u.max(e.v)));
    }
    let mut sadj = vec![Vec::new(); n];
    for &(u, v) in &skeleton {
        sadj[u].push(v);
        sadj[v].push(u);
    }
    let degrees: Vec<usize> = sadj.iter().map(|a| a.len()).collect();

    Ok(Report {
        n,
        colours: inst.colours,
        root: inst.root,
        matchings: walker.count,
        feasible: walker.buckets.len(),
        dimension,
        ghz,
        counterexample: ghz && n > 4 && dimension >= 3,
        feasible_mono,
        violations,
        colourings,
        unique_pm_nonmono,
        cancelling_nonmono,
        cancelling_nonmono_zero,
        skeleton_edges: skeleton.len(),
        degrees,
        connectivity: connectivity(n, &sadj),
        matching_covered: walker.used_edges.iter().all(|&b| b),
        mono_matchings,
    })
}

// ---------------------------------------------------------------------------
// Instance JSON.
// ---------------------------------------------------------------------------

#[derive(Deserialize)]
struct EdgeIn {
    u: usize,
    v: usize,
    cu: usize,
    cv: usize,
    /// Coefficients of the weight over the basis 1, z, z^2, ... as [numerator, denominator]
    /// pairs, where z = exp(2 pi i / root_of_unity). Omitted means the weight 1.
    #[serde(default)]
    w: Option<Vec<[i128; 2]>>,
}

#[derive(Deserialize)]
struct InstanceIn {
    #[serde(default)]
    name: Option<String>,
    n: usize,
    colours: usize,
    #[serde(default)]
    root_of_unity: Option<usize>,
    edges: Vec<EdgeIn>,
}

fn weight(root: usize, coeffs: &Option<Vec<[i128; 2]>>) -> R<Cyc> {
    let Some(coeffs) = coeffs else { return Ok(Cyc::one(root)) };
    if coeffs.len() > root {
        return Err(Fault::Input(format!(
            "weight has {} coefficients but root_of_unity is {root}",
            coeffs.len()
        )));
    }
    let mut c = vec![Rat::zero(); root];
    for (i, nd) in coeffs.iter().enumerate() {
        c[i] = Rat::new(nd[0], nd[1])?;
    }
    Ok(Cyc { m: root, c })
}

/// Reads one instance. Validation of the graph itself happens in `check`.
pub fn parse(text: &str) -> R<Instance> {
    let parsed: InstanceIn = serde_json::from_str(text)
        .map_err(|e| Fault::Input(format!("malformed instance JSON: {e}")))?;
    let root = parsed.root_of_unity.unwrap_or(1);
    if root == 0 || root > MAX_ROOT {
        return Err(Fault::Input(format!("root_of_unity {root} outside 1..={MAX_ROOT}")));
    }
    let mut edges = Vec::with_capacity(parsed.edges.len());
    for e in &parsed.edges {
        let w = weight(root, &e.w)?;
        // Canonical orientation u < v, carrying the half-edge colours with the endpoints.
        let (u, v, cu, cv) =
            if e.u <= e.v { (e.u, e.v, e.cu, e.cv) } else { (e.v, e.u, e.cv, e.cu) };
        edges.push(Edge { u, v, cu, cv, w });
    }
    Ok(Instance {
        name: parsed.name.unwrap_or_else(|| "unnamed".into()),
        n: parsed.n,
        colours: parsed.colours,
        root,
        edges,
    })
}
