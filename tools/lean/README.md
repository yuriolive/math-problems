# `tools/lean` — axiom audit

Rule 8 says no `sorry`, and that every theorem is audited with `#print axioms`. That was
checked by a person reading Lean output, which is the kind of check that passes by habit.
This makes it a command that exits non-zero.

```bash
uv run python tools/lean/audit.py
```

```
auditing problems/erdos/64/formalization
  no *Check.lean file, nothing to audit
auditing problems/erdos/64/formalization-egc
  AxiomCheck.lean: 6 theorem(s) audited
  BridgeCheck.lean: 4 theorem(s) audited
  DensityCheck.lean: 5 theorem(s) audited

15 theorem(s) audited across 2 project(s); axioms are Classical.choice, Quot.sound, propext only
```

## Two passes

**Source scan** — a `sorry` or `admit` token in any `.lean` file under the project. This
runs first because a `sorry` in a file no audit target imports would be invisible to the
second pass. Lean comments are stripped before scanning, including nested `/- -/` blocks,
so a docstring that says "no `sorry` appears in this project" is not read as a violation
of itself.

**Axiom audit** — each `*Check.lean` at a project root is run through `lake env lean` and
every `depends on axioms: [...]` line is parsed.

| Axiom set | Treatment |
| :--- | :--- |
| `propext`, `Classical.choice`, `Quot.sound` | expected; as proved as anything in Mathlib |
| `sorryAx` | **failure** — the theorem is not proved; this is what `sorry` compiles to |
| `Lean.ofReduceBool`, `Lean.trustCompiler` | reported — not unsound, but the claim rests on an evaluator, and rule 5 says which layer is trusted must be written down |
| anything else | failure |

A theorem carrying `sorryAx` looks proved at every level except this one, which is the
whole reason the pass exists.

## Flags

| Flag | Effect |
| :--- | :--- |
| `--list` | show the projects and audit files that would be used, then stop |
| `--skip-build` | source scan only; does not invoke `lake` (fast, no toolchain needed) |
| _positional_ | audit only the given project directories |

## Audits that could not run

An audit file whose project-local imports are missing is reported as **NOT AUDITED** and
counted separately — neither a pass nor a failure. `BridgeCheck.lean` is the standing case:
it needs `EGC.lean`, a third-party file with no license that is gitignored rather than
redistributed, so on a fresh clone and in CI it cannot be checked at all.

```
BridgeCheck.lean: SKIPPED, needs absent module `EGC`
NOT AUDITED: .../BridgeCheck.lean needs `EGC`, which is not present.
             Its theorems carry no verdict here.
11 theorem(s) audited ... , 1 audit file(s) skipped
```

Reporting that as green would be rule 2 — "absent must never mean not evaluated" — broken
by the tool written to enforce rule 8.

## Relationship to lean-action

[`leanprover/lean-action`](https://github.com/leanprover/lean-action) has its own
`axiom-audit` input, defaulting to exactly `propext,Classical.choice,Quot.sound`, and this
repository's CI uses the action to build. What this script adds on top:

* the `sorry`/`admit` **source** scan, which catches a file no audit target imports;
* the NOT-AUDITED distinction above;
* the trusted-evaluator call-out (`Lean.ofReduceBool`, `Lean.trustCompiler`);
* repo-wide project discovery, so a second problem is covered without configuration;
* the same result locally, with no CI and no network.

CI additionally runs the action's `lean4checker`, which re-checks every proof in the kernel
independently of the elaborator. That is **stronger** than `#print axioms`, which trusts
the environment it reads. If the two ever disagree, believe lean4checker.

## Notes

A Lean project is any directory holding a `lakefile.*` and a `lean-toolchain`. `vendor/`
is skipped, along with `.lake/` and the usual build directories.

`EGC.lean` is gitignored in two places — the project root and `vendor/` — so a fresh
clone has neither copy and `BridgeCheck.lean` is skipped rather than failing. Fetch the
file by hand into the project root to audit those four theorems locally.

The full audit compiles against Mathlib and is slow on a cold cache. `--skip-build` is
the one to use in a tight loop.
