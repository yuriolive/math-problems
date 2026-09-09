# Proximity koala-irs12

> **Statement.** Fix the interleaved Reed–Solomon profile `koalaIRS12`: the field is
> `KoalaBear.Ext6` (the sextic extension of the KoalaBear prime $2^{31}-2^{24}+1$), the
> evaluation domain is the smooth NTT domain of size $2^{18}$, the total dimension is
> $2^{20}$, the interleaving is $8$ (so the base dimension is $2^{17}$ and the rate is
> $1/2$), and the number of spot-check repetitions is $t = 128$. Let
> $\gamma(\delta)$ be ArkLib's *certified* combination-round error of the executable IRS
> straight-line extractor at relative radius $\delta$ — the MCA-plus-list term of ABF26
> Lemma 6.10, which upper-bounds the Definition 6.11 winning-set soundness. Exhibit a
> radius $\delta = P/Q$ with
> $$\delta \in \left(0,\ \tfrac{131073}{262144}\right), \qquad \gamma(\delta) \le 2^{-128},$$
> and score it by the induced spot-check term: the score in centibits is the largest $B$
> with $(1-\delta)^{128} \le 2^{-B/100}$. Larger $B$ is stronger. Every part of this must
> be a Lean 4 proof of the pinned theorem type, checked by the Lean kernel with an axiom
> closure limited to `propext`, `Classical.choice` and `Quot.sound`.

