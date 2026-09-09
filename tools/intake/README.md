# `tools/intake` — choosing the problem before the architecture

Both of this repository's real failures were selection failures. Neither was fixable by
any orchestrator, framework, or model:

* A GPU campaign swept cubic graphs from $n = 32$ to $n = 52$ for Erdős #64. The
  literature's $f(4) \ge 54$ makes every one of those orders provably empty.
* The verifier is a 64-vertex bitmask engine. The open gap $f(4) \in [54, 78]$ was more
  than half out of reach before a line of search code ran.

Both were answerable in an afternoon of reading. So the scaffold puts four questions at
the top of a new problem's README, unanswered, and `--check` fails while any of them
still is.

```bash
uv run python tools/intake/scaffold.py erdos 707   # create problems/erdos/707/
uv run python tools/intake/scaffold.py --check     # find unanswered intakes
```

## The four questions

**1. Can a compiled ground-truth checker be written in about a day?**
It defines what a solution *is*. Every published figure here that turned out to be false
came from trusting a search kernel's own counters instead.

**2. Does the objective have a gradient — does a small perturbation move the score?**
The single best predictor of which instrument will work, and cheap to answer in advance.
A real-valued objective where the twelfth decimal place counts is something evolutionary
search can climb. A lexicographic integer profile that most local moves leave unchanged
is not. **A flat objective is a proof target, not a search target** — scaffold it with
`formalization/` and no `cuda/`.

**3. Is there a published open gap strictly easier than the headline conjecture?**
There usually is, and it is usually far more tractable. Keep it one flag away from the
main objective, and never conflate a hit on it with the harder claim.

**4. Is the reachable instance size inside the checker's hard limit?**
Write the limit and the target range down as numbers, in the same units, and compare them
in the README. That comparison is one line long and would have caught the second failure
above.

## The worked example

[`problems/erdos/64`](../../problems/erdos/64/) has its intake section filled in
retrospectively, and it fails three of the four. It is the most useful thing in that file:
the search side produced no result, the Lean side produced a machine-checked density
bound, and question 2 predicted exactly that split.

## What the scaffold writes

```
problems/<collection>/<id>/
├── README.md               intake questions, known results table, measured state
├── ROADMAP.md              live directions, and closed ones with the reason
├── verifier/               empty; the checker goes here, before the search
└── tests/                  empty; differential tests go here
```

`cuda/`, `sat/`, `formalization/` and `paper/` are added when the intake verdict calls for
them, rather than by default — a problem that fails the gradient question should not be
given a GPU searcher out of habit.

The known-results table requires a citation per row: author, year, and a URL, arXiv id or
DOI. A bound that cannot be cited is not a bound.
