"""Scaffold a new problem directory, intake questions first.

This repository has failed twice at problem selection and never at orchestration:

* A GPU campaign swept cubic graphs from n = 32 to n = 52 for Erdős #64 before anyone
  read that f(4) >= 54 makes every one of those orders provably empty.
* The verifier is a 64-vertex bitmask engine, so the open gap f(4) in [54, 78] was half
  out of reach before a line of search code ran.

Both were knowable in an afternoon of reading. So the scaffold writes the four intake
questions at the top of the new README and refuses to pretend they are answered: the
file is created with them unanswered and `--check` reports any problem directory whose
questions are still blank.

    uv run python tools/intake/scaffold.py erdos 707      # create problems/erdos/707/
    uv run python tools/intake/scaffold.py --check        # find unanswered intakes

Exits non-zero when `--check` finds an unanswered intake, so it can gate a commit.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROBLEMS = REPO_ROOT / "problems"

UNANSWERED = "_unanswered_"

QUESTIONS = [
    ("checker",
     "Can a compiled ground-truth checker be written in about a day?",
     "It defines what a solution *is*. Without it a search produces numbers nobody\n"
     "should trust, and every published figure here that turned out to be false came\n"
     "from trusting a search kernel's own counters."),
    ("gradient",
     "Does the objective have a gradient — does a small perturbation move the score?",
     "Circle packing rewards the twelfth decimal place, so evolutionary search climbs.\n"
     "A lexicographic integer profile barely moves under an edge swap, so it does not.\n"
     "This single property predicts whether search or proof is the right instrument."),
    ("gap",
     "Is there a published open gap strictly easier than the headline conjecture?",
     "There usually is, and it is usually far more tractable. Keep it one flag away\n"
     "from the main objective, and never conflate a hit on it with the harder claim."),
    ("reach",
     "Is the reachable instance size inside the checker's hard limit?",
     "State the limit as a number and the target range as a number, in the same units,\n"
     "and compare them here. Erdős #64's verifier stops at 64 vertices while the open\n"
     "gap runs to 78; writing both down would have caught it."),
]

README_TEMPLATE = """# {collection} {ident}

> **Statement.** _One paragraph. What is being asked, precisely enough that a checker
> could be written from this text alone._

> **Status.** Open / partially settled / settled. Cite the source for that claim.

## 0. Intake

Answered before any code was written. Rule 6 and Rule 12 both apply here: read the
literature and check the instrument's reach before spending compute.

{questions}

**Verdict.** {unanswered}

_A problem that fails the gradient question is a proof target, not a search target, and
should be scaffolded with `formalization/` and no `cuda/`. A problem that fails the reach
question needs the checker widened first, or a different target._

## 1. Known results

| Result | Value | Source |
| :--- | :--- | :--- |
| _the field's scale function, if it has one_ | | |
| _best known bound_ | | |
| _settled region_ | | |

Every row needs a citation: author, year, and a URL, arXiv id or DOI. A bound that
cannot be cited is not a bound.

## 2. What would count as progress

_Be specific and falsifiable. "Improve the bound" is not an answer; "decide whether
f(4) = 54" is._

## 3. Measured state

_Empty until a checker has run. Numbers here come from the compiled checker, never from
a search kernel. A count that hit its cap prints as `N+`._

## 4. Layout

```
{path}/
├── README.md               this file
├── ROADMAP.md              what is worth trying, what is closed, and why
├── verifier/               compiled ground-truth checker
└── tests/                  differential tests against a slow reference
```

Add `cuda/`, `sat/`, `formalization/` and `paper/` when the intake verdict calls for
them. The shared paper build needs no configuration:
`uv run python tools/paper/build.py {path}/paper`.
"""

ROADMAP_TEMPLATE = """# {collection} {ident} — roadmap

## Live directions

_One heading per direction, each with: what it would show, what it needs, and how it
would be verified._

## Closed directions

_Directions ruled out, and the reason. This section is the most valuable one in the file:
it stops the same dead end being re-entered. A direction closed by a published result
gets the citation; one closed by a measurement gets the command that measured it._

## Rules

The repository's working rules apply. The two that bite first on a new problem:

* Ground truth is a separate program from the search.
* "Absent" must never mean "not evaluated".
"""


def question_block() -> str:
    out = []
    for i, (key, question, why) in enumerate(QUESTIONS, 1):
        why_text = "\n".join(f"> {line}" for line in why.splitlines())
        out.append(
            f"### {i}. {question}\n\n"
            f"{why_text}\n\n"
            f"**Answer.** {UNANSWERED}\n"
        )
    return "\n".join(out)


def create(collection: str, ident: str, force: bool) -> int:
    target = PROBLEMS / collection / ident
    if target.exists() and not force:
        print(f"{rel(target)} already exists; pass --force to add missing files only")
        if not any(target.iterdir()):
            pass
        else:
            return 1

    (target / "tests").mkdir(parents=True, exist_ok=True)
    (target / "verifier").mkdir(parents=True, exist_ok=True)

    path = rel(target)
    files = {
        target / "README.md": README_TEMPLATE.format(
            collection=collection.capitalize(), ident=ident, path=path,
            questions=question_block(), unanswered=UNANSWERED),
        target / "ROADMAP.md": ROADMAP_TEMPLATE.format(
            collection=collection.capitalize(), ident=ident),
    }
    written = []
    for p, content in files.items():
        if p.exists() and not force:
            print(f"  kept {rel(p)}")
            continue
        p.write_text(content, encoding="utf-8")
        written.append(rel(p))

    for w in written:
        print(f"  wrote {w}")
    print(f"\n{path} scaffolded. Answer the four intake questions in its README before "
          f"writing code.\nThen: uv run python tools/intake/scaffold.py --check")
    return 0


def check() -> int:
    if not PROBLEMS.is_dir():
        print("no problems/ directory")
        return 1

    readmes = sorted(PROBLEMS.glob("*/*/README.md"))
    if not readmes:
        print("no problem READMEs found")
        return 1

    findings = []
    for readme in readmes:
        text = readme.read_text(encoding="utf-8")
        if "## 0. Intake" not in text:
            findings.append(f"{rel(readme)}: no intake section")
            continue
        n = text.count(UNANSWERED)
        if n:
            findings.append(f"{rel(readme)}: {n} intake answer(s) still {UNANSWERED}")

    if findings:
        print(f"{len(findings)} finding(s):")
        for f in findings:
            print("  " + f)
        return 1

    print(f"{len(readmes)} problem(s) checked, every intake question answered")
    return 0


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("collection", nargs="?", help="e.g. erdos")
    ap.add_argument("ident", nargs="?", help="e.g. 707")
    ap.add_argument("--check", action="store_true",
                    help="report problem directories with unanswered intake questions")
    ap.add_argument("--force", action="store_true", help="overwrite existing template files")
    args = ap.parse_args(argv)

    if args.check:
        return check()
    if not args.collection or not args.ident:
        ap.error("give a collection and an identifier, or pass --check")
    return create(args.collection, args.ident, args.force)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