> **Status.** Open, and live as a public leaderboard. The Ethereum Foundation Formal
> Verification team launched [better.codes](https://better.codes/) on 20 August 2026
> ([announcement](https://blog.ethereum.org/en/2026/08/20/better-codes-challenge)). As of
> 9 September 2026 the certified lower bound is **68.04 bits** and the certified attack
> (unsafe) side is **116.13 bits**, against a fixed **128.00** bit target.

## 0. Intake

Answered before any code was written. Rule 6 and Rule 12 both apply here: read the
literature and check the instrument's reach before spending compute.

### 1. Can a compiled ground-truth checker be written in about a day?

> It defines what a solution *is*. Without it a search produces numbers nobody
> should trust, and every published figure here that turned out to be false came
> from trusting a search kernel's own counters.

**Answer.** Yes — and better than yes: *the checker is not ours to write.* The challenge
ships its own ground truth, and it is stricter than anything this repository has built.
`benchmark.sh` runs [Comparator](https://github.com/leanprover/comparator), which checks
that the submitted theorem's exported type is character-identical to the pinned
`ProtocolClaim B P Q`, then re-checks every submission module with the Lean kernel inside
a read-only sandbox, then rejects the submission if its axiom closure contains anything
outside `propext`, `Classical.choice`, `Quot.sound`. That whitelist is the same one
[`tools/lean/audit.py`](../../../tools/lean/audit.py) already enforces here.

Rule 1 therefore holds by construction — ground truth is a separate program, written by
someone else, run before the score exists. What we owe is the *day* of work to reproduce
its verdict locally, which is exactly the gate in §3.

### 2. Does the objective have a gradient — does a small perturbation move the score?

> Circle packing rewards the twelfth decimal place, so evolutionary search climbs.
> A lexicographic integer profile barely moves under an edge swap, so it does not.
> This single property predicts whether search or proof is the right instrument.

**Answer.** Yes, and it is smooth — the best gradient answer of any candidate screened in
this repository. The score is a closed form in the single real parameter $\delta$:

$$B(\delta) \;=\; \left\lfloor -12800 \cdot \log_2(1-\delta) \right\rfloor \text{ centibits},$$

strictly increasing and differentiable on the whole admissible interval. There is no
plateau, no max-over-pairs, no integer step function — the three shapes that disqualified
most of [`CANDIDATES.md`](../../CANDIDATES.md). Any certified increase in $\delta$, however
small, raises the score, and the leaderboard promotes gains as small as **+0.01 bits**.

The gradient is in $\delta$, not in the proof. The work is proving
$\gamma(\delta) \le 2^{-128}$ at a larger $\delta$; the *reward* for succeeding is
continuous rather than all-or-nothing, which is what makes incremental effort payable.

### 3. Is there a published open gap strictly easier than the headline conjecture?

> There usually is, and it is usually far more tractable. Keep it one flag away
> from the main objective, and never conflate a hit on it with the harder claim.

**Answer.** Yes — and here the easier gap *is* the target, which is unusual. The headline
is the Proximity Prize grand challenges on Reed–Solomon proximity gaps and correlated
agreement (PPL 097 and PPL 162, share of a \$1,000,000 pool), and those require acceptance
at a refereed venue. `koalaIRS12` is the self-contained sub-instance carved out of the same
paper, at one fixed parameter point, gated by a machine instead of a referee.

The flag between them: a score on this leaderboard is **a certified bound at one profile**,
not a resolution of the proximity-gaps conjecture. Never write the second sentence when the
first is what happened.

### 4. Is the reachable instance size inside the checker's hard limit?

> State the limit as a number and the target range as a number, in the same units,
> and compare them here. Erdős #64's verifier stops at 64 vertices while the open
> gap runs to 78; writing both down would have caught it.

**Answer.** Yes, and every number is in bits:

| Quantity | Value |
| :--- | ---: |
| Certified soundness (lower), 9 Sep 2026 | 68.04 bits |
| Certified attack (upper), 9 Sep 2026 | 116.13 bits |
| Open interval width | 48.09 bits |
| Fixed target | 128.00 bits |
| Ceiling as $\delta \to 131073/262144$ | 128.00 bits |
| Literature baselines used for the progress metric | 64.00 and 116.49 bits |

The ceiling and the target coincide, which is the reassuring part: reaching 128 bits means
certifying the full minimum-relative-distance radius, and no reparametrisation is being
asked for that the profile cannot express. The checker's hard limit is not an instance
size but a *proof* size — the promoted 68.04-bit certificate is 8.75 MB of generated Lean
across three files, and the binding cost is elaboration time, measured in §3.

**Verdict.** The four technical questions pass. **The economic question fails**, and it is
the one that decides whether to spend time here.

The [program terms](https://better.codes/program-terms) were read on 9 September 2026.
There is no payout figure because there is no payout commitment:

* The Program is "an experimental and **discretionary** research rewards program", operated
  and funded by Stiftung Ethereum.
* The EF has "sole and final discretion" over "whether any Participant receives an award"
  and "the amount and allocation of any award".
* "Passing tests, producing an improved benchmark score, being promoted to a repository, or
  appearing on a leaderboard **does not create an entitlement to payment**."
* "Published scores, tables, formulas, rankings, reward estimates, and pro rata calculations
  guide the evaluation process but **are not guarantees**."
* "**No award exists or becomes payable unless and until** an authorised representative of
  the EF confirms the award and its amount in writing (an 'Award Notice')."
* The EF may "pause, suspend, or cancel the Program" and such action "may apply to pending
  submissions".
* Aggregate liability is capped at "the greater of `US$100` and the amount of any award
  expressly confirmed".
* "The Participant is responsible for all costs and risks associated with preparing and
  submitting work."
* Disputes go to single-arbitrator arbitration in Zurich under Swiss law — which costs more
  than any plausible award.

So the leaderboard is not a prize with a price. It is a discretionary grant program with a
public scoreboard attached, and the 72 promoted lower-track submissions are unpaid until and
unless the EF individually decides otherwise in writing. That is a legitimate thing for a
foundation to run; it is simply not something whose expected value can be computed, and
Rule 10 does not permit pretending otherwise.

Note also that the site, CLI, verification workflow and leaderboard are operated by **Eigen
Labs**, not the EF, and Eigen Labs "has no authority to bind the EF, determine or promise an
award". The thing that scores the work and the thing that might pay for it are different
organisations.

**Therefore: keep the scaffold, do not fund a campaign.** The problem is real, the gate is
worth having, and the two structural questions in [`ROADMAP.md`](./ROADMAP.md) — the
`winningSetDensity` monotonicity theorem, and where the `lambda_le` slack sits — are worth
answering on their merits. But this is a capability and reputation bet, not a paid one, and
it must not be entered as though money were on the table.

## 1. Known results

| Result | Value | Source |
| :--- | :--- | :--- |
| Problem source | ABF26, open problems in list decoding and correlated agreement | Arnon, Boneh, Fenzi, [eprint 2026/680](https://eprint.iacr.org/2026/680) |
| Formalization | ArkLib, rev `e65197892890b8fd9b0dc05b8980273cf1d595cc` | [Verified-zkEVM/ArkLib](https://github.com/Verified-zkEVM/ArkLib) |
| Challenge harness | `irs-reduction-threshold-v13`, tracks `…-lower` / `…-upper` | [proximity-prize/proximity-prize](https://github.com/proximity-prize/proximity-prize) |
| Certified lower bound | 68.04 bits at $\delta = 10341375/33554432 \approx 0.308199$ | [better.codes](https://better.codes/) leaderboard, 6 Sep 2026 |
| Certified upper bound | 116.13 bits at unsafe index 122369 | [better.codes](https://better.codes/) leaderboard |
| Progress metric | $1 - (\text{Attack} - \text{Soundness})/(116.49 - 64.00) = 8.38\%$ | better.codes |
| Grand challenge | share of \$1,000,000 pool, peer review required | [proximityprize.org](https://proximityprize.org/), PPL 097 / PPL 162 |
| Launch | 20 August 2026 | [EF blog](https://blog.ethereum.org/en/2026/08/20/better-codes-challenge) |

The profile constants are read from the pinned Lean source, not from prose:
`ProximityPrize/Benchmark/IRSProfile.lean` gives `totalDimension = 2^20`,
`interleaving = 8`, `baseDimension = 2^17`, `domainSize = 2^18`, `repetitions = 128`,
`minRelativeDistance = 131073/262144`.

## 2. What would count as progress

In descending order of value:

1. **A promoted submission on the `lower` track** — any $B > 6804$ centibits, accepted by
   the independent verifier. This is the only outcome that moves the public number.
2. **A promoted submission on the `upper` track** — any $B < 11613$ centibits, narrowing
   the interval from above.
3. **A reusable lemma upstreamed** to the challenge repository, whether or not it raised a
   bound. The challenge explicitly upstreams promoted lemmas and impossibility results.
4. **A measured negative** — a radius at which the certificate provably cannot close, with
   the obstruction named. Under Rule 11 this is worth writing down; under the challenge's
   own rules it is worth publishing.

Not progress: a numeric bound produced by anything other than the pinned theorem type; a
local run that used `BENCHMARK_INSECURE_LOCAL=1`, which is unranked by construction.

## 3. Measured state

Measured on a 32-core / 48 GB Windows host, 9 September 2026. The Lean gate has **not**
passed yet; what is recorded here is what has actually been run.

### Scoring contract — reproduced exactly

`uv run python problems/proximity/koala-irs12/tests/test_score_contract.py`, exact rational
arithmetic throughout, 8/8 assertions passing:

| Quantity | Value | Submission claims |
| :--- | ---: | ---: |
| Lower radius | $10341375/33554432 = 0.308196992$ | — |
| Lower score | 6804 centibits | 6804 ✓ |
| Upper radius | $122369/262144 = 0.466800690$ | — |
| Upper score | 11613 centibits | 11613 ✓ |
| Ceiling as $\delta \to$ `minRelativeDistance` | 12800 centibits | = the 128.00 bit target |
| One upper grid step | 0.13 centibits | finer than the leaderboard's 1-centibit resolution |

Both promoted leaderboard numbers are reproduced bit-exactly from the pinned Lean
definitions, so the scoring contract is understood. This checks *our reading of the score*,
not the theorem — the theorem is the Lean kernel's job.

One assumption of mine was falsified in the process: I expected the upper track's
`gridPt i = i / 2^18` discretisation to be too coarse for small moves. Measured, one step
is worth 0.13 centibits and cannot move the reported score at all, so granularity is not
what stalled the attack track. Recorded rather than quietly corrected, per Rule 9.

### Lean gate — blocked on Windows; the harness requires Linux

**Result: the gate cannot run on this host.** Three walls, in order, none mathematical:

1. **Dependency build memory.** See below — worked around.
2. **Console encoding.** `scripts/check-submission-imports.sh` pipes a Python program that
   prints submission source containing `ℕ`; Python on Windows defaults to cp1252 and dies
   with `UnicodeEncodeError: 'charmap' codec can't encode character 'ℕ'`. Worked
   around legitimately with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` — this changes only how
   the harness's own output is encoded, not what it checks.
3. **The sandbox shim is a shell script.** Comparator execs `COMPARATOR_LANDRUN` as a
   process. On the non-Linux path that is
   `.benchmark-tools/comparator/scripts/fake-landrun.sh`, a `#!/usr/bin/env bash` script,
   and Windows `CreateProcess` cannot run it:

   ```
   WARNING: using Comparator's fake sandbox; this local run is not trusted
   Building ProximityPrize.Benchmark.Challenge
   uncaught exception: %1 is not a valid Win32 application. (error code: 193)
   ```

   Wall 3 has no legitimate workaround. Replacing the shim with a `.bat` would be editing
   the checker to make the checker pass, which is the one thing that must never be done
   here. Rule 1 is not negotiable when the ground-truth program is the thing that is
   inconvenient.

**The measured entry requirement is therefore a Linux host**, not merely a Lean toolchain.
WSL2 Ubuntu on this machine has `git`, `curl`, `python3`, `systemd-run` and `gcc`; `elan`
is installed by `setup.sh` itself, and `go` is needed only for the *ranked* `landrun` path.
Cost of that route: a full rebuild of all 3906 jobs (the Windows `.lake` tree cannot be
reused), roughly 10–12 GB of disk and on the order of an hour, before the gate itself
starts. WSL2 here reports 22 GB of RAM against the host's 48, so the memory wall below
applies at least as strongly.

### Dependency build — failed on memory, not mathematics

`./setup.sh` reached 3883 of 3906 build jobs and then failed:

```
✖ [3759/3906] Building VCVio.ProgramLogic.Tactics.Common.Core (37s)
libc++abi: terminating due to uncaught exception of type std::bad_alloc: std::bad_alloc
error: Lean exited with code 3221226505
```

Lake defaults to one job per core, so 32 `lean.exe` processes were resident and a single
heavy tactic file in a *transitive dependency* (VCVio, pulled in by ArkLib) exhausted the
allocator. Nothing about `koalaIRS12` was reached.

Lake 5.0.0 has no `-j` / `--jobs` flag to bound this — it was removed from the CLI, so the
only levers are the `LAKE_JOBS` / `LEAN_NUM_THREADS` environment variables and simply
re-running once most of the tree is built and fewer jobs are live at a time.

The number worth keeping: **the binding constraint on entry is dependency build memory, not
the challenge**. Mathlib's cache supplies 6.3 GB of prebuilt oleans, but ArkLib, CompPoly,
VCVio, Cslib and PolyFun have no cache and compile from source — 3906 jobs.

### Where this leaves the gate

Not passed, and not failed on its merits — it never reached the mathematics. The scoring
contract is understood and reproduced exactly; the dependency tree builds; the two
protected contracts audit clean (`ok — protected IRS path uses only
propext/Classical.choice/Quot.sound`). What is missing is a Linux host to run Comparator on.

Nothing here may be reported as a score in any case: a local run uses
`BENCHMARK_INSECURE_LOCAL=1`, which disables the sandbox and is unranked by construction.

## 4. Layout

```
problems/proximity/koala-irs12/
├── README.md               this file
├── ROADMAP.md              the gate, what is worth trying, and what is closed
├── upstream/               the challenge repository — NOT redistributed, see below
└── tests/                  reproduction harness for the gate
```

There is no `verifier/` here on purpose: the ground-truth checker is Comparator plus the
Lean kernel, shipped by the challenge, and writing a second one would create exactly the
two-sources-of-truth problem Rule 1 exists to prevent.

`upstream/` is a clone of a third-party repository and is gitignored. Fetch it with:

```bash
git clone https://github.com/proximity-prize/proximity-prize.git \
  problems/proximity/koala-irs12/upstream
```

It is Apache-2.0 licensed, the same as this repository, but it is a separate work with
separate authorship; nothing in it is this repository's contribution.
