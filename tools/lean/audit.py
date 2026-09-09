"""Enforce the no-`sorry` rule mechanically instead of by inspection.

Rule 8 of this repository says every theorem is audited with `#print axioms` and that an
unproved obligation must be a named hypothesis rather than a `sorry`. Until now that was
checked by a person reading Lean output, which is exactly the kind of check that passes
by habit. This does it as a command that exits non-zero.

Two passes, because they catch different lies:

1. **Source scan.** `sorry` or `admit` anywhere in a tracked `.lean` file. A `sorry` in a
   file that is never imported by an audit target would otherwise be invisible to pass 2.
2. **Axiom audit.** Run each project's audit file (any `*Check.lean` at its root) through
   `lake env lean` and read every `depends on axioms: [...]` line. Anything outside the
   three standard axioms fails, and `sorryAx` fails loudest: it is what a `sorry`
   actually compiles to, so a theorem can look proved and still carry it.

`Lean.ofReduceBool` and `Lean.trustCompiler` are called out separately. They are not
unsound, but they mean a claim rests on the compiler evaluating a decision procedure
rather than on a proof, and Rule 5 says which layer is trusted must be written down.

    uv run python tools/lean/audit.py                    # every Lean project found
    uv run python tools/lean/audit.py <project-dir> ...  # specific projects
    uv run python tools/lean/audit.py --list             # show what would be audited

Exits non-zero on any finding, so it can gate a commit.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# `vendor` and `upstream` hold third-party Lean that is fetched by hand and not
# redistributed here. Auditing it would report on someone else's proofs as though they
# were this repository's, which is the opposite of what rule 8 is for.
SKIP_PARTS = {".lake", ".git", "__pycache__", "target", "node_modules", ".venv", "vendor",
              "upstream"}

# The axioms Mathlib itself rests on. A theorem depending only on these is as proved as
# anything in Mathlib is.
STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

# Not unsound, but they shift the claim onto the compiler or the kernel's evaluator.
TRUSTED_AXIOMS = {"Lean.ofReduceBool", "Lean.trustCompiler"}

# `sorry` compiles to this. It is the single most important thing here.
SORRY_AXIOM = "sorryAx"

AXIOM_LINE = re.compile(r"'([^']+)' depends on axioms: \[([^\]]*)\]")

# `sorry` as a token, not as a substring of an identifier or inside a word in a comment.
SORRY_TOKEN = re.compile(r"(?<![A-Za-z0-9_.])(sorry|admit)(?![A-Za-z0-9_'])")


def strip_comments(text: str) -> str:
    """Blank out Lean comments, preserving line structure so line numbers survive.

    Needed because the honest thing to do in this repository is to write "no `sorry`
    appears in this project" in a docstring, and a scanner that reads its own
    documentation as a violation is useless. Lean block comments nest, so track depth.
    """
    out = []
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        two = text[i:i + 2]
        if depth == 0 and two == "--":
            j = text.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
        elif two == "/-":
            depth += 1
            out.append("  ")
            i += 2
        elif two == "-/" and depth > 0:
            depth -= 1
            out.append("  ")
            i += 2
        else:
            ch = text[i]
            out.append(ch if (depth == 0 or ch == "\n") else " ")
            i += 1
    return "".join(out)


class Finding:
    def __init__(self, where: str, what: str, detail: str = ""):
        self.where = where
        self.what = what
        self.detail = detail

    def __str__(self) -> str:
        tail = f"\n      {self.detail}" if self.detail else ""
        return f"{self.where}: {self.what}{tail}"


def find_projects(paths: list[str]) -> list[Path]:
    """A Lean project is a directory with a lakefile and a pinned toolchain."""
    if paths:
        out = []
        for p in paths:
            d = Path(p).resolve()
            if not d.is_dir():
                raise SystemExit(f"not a directory: {p}")
            out.append(d)
        return out

    projects = []
    for lakefile in sorted(REPO_ROOT.rglob("lakefile.*")):
        if any(part in SKIP_PARTS for part in lakefile.parts):
            continue
        d = lakefile.parent
        if (d / "lean-toolchain").is_file() and d not in projects:
            projects.append(d)
    return projects


def scan_sources(project: Path) -> list[Finding]:
    """Pass 1: a `sorry` token in any Lean source under the project."""
    findings = []
    for src in sorted(project.rglob("*.lean")):
        if any(part in SKIP_PARTS for part in src.parts):
            continue
        try:
            text = src.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            findings.append(Finding(rel(src), f"unreadable ({e})"))
            continue
        code = strip_comments(text)
        raw_lines = text.splitlines()
        for i, line in enumerate(code.splitlines(), 1):
            m = SORRY_TOKEN.search(line)
            if m:
                findings.append(Finding(
                    f"{rel(src)}:{i}",
                    f"`{m.group(1)}` in source",
                    "an unproved obligation must be a named hypothesis: "
                    f"{raw_lines[i - 1].strip()[:70]}",
                ))
    return findings


def audit_files(project: Path) -> list[Path]:
    return sorted(p for p in project.glob("*Check.lean"))


IMPORT_LINE = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)", re.MULTILINE)


def missing_local_import(project: Path, audit: Path) -> str | None:
    """Name a project-local module the audit file needs but that is not present.

    `BridgeCheck.lean` imports `EGCBridge`, which imports `EGC` -- a third-party file that
    carries no license and so is deliberately not redistributed. On a machine without it,
    the right answer is "this audit was not run", not "this audit failed" and certainly
    not silence. Walks imports transitively over modules that would live in this project.
    """
    seen: set[str] = set()
    stack = [audit]
    while stack:
        f = stack.pop()
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for mod in IMPORT_LINE.findall(strip_comments(text)):
            if mod in seen:
                continue
            seen.add(mod)
            # Only project-local modules are our problem; Mathlib and Lean core are Lake's.
            root = mod.split(".")[0]
            if root in {"Mathlib", "Init", "Std", "Lean", "Batteries", "Aesop", "Qq",
                        "Plausible", "ProofWidgets", "ImportGraph", "LeanSearchClient",
                        "Cli"}:
                continue
            candidates = [project / (mod.replace(".", "/") + ".lean")]
            if not any(c.is_file() for c in candidates):
                return mod
            stack.append(next(c for c in candidates if c.is_file()))
    return None


def run_audit(project: Path, audit: Path) -> tuple[list[Finding], int]:
    """Pass 2: read the `#print axioms` output. Returns (findings, theorems seen)."""
    try:
        proc = subprocess.run(
            ["lake", "env", "lean", audit.name],
            cwd=project, capture_output=True, text=True, timeout=1800,
        )
    except FileNotFoundError:
        return [Finding(rel(audit), "`lake` not found on PATH — cannot audit axioms")], 0
    except subprocess.TimeoutExpired:
        return [Finding(rel(audit), "audit timed out after 30 minutes")], 0

    out = proc.stdout + proc.stderr
    matches = AXIOM_LINE.findall(out)

    findings = []
    if proc.returncode != 0 and not matches:
        first = next((l for l in out.splitlines() if "error" in l.lower()), out.strip()[:200])
        return [Finding(rel(audit), f"lean exited {proc.returncode}", first)], 0

    for name, axioms in matches:
        used = {a.strip() for a in axioms.split(",") if a.strip()}
        if SORRY_AXIOM in used:
            findings.append(Finding(
                rel(audit),
                f"{name} depends on {SORRY_AXIOM}",
                "this theorem is NOT proved: `sorry` is in its dependency graph",
            ))
            continue
        unexpected = used - STANDARD_AXIOMS - TRUSTED_AXIOMS
        if unexpected:
            findings.append(Finding(
                rel(audit), f"{name} depends on unexpected axioms",
                ", ".join(sorted(unexpected)),
            ))
        trusted = used & TRUSTED_AXIOMS
        if trusted:
            findings.append(Finding(
                rel(audit), f"{name} rests on a trusted evaluator",
                f"{', '.join(sorted(trusted))} — say so wherever this theorem is cited",
            ))

    if not matches:
        findings.append(Finding(
            rel(audit), "no `#print axioms` output",
            "the audit file compiled but audited nothing; add `#print axioms <thm>` lines",
        ))
    return findings, len(matches)


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("projects", nargs="*", help="Lean project directories (default: all found)")
    ap.add_argument("--list", action="store_true", help="list what would be audited and stop")
    ap.add_argument("--skip-build", action="store_true",
                    help="only scan sources; do not invoke lake")
    args = ap.parse_args(argv)

    projects = find_projects(args.projects)
    if not projects:
        print("no Lean projects found")
        return 1

    if args.list:
        for d in projects:
            audits = audit_files(d)
            names = ", ".join(a.name for a in audits) or "no *Check.lean file"
            print(f"{rel(d)}  ({names})")
        return 0

    findings: list[Finding] = []
    skipped: list[tuple[str, str]] = []
    audited = 0

    for d in projects:
        print(f"auditing {rel(d)}")
        findings += scan_sources(d)

        if args.skip_build:
            continue

        audits = audit_files(d)
        if not audits:
            # Not every Lean project claims a theorem; one that does must audit it.
            print("  no *Check.lean file, nothing to audit")
            continue
        for a in audits:
            gone = missing_local_import(d, a)
            if gone:
                skipped.append((rel(a), gone))
                print(f"  {a.name}: SKIPPED, needs absent module `{gone}`")
                continue
            fs, n = run_audit(d, a)
            findings += fs
            audited += n
            print(f"  {a.name}: {n} theorem(s) audited")

    print()
    if findings:
        print(f"{len(findings)} finding(s):")
        for f in findings:
            print(f"  {f}")
        return 1

    # An audit that could not run is neither a pass nor a failure, and must not be
    # reported as either. Rule 2, applied to this tool's own output.
    for where, mod in skipped:
        print(f"NOT AUDITED: {where} needs `{mod}`, which is not present. Its theorems "
              f"carry no verdict here.")

    # Rule 2 applies to this tool as much as to anything it checks: with --skip-build
    # nothing was audited, and saying "axioms are standard" would be reporting an
    # unevaluated check as a passing one.
    if args.skip_build:
        print(f"source scan only across {len(projects)} project(s): no `sorry` or `admit` "
              f"token found. AXIOMS NOT AUDITED -- run without --skip-build for that.")
        return 0

    tail = f", {len(skipped)} audit file(s) skipped" if skipped else ""
    print(f"{audited} theorem(s) audited across {len(projects)} project(s); "
          f"axioms are {', '.join(sorted(STANDARD_AXIOMS))} only{tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
