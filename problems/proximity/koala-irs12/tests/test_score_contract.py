"""Exact re-derivation of the koalaIRS12 scoring contract.

This does **not** check the mathematics; the Lean kernel and Comparator do that, and
writing a second checker for the theorem would violate Rule 1. What it checks is our own
reading of how a radius turns into a score — the thing that, misread, makes every later
number wrong while looking fine. `CANDIDATES.md` records that the scout's own statement of
the objective was wrong for *both* problems that survived screening, so the arithmetic is
re-derived here from the pinned Lean definitions rather than from prose.

From `ProximityPrize/Benchmark/TargetLower.lean`, a `ProtocolClaim B P Q` requires

    (1 - P/Q) ^ repetitions <= 2 ^ (-B/100)

with `repetitions = 128`. Raising both sides to the 100th power (monotone on positives)
clears the fractional exponent and leaves a comparison of exact integers:

    (Q - P) ^ 12800 * 2 ^ B <= Q ^ 12800

so the best score at a given radius is the largest `B` satisfying it. All arithmetic below
is exact; no floating point enters a pass/fail decision.
"""

from __future__ import annotations

from fractions import Fraction

# Profile constants, read from ProximityPrize/Benchmark/IRSProfile.lean.
REPETITIONS = 128
MIN_RELATIVE_DISTANCE = Fraction(131073, 262144)

# The promoted lower-track submission, read from ProximityPrize/SubmissionLower/.
PROMOTED_RADIUS = Fraction(10341375, 33554432)
PROMOTED_CENTIBITS = 6804

# The promoted upper-track submission, read from ProximityPrize/SubmissionUpper/. The
# radius is not a free rational: `TargetUpper.lean` pins it to `ProximityGap.gridPt`,
# which ArkLib defines as `k / Fintype.card ι`, and here `ι = Fin (2 ^ 18)`.
DOMAIN_SIZE = 2 ** 18
PROMOTED_UNSAFE_INDEX = 122369
PROMOTED_UPPER_CENTIBITS = 11613
PROMOTED_UNSAFE_RADIUS = Fraction(PROMOTED_UNSAFE_INDEX, DOMAIN_SIZE)


def best_centibits(radius: Fraction) -> int:
    """Largest B with (1 - radius) ** REPETITIONS <= 2 ** (-B / 100), exactly."""
    remainder = 1 - radius
    if not 0 < remainder <= 1:
        raise ValueError(f"radius {radius} is outside (0, 1]")
    power = remainder ** (REPETITIONS * 100)
    # power = num / den; find the largest B with power * 2**B <= 1.
    num, den = power.numerator, power.denominator
    # den >= num, so B is the largest integer with 2**B <= den / num.
    b = den.bit_length() - num.bit_length()
    while num << b > den:
        b -= 1
    while num << (b + 1) <= den:
        b += 1
    return b


def least_centibits(radius: Fraction) -> int:
    """Smallest B with 2 ** (-B / 100) <= (1 - radius) ** REPETITIONS, exactly.

    The upper track's `score` field points the inequality the other way, so on that track
    a *smaller* B is stronger.
    """
    remainder = 1 - radius
    if not 0 < remainder <= 1:
        raise ValueError(f"radius {radius} is outside (0, 1]")
    power = remainder ** (REPETITIONS * 100)
    num, den = power.numerator, power.denominator
    b = den.bit_length() - num.bit_length()
    while (num << b) < den:
        b += 1
    while b > 0 and (num << (b - 1)) >= den:
        b -= 1
    return b


def test_promoted_radius_is_admissible() -> None:
    assert 0 < PROMOTED_RADIUS < MIN_RELATIVE_DISTANCE


def test_promoted_score_is_exactly_reproduced() -> None:
    assert best_centibits(PROMOTED_RADIUS) == PROMOTED_CENTIBITS


def test_promoted_score_is_tight() -> None:
    """One more centibit must fail, or the submission left score on the table."""
    remainder = 1 - PROMOTED_RADIUS
    power = remainder ** (REPETITIONS * 100)
    assert power.numerator << PROMOTED_CENTIBITS <= power.denominator
    assert power.numerator << (PROMOTED_CENTIBITS + 1) > power.denominator


