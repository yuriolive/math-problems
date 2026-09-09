"""Rate analysis of the better.codes lower-track leaderboard, scraped 2026-09-09."""
import io, sys
from datetime import date
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# (date, score in bits) for every promoted lower-track submission, newest first.
D = [
    ((9, 6), 68.04), ((9, 4), 68.03), ((9, 3), 68.02), ((9, 3), 68.01), ((9, 3), 68.00),
    ((9, 2), 67.87), ((9, 2), 67.85), ((9, 2), 67.84), ((9, 2), 67.82), ((9, 2), 67.80),
    ((9, 1), 67.78), ((9, 1), 67.77), ((9, 1), 67.76), ((9, 1), 67.75),
    ((8, 31), 67.67), ((8, 31), 67.66), ((8, 31), 67.65), ((8, 31), 67.64),
    ((8, 31), 67.63), ((8, 31), 67.61), ((8, 31), 67.60), ((8, 31), 67.54),
    ((8, 31), 67.53),
    ((8, 30), 67.51), ((8, 30), 67.50), ((8, 30), 67.43), ((8, 30), 67.41),
    ((8, 30), 67.40), ((8, 30), 67.37), ((8, 30), 67.35), ((8, 30), 67.34),
    ((8, 29), 67.33), ((8, 29), 67.32),
    ((8, 28), 67.31), ((8, 28), 67.00), ((8, 28), 66.75), ((8, 28), 66.74),
    ((8, 28), 66.42), ((8, 28), 66.18), ((8, 28), 66.00), ((8, 28), 65.69),
    ((8, 28), 65.68),
    ((8, 27), 65.56), ((8, 27), 65.33), ((8, 27), 64.92), ((8, 27), 64.89),
    ((8, 27), 64.64), ((8, 27), 64.62), ((8, 27), 64.54), ((8, 27), 64.52),
    ((8, 27), 64.30), ((8, 27), 64.26), ((8, 27), 64.23), ((8, 27), 64.01),
    ((8, 21), 63.99), ((8, 21), 63.94), ((8, 21), 63.82), ((8, 21), 63.81),
    ((8, 20), 63.60), ((8, 20), 63.58), ((8, 20), 53.13), ((8, 20), 53.12),
]
TODAY = date(2026, 9, 9)
LAUNCH = date(2026, 8, 20)
TARGET = 116.13          # the certified attack bound: where the two tracks meet
BASELINE = 53.00         # literature baseline the challenge starts from

rows = [(date(2026, m, d), s) for (m, d), s in D][::-1]   # oldest first

print(f"submissions        {len(rows)}")
print(f"window             {rows[0][0]} .. {rows[-1][0]}  (today {TODAY})")
print(f"score              {rows[0][1]:.2f} -> {rows[-1][1]:.2f} bits")

total = rows[-1][1] - rows[0][1]
days = (rows[-1][0] - rows[0][0]).days
print(f"total movement     {total:.2f} bits in {days} days")

# The single largest jump dominates; strip it and look at the grind.
gains = [(rows[i+1][1] - rows[i][1], rows[i+1][0]) for i in range(len(rows) - 1)]
biggest = max(gains)
print(f"largest single     +{biggest[0]:.2f} bits on {biggest[1]}")
grind = total - biggest[0]
print(f"movement ex-jump   {grind:.2f} bits in {days} days = {grind/days:.4f} bits/day")

print()
for label, since in (("last 7 days", 7), ("last 14 days", 14)):
    cut = date.fromordinal(TODAY.toordinal() - since)
    win = [r for r in rows if r[0] >= cut]
    if len(win) >= 2:
        moved = win[-1][1] - win[0][1]
        print(f"{label:14} {moved:.2f} bits over {len(win)} submissions "
              f"= {moved/since:.4f} bits/day")

stall = (TODAY - rows[-1][0]).days
print(f"days since last    {stall}")

print()
remaining = TARGET - rows[-1][1]
print(f"remaining to {TARGET}  {remaining:.2f} bits")
for label, rate in (("all-time inc. jump", total / days),
                    ("all-time ex-jump", grind / days),
                    ("last 7 days", 0.29 / 7)):
    if rate > 0:
        yrs = remaining / rate / 365.25
        print(f"  at {label:20} {rate:.4f} bits/day -> {remaining/rate:7.0f} days "
              f"= {yrs:5.1f} years")

print()
# Diminishing returns: mean gain per submission, in order.
n = len(gains)
for lo, hi, name in ((0, n//3, "first third"), (n//3, 2*n//3, "second third"),
                     (2*n//3, n, "final third")):
    chunk = [g for g, _ in gains[lo:hi]]
    print(f"mean gain, {name:13} {sum(chunk)/len(chunk):.4f} bits/submission "
          f"(n={len(chunk)})")
