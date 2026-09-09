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

## Notes

A Lean project is any directory holding a `lakefile.*` and a `lean-toolchain`. `vendor/`
is skipped, along with `.lake/` and the usual build directories.

`problems/erdos/64/formalization-egc/BridgeCheck.lean` audits theorems that depend on
`vendor/EGC.lean`, a third-party file fetched by hand and deliberately not redistributed.
On a machine without it, `lake` fails and the audit reports that failure rather than
passing quietly — which is the correct behaviour, but it means a fresh clone will see a
finding there until the file is fetched.

The full audit compiles against Mathlib and is slow on a cold cache. `--skip-build` is
the one to use in a tight loop.
