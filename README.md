# math-problems

A working stack for attacking open problems in mathematics: search for counterexamples,
check every candidate with compiled code, and formalize whatever turns out to be provable.

The organising principle is that **nothing is believed because a search said so**. Every
number that leaves this repository comes from a checker independent of the thing being
checked, and anything claimed as proved is machine-checked in Lean 4.

## Layout

```
problems/<collection>/<id>/   one directory per problem, e.g. problems/erdos/64/
tools/                        code reused across problems
.agents/skills/               the methodology, as a reusable agent skill
```

Inside a problem directory the convention is:

```
problems/<collection>/<id>/
├── README.md               the statement, the literature, and the measured state
├── ROADMAP.md              what is worth trying, what is closed, and why
├── verifier/               compiled ground-truth checker (Rust)
├── cuda/                   GPU search, if the problem admits one
├── sat/                    SAT/SMT encoding, if it admits one
├── engine/                 candidate evaluation, archive, run log
├── formalization*/         Lean 4 projects
├── paper/                  main.tex, built by tools/paper
├── tools/                  problem-specific scripts
└── tests/                  including differential tests against the verifier
```

`tools/` at the root is the shared layer; `problems/<...>/tools/` is problem-specific. When
a script proves useful twice, it moves up.

## The shared layer

* **[`tools/paper`](./tools/paper/)** — LaTeX → PDF pipeline. Picks whatever TeX engine is
  installed, settles references and bibliography, verifies the output is a real PDF and
  reports its page count, and prints the first genuine TeX error on failure. Adding a paper
  to a new problem needs no new build code:
  `uv run python tools/paper/build.py problems/<collection>/<id>/paper`, or `--all`. Shared
  macros live in `tools/paper/shared/preamble.tex`, including `\checkedin{...}` for
  attaching a Lean identifier to a printed statement.
* **[`tools/intake`](./tools/intake/)** — scaffolds a new problem with the four intake
  questions unanswered at the top of its README, and `--check` fails while any of them
  still is. The questions are the ones that would have prevented this repository's two
  real failures: a campaign over a provably empty region, and a target half of which lay
  outside the checker's hard limit.
  `uv run python tools/intake/scaffold.py <collection> <id>`.
* **[`tools/lean`](./tools/lean/)** — makes rule 8 a command instead of a habit. Scans
  every Lean source for a `sorry` or `admit` token, then runs each project's `*Check.lean`
  through `lake env lean` and reads the `#print axioms` output, failing on `sorryAx` or
  any axiom outside the three standard ones, and flagging separately where a claim rests
  on a trusted evaluator. `uv run python tools/lean/audit.py`.
* **[`tools/check_docs.py`](./tools/check_docs.py)** — catches markdown that renders
  broken on GitHub even though it looks fine locally: `#` inside math (KaTeX refuses it),
  a LaTeX word that lost its backslash, and an unescaped `$` that silently opens a math
  span across paragraphs. All three have occurred here. Run
  `uv run python tools/check_docs.py`; it exits non-zero, so it can gate a commit.
* **[`.agents/skills/neuro-symbolic-math`](./.agents/skills/neuro-symbolic-math/)** — the
  methodology: how to scaffold a problem, how to build a checker that cannot quietly lie,
  how to design a search objective that actually has a gradient, and the working rules
  below.

Per-problem verifiers, GPU searchers and Lean setups are not yet factored into libraries;
they follow the documented pattern instead, on the view that the second instance is what
reveals the right abstraction.

## Working rules

Not stylistic. Each of these exists because violating it produced a false result here.

1. **Ground truth is a separate program.** Published numbers come from the compiled
   verifier, never from the search kernel, whose counters are capped and exist only to
   drive the search.
2. **"Absent" must never mean "not evaluated".** A checker carries three states —
   satisfied, violated, unknown — end to end. A short-circuited check that serializes as
   `false` will eventually be read as "absent" and published.
3. **Mark lower bounds as lower bounds.** A count that hit its cap prints as `N+`.
4. **Report only what was measured.** Throughput means operations whose result was actually
   computed, not loop iterations.
5. **Say which components are trusted and which are verified.** A pipeline whose Lean layer
   checks structure while a compiled binary checks the hard part has one verified layer and
   one trusted layer. Write that sentence down.