def test_score_is_strictly_increasing_in_radius() -> None:
    """The gradient claim in the intake, checked rather than asserted."""
    scores = [
        best_centibits(PROMOTED_RADIUS + Fraction(k, 33554432))
        for k in range(0, 5000, 1000)
    ]
    assert scores == sorted(scores)
    assert scores[0] < scores[-1]


def test_ceiling_is_the_128_bit_target() -> None:
    """The target is reachable within the profile: delta -> minRelativeDistance gives 128 bits.

    This is the reach comparison from intake question 4, in the same units as the target.
    """
    just_inside = MIN_RELATIVE_DISTANCE - Fraction(1, 2 ** 30)
    ceiling = best_centibits(just_inside)
    assert ceiling >= 12800, f"ceiling {ceiling} centibits is below the 12800 target"


def test_promoted_upper_score_is_exactly_reproduced() -> None:
    assert 0 < PROMOTED_UNSAFE_RADIUS < MIN_RELATIVE_DISTANCE
    assert least_centibits(PROMOTED_UNSAFE_RADIUS) == PROMOTED_UPPER_CENTIBITS


def test_upper_grid_is_finer_than_the_leaderboard_resolution() -> None:
    """The attack track's discretisation is *not* what is holding it back.

    The lower track takes an arbitrary rational `P/Q` while the upper track is pinned to
    `gridPt i = i / 2 ** 18`, which invites the guess that the attack side stalled because
    it cannot make small moves. Measured, that guess is wrong: one grid step is worth
    about 0.13 centibits, well under the one-centibit resolution the leaderboard reports
    in. Granularity is not the obstruction; the `unsafeAbove` obligation is.
    """
    steps = 100
    here = least_centibits(PROMOTED_UNSAFE_RADIUS)
    back = least_centibits(Fraction(PROMOTED_UNSAFE_INDEX - steps, DOMAIN_SIZE))
    per_step = (here - back) / steps
    assert 0 < per_step < 1, f"one grid step is {per_step} centibits, expected under 1"
    # A single step cannot even move the reported score.
    assert least_centibits(Fraction(PROMOTED_UNSAFE_INDEX - 1, DOMAIN_SIZE)) == here


def test_the_two_tracks_bracket_the_open_interval() -> None:
    lower = best_centibits(PROMOTED_RADIUS)
    upper = least_centibits(PROMOTED_UNSAFE_RADIUS)
    assert lower < upper, "certified soundness must sit below the certified attack"
    assert upper <= 12800, "the attack side must sit at or below the 128-bit target"


if __name__ == "__main__":
    print(f"promoted radius      {PROMOTED_RADIUS} = {float(PROMOTED_RADIUS):.9f}")
    print(f"promoted score       {best_centibits(PROMOTED_RADIUS)} centibits "
          f"(submission claims {PROMOTED_CENTIBITS})")
    print(f"admissible interval  (0, {MIN_RELATIVE_DISTANCE}) = "
          f"(0, {float(MIN_RELATIVE_DISTANCE):.9f})")
    ceiling = best_centibits(MIN_RELATIVE_DISTANCE - Fraction(1, 2 ** 30))
    print(f"ceiling at the edge  {ceiling} centibits")
    print()
    print(f"unsafe radius        {PROMOTED_UNSAFE_RADIUS} = "
          f"{float(PROMOTED_UNSAFE_RADIUS):.9f}  (grid index {PROMOTED_UNSAFE_INDEX})")
    print(f"unsafe score         {least_centibits(PROMOTED_UNSAFE_RADIUS)} centibits "
          f"(submission claims {PROMOTED_UPPER_CENTIBITS})")
    step = (least_centibits(PROMOTED_UNSAFE_RADIUS)
            - least_centibits(Fraction(PROMOTED_UNSAFE_INDEX - 100, DOMAIN_SIZE))) / 100
    print(f"one upper grid step  {step} centibits")
    print(f"open interval        {best_centibits(PROMOTED_RADIUS)} .. "
          f"{least_centibits(PROMOTED_UNSAFE_RADIUS)} centibits")
