# Proximity koala-irs12 — roadmap

## The gate

**Reproduce the promoted 68.04-bit certificate locally, before writing a line of proof
search.** Rule 6 in its sharpest form: if the harness's own verdict cannot be reproduced,
nothing produced against it can be trusted, and the failure is cheap to discover now and
expensive to discover after a week of elaboration.

```bash
cd problems/proximity/koala-irs12/upstream
./setup.sh
BENCHMARK_INSECURE_LOCAL=1 ./benchmark.sh lower
```

Pass condition: the run reports `6804` centibits at radius `10341375/33554432`, having
compiled `ProximityPrize/SubmissionLower/Solution.lean` through Comparator and the Lean
kernel with no axiom outside `propext`, `Classical.choice`, `Quot.sound`.

Fail condition, and what it means:

| Failure | Reading |
| :--- | :--- |
| Comparator rejects the type | the pinned statement moved; re-clone at the current challenge version |
| Axiom closure is dirty | the toolchain or ArkLib rev is wrong; do not proceed |
| Score is not `6804` | the scoring contract is misread; stop and re-derive $B(\delta)$ |
| Elaboration does not finish | the machine is the binding constraint, not the mathematics — measure it and record the number before deciding anything |

`BENCHMARK_INSECURE_LOCAL=1` uses Comparator's fake sandbox and is **unranked by
construction**. It is a reproduction check, never evidence. A ranked score exists only when
the challenge's independent verifier accepts an exact commit. Rule 5: the Lean kernel layer
is verified, the local sandbox layer is trusted and in this configuration deliberately
disabled.

## Live directions

### Raise $\delta$ on the `lower` track

What it would show: a larger certified radius at which
$\gamma(\delta) \le 2^{-128}$, hence a score above 6804 centibits.

What it needs: the slack in ArkLib's `certifiedGammaError` at the current radius, measured
rather than guessed. The score is $B(\delta) = \lfloor -12800\log_2(1-\delta)\rfloor$, so
the whole question is how far $\delta$ can move before the certified error crosses
$2^{-128}$.

How it would be verified: the gate command above, then the independent verifier.

### Lower $B$ on the `upper` track

Looks like the open side — 11 promoted submissions from 6 solvers against 72 from 22 — but
the two tracks are **not symmetric**, and the asymmetry is in the pinned types, not in how
much attention each has had. Every attack submission on the leaderboard is dated 20 August
2026 between 16:22 and 19:55; the track has not moved in the three weeks since.

Read the two obligations side by side:

| Track | Obligation | Shape |
| :--- | :--- | :--- |
| lower | `certifiedGammaError δ ≤ reductionTarget` | one radius |
| upper | `∀ δ ∈ Set.Ico δ* minRelativeDistance, epsilonStar < winningSetDensity encoder δ` | every radius in a half-open interval |

Three consequences:

1. **A point versus a continuum.** The lower certificate discharges a numeric inequality at
   a single $\delta$. The upper certificate is universally quantified over an interval, and
   `TargetUpper.lean` says why in as many words: *"The whole admissible suffix is certified
   because no monotonicity theorem is assumed."*
2. **Improvement enlarges the obligation.** Lowering the score means lowering the index $i$,
   which lowers $\delta^\* = i/2^{18}$, which makes `Set.Ico δ* minRelativeDistance`
   strictly *wider*. Each gain on the attack track buys a harder next step. The soundness
   track has no such feedback — a bigger $\delta$ is still one point.
3. **It is not granularity.** The obvious guess — that `gridPt i = i/2^18` is too coarse for
   small moves — is measurably false. One grid step is worth **0.13 centibits**, finer than
   the one-centibit resolution the leaderboard reports in; a single step cannot even change
   the displayed score. Measured by
   `test_upper_grid_is_finer_than_the_leaderboard_resolution` in
   [`tests/test_score_contract.py`](./tests/test_score_contract.py).

**So the structural prize on the attack side is a monotonicity theorem for
`winningSetDensity`.** With it, `unsafeAbove` collapses from a statement about an interval
to a statement at one endpoint, and the upper track becomes as incremental as the lower one.
That is a single named lemma, it is the stated reason the obligation has its current shape,
and nobody has moved the number in three weeks. It is the most interesting thing on this
challenge and it is worth a literature pass before any grinding on the lower track.