6. **Read the literature before spending compute.** Find the field's scale function and read
   the known bounds off it. A search below a settled frontier cannot succeed however long
   it runs — and that mistake has already cost this repository a campaign.
7. **Prefer the open published gap to the headline problem.** There is usually a real,
   citable target far more tractable than the conjecture itself. Keep it one flag away from
   the main objective, and never conflate a hit on the easier target with the harder one.
8. **No `sorry`.** An unproved obligation is a named hypothesis, visible in the statement,
   or a comment naming the tool that discharged it. Every theorem is audited with
   `#print axioms`.
9. **Replace a falsified claim, do not annotate it.** Corrections live in the commit
   history; the docs carry the current state.
10. **Every number traceable** to a command that was run or a source that can be cited.
11. **Delete a layer that has produced nothing.** An LLM synthesis loop ran here for
    a long time without ever beating the annealer it was supposed to help. Keeping it
    cost maintenance and implied a capability the repository did not have. Measure the
    layer, not the idea.
12. **Choose the problem before the architecture, and check the instrument's reach.**
    Both failures here were selection failures, not orchestration failures: a sweep over
    a region a published bound had already emptied, and a target more than half of which
    sat outside the verifier's 64-vertex limit. Write the limit and the target range down
    as numbers, in the same units, and compare them. `tools/intake` asks this.
13. **A flat objective is a proof target.** If a small perturbation does not move the
    score, evolutionary search has nothing to climb and the effort belongs in
    formalization instead. This is the single best predictor of which instrument will
    work, and it is cheap to answer in advance.

## Problems

Candidate next problems, scouted and screened against the intake filter, are in
[`problems/CANDIDATES.md`](./problems/CANDIDATES.md). Twenty were scouted and one survived
screening; the recorded failure patterns are more useful than the shortlist.


### [`problems/erdos/64`](./problems/erdos/64/) — Erdős–Gyárfás conjecture

Does every finite graph with minimum degree at least 3 contain a cycle whose length is a
power of two? Open.

* **Search side.** No counterexample, and the published bounds are unchanged. The reachable
  region turned out to be *provably* empty: the literature's $f(4) \ge 54$ means no cubic
  counterexample exists below 54 vertices, so every order this repository had been sweeping
  was excluded in advance. The live computational target is instead closing
  $f(4) \in [54, 78]$, a strictly easier and genuinely open question.
* **Formalization side.** A machine-checked strict density bound for a hypothetical minimal
  counterexample, $|V_3| > \tfrac{2}{3}|V|$ — an argument due to a forum contributor,
  previously unverified — plus a reformulation identifying exactly what controls that
  constant, and a conditional improvement to $12/17$. No `sorry`; every theorem audits to
  the three standard axioms.
* Write-up: [`problems/erdos/64/paper/main.pdf`](./problems/erdos/64/paper/main.pdf).
  Measured candidate table and details:
  [`problems/erdos/64/README.md`](./problems/erdos/64/README.md). What is worth trying
  next, and what is closed:
  [`problems/erdos/64/ROADMAP.md`](./problems/erdos/64/ROADMAP.md).

## Adding a problem

1. `mkdir -p problems/<collection>/<id>` and write its `README.md` first: the statement,
   the known bounds with citations, and what would count as progress. Rule 6 applies before
   any code is written.
2. Build the checker before the search. It defines what a solution *is*, and a search
   without it produces numbers nobody should trust.
3. Add differential tests — the fast checker against a slow, independent reference. In a
   repository like this one that is the single highest-value test.
4. Add `paper/main.tex` when there is something to write up; the build pipeline needs no
   configuration.

## Toolchain

| Component | Used for |
| :--- | :--- |
| Rust (2021) | compiled verifiers |
| Lean 4 + Lake, optionally Mathlib | formalization |
| CUDA (`nvcc`), Ada `sm_89` by default | GPU search |
| Python ≥ 3.12 via `uv` | orchestration and tooling |
| Z3 (`z3-solver`) | SAT/SMT encodings; the only third-party Python dependency |
| MiKTeX, TeX Live or Tectonic | paper builds |
| `agy` (Antigravity CLI) | optional; headless via `-p`, structured output via `--json-schema` |

Use `uv run python ...` rather than a bare `python`, so the pinned environment is used.