Caveat before betting on it: a monotonicity theorem may be false, or may be exactly as hard
as the grand challenge. Establish which before committing — that is a reading task, not a
compute task.

### Measure where the certificate's cost actually sits

The promoted lower certificate is 8.75 MB of generated Lean in three files
(`Solution.lean` 4.1 MB, `LowerGeometry.lean` 2.4 MB, `LowerFoundation.lean` 2.2 MB).
Before generating anything, find out which part of that is numeric certificate and which is
structure — the ratio decides whether the instrument is a proof search or a certificate
generator with a thin Lean shell.

## Closed directions

Nothing closed by measurement yet. Three closed by the repository's rules, recorded so they
are not re-entered:

* **Writing our own verifier.** The challenge ships ground truth. A second checker here
  would create two sources of truth for the same number, which is the failure Rule 1
  exists to prevent. `verifier/` is intentionally absent.
* **Quoting a local unranked run as a result.** `BENCHMARK_INSECURE_LOCAL=1` disables the
  sandbox. Rule 4: report only what was measured, and what that mode measures is
  reproduction, not rank.
* **Describing a leaderboard score as progress on proximity gaps.** The grand challenges
  (PPL 097 / PPL 162) are a separate, refereed target. Rule 7: keep the easier target one
  flag away and never conflate a hit on it with the harder claim.

## Can the 48.09-bit gap be walked?

No. Measured, not guessed — `uv run python tools/leaderboard_rate.py` over the 62 promoted
lower-track submissions scraped on 9 September 2026:

| Quantity | Value |
| :--- | ---: |
| Total movement, 20 Aug – 6 Sep | 14.92 bits in 17 days |
| Largest single submission | **+10.45 bits** (20 Aug) |
| Everything else, combined | 4.47 bits |
| Rate over the last 7 days | 0.0343 bits/day |
| Days since the last promotion | 3 |
| Remaining to the 116.13-bit attack bound | 48.09 bits |

Extrapolating the remaining distance:

| At this rate | Time to close |
| :--- | ---: |
| all-time, including the jump | 0.2 years |
| all-time, excluding the jump | 0.5 years |
| the last 7 days | **3.2 years** |

And the returns are decaying fast — mean gain per promoted submission, in thirds:

| Period | Mean gain |
| :--- | ---: |
| first third (n=20) | 0.6280 bits |
| second third (n=20) | 0.0930 bits |
| final third (n=21) | 0.0238 bits |

A **26× decay in twenty days**, which makes the 3.2-year figure optimistic rather than
pessimistic: it assumes the current rate holds, and the trend says it will not.

**The conclusion that matters:** one submission produced 70% of all progress ever made on
this track, and the other 61 produced 4.47 bits between them. This is not a distance that
gets walked, it is a distance that gets jumped. Grinding the enumeration is a technique
that has visibly exhausted itself — anyone entering now to do more of it is buying the
0.0238-bits-per-submission tail.

That does **not** mean the challenge is not worth entering: promotion is per-submission, so
beating 6804 by +0.01 bits is both achievable and, apparently, sufficient to be credited.
It means the two things must not be confused. Closing the gap needs a second structural
step of the kind that happened once on 20 August, not more table.

## Risks

* **There is no payout, only a discretion.** Resolved on 9 September 2026 by reading
  [the program terms](https://better.codes/program-terms): promotion to the leaderboard
  "does not create an entitlement to payment", published reward estimates "are not
  guarantees", and "no award exists or becomes payable unless and until" the EF issues a
  written Award Notice. Liability is capped at the greater of `US$100` and any confirmed
  award. The full extract is in [`README.md`](./README.md) §0. This is settled, and it
  settles the economics: **do not enter this expecting to be paid.**
* **The field is crowded and fast.** 72 promoted submissions from 22 solvers in the first
  three weeks, and the recent gains are +0.01 bits each — the cheap slack is being ground
  out by many agents in parallel. First-mover advantage is already gone; what remains is
  whether a *different* technique finds a step the incremental grind cannot.
* **One large jump dominates the history.** A single submission on 20 August moved the
  bound +10.45 bits (53.13 → 63.58); everything since totals under 5 bits. That shape
  suggests the remaining progress is structural, not incremental.

## Rules

The repository's working rules apply. The two that bite first on a new problem:

* Ground truth is a separate program from the search.
* "Absent" must never mean "not evaluated".
