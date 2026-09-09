"""Reusable LaTeX -> PDF build pipeline.

One paper directory per problem; this module builds any of them. It picks whatever TeX
engine is installed, runs enough passes to settle references and the bibliography,
verifies the PDF is real, and reports what it produced.

    uv run python tools/paper/build.py problems/erdos/64/paper
    uv run python tools/paper/build.py problems/erdos/64/paper --clean
    uv run python tools/paper/build.py --all

A paper directory needs a `main.tex` (or exactly one `*.tex` with a `\\documentclass`).
`refs.bib` is optional. Shared macros live in `tools/paper/shared/preamble.tex`; papers
pick them up via TEXINPUTS, so a paper only has to `\\input{preamble}`.

Engine preference: latexmk (handles the pass count and bibtex itself), then a manual
pdflatex/bibtex/pdflatex/pdflatex loop, then xelatex, then lualatex. Tectonic is used if
present since it needs no local package tree.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SHARED = Path(__file__).resolve().parent / "shared"

# Intermediates worth deleting; the PDF and the sources are never touched.
JUNK_SUFFIXES = {
    ".aux", ".bbl", ".blg", ".fls", ".fdb_latexmk", ".log", ".out", ".toc",
    ".lof", ".lot", ".synctex.gz", ".bcf", ".run.xml", ".nav", ".snm", ".vrb",
}


@dataclass
class Result:
    paper: Path
    pdf: Path | None
    pages: int | None
    engine: str
    ok: bool
    detail: str = ""


def find_tex(paper_dir: Path) -> Path:
    """The main source of a paper directory."""
    main = paper_dir / "main.tex"
    if main.is_file():
        return main
    candidates = [
        p for p in sorted(paper_dir.glob("*.tex"))
        if "\\documentclass" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(f"no .tex with a \\documentclass in {paper_dir}")
    raise RuntimeError(
        f"{paper_dir} has several candidate mains ({[c.name for c in candidates]}); "
        "name the entry point main.tex"
    )


def which(*names: str) -> str | None:
    for n in names:
        if shutil.which(n):
            return n
    return None


def tex_env() -> dict[str, str]:
    """Put the shared macros on TEXINPUTS so papers can `\\input{preamble}`."""
    env = dict(os.environ)
    sep = ";" if sys.platform == "win32" else ":"
    # A trailing empty entry keeps the default search path.
    env["TEXINPUTS"] = f"{SHARED}{sep}{env.get('TEXINPUTS', '')}{sep}"
    env["BIBINPUTS"] = f"{SHARED}{sep}{env.get('BIBINPUTS', '')}{sep}"
    env["max_print_line"] = "10000"
    return env


def run(cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True,
                          text=True, errors="replace", timeout=900)


def first_error(log: str) -> str:
    """Pull the first real TeX error out of a log, for a one-line report."""
    for line in log.splitlines():
        if line.startswith("!") or "Fatal error" in line:
            return line.strip()[:200]
    m = re.search(r"^l\.\d+.*$", log, re.MULTILINE)
    return (m.group(0).strip()[:200] if m else "see the .log")


def build_one(paper_dir: Path, keep_intermediates: bool = False) -> Result:
    paper_dir = paper_dir.resolve()
    tex = find_tex(paper_dir)
    stem = tex.stem
    env = tex_env()
    has_bib = (paper_dir / "refs.bib").is_file() or bool(list(paper_dir.glob("*.bib")))

    engine = which("latexmk") or which("tectonic") or which("pdflatex") or \
        which("xelatex") or which("lualatex")
    if engine is None:
        return Result(paper_dir, None, None, "none", False,
                      "no TeX engine found (install MiKTeX, TeX Live, or tectonic)")

    logs: list[str] = []
    if engine == "latexmk":
        proc = run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
                    "-file-line-error", tex.name], paper_dir, env)
        logs.append(proc.stdout + proc.stderr)
    elif engine == "tectonic":
        proc = run(["tectonic", "--keep-logs", "--synctex=false", tex.name], paper_dir, env)
        logs.append(proc.stdout + proc.stderr)
    else:
        # Manual passes: enough to settle labels, citations and the bibliography.
        passes = [[engine, "-interaction=nonstopmode", "-halt-on-error",
                   "-file-line-error", tex.name]]
        if has_bib:
            passes.append(["bibtex", stem])
        passes.append([engine, "-interaction=nonstopmode", "-halt-on-error",
                       "-file-line-error", tex.name])
        passes.append([engine, "-interaction=nonstopmode", "-halt-on-error",
                       "-file-line-error", tex.name])
        for cmd in passes:
            if cmd[0] == "bibtex" and not shutil.which("bibtex"):
                continue
            proc = run(cmd, paper_dir, env)
            logs.append(proc.stdout + proc.stderr)

    pdf = paper_dir / f"{stem}.pdf"
    if not pdf.is_file() or pdf.stat().st_size < 1000:
        return Result(paper_dir, None, None, engine, False, first_error("\n".join(logs)))

    pages = count_pages(pdf)
    if not keep_intermediates:
        clean(paper_dir, stem, keep_pdf=True)
    return Result(paper_dir, pdf, pages, engine, True)


def count_pages(pdf: Path) -> int | None:
    """Page count straight from the PDF, no dependencies."""
    try:
        data = pdf.read_bytes()
    except OSError:
        return None
    counts = [int(m.group(1)) for m in re.finditer(rb"/Count\s+(\d+)", data)]
    if counts:
        return max(counts)
    n = len(re.findall(rb"/Type\s*/Page[^s]", data))
    return n or None


def clean(paper_dir: Path, stem: str | None = None, keep_pdf: bool = True) -> list[Path]:
    removed = []
    for p in paper_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix == ".pdf" and keep_pdf:
            continue
        if "".join(p.suffixes[-2:]) in JUNK_SUFFIXES or p.suffix in JUNK_SUFFIXES:
            p.unlink()
            removed.append(p)
    return removed


def discover(root: Path) -> list[Path]:
    """Every directory holding a buildable paper."""
    found = []
    for tex in sorted(root.rglob("*.tex")):
        if ".lake" in tex.parts or "shared" in tex.parts:
            continue
        try:
            if "\\documentclass" in tex.read_text(encoding="utf-8", errors="ignore"):
                found.append(tex.parent)
        except OSError:
            continue
    return sorted(set(found))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a paper to PDF")
    ap.add_argument("paper", nargs="?", help="paper directory (e.g. problems/erdos/64/paper)")
    ap.add_argument("--all", action="store_true", help="build every paper in the repo")
    ap.add_argument("--clean", action="store_true", help="delete intermediates and exit")
    ap.add_argument("--keep-intermediates", action="store_true",
                    help="leave .aux/.log in place for debugging")
    args = ap.parse_args()

    if args.all:
        targets = discover(REPO_ROOT)
        if not targets:
            print("no papers found")
            return 1
    elif args.paper:
        targets = [Path(args.paper)]
    else:
        ap.error("give a paper directory or --all")

    if args.clean:
        for t in targets:
            removed = clean(Path(t).resolve(), keep_pdf=True)
            print(f"{t}: removed {len(removed)} intermediate file(s)")
        return 0

    failures = 0
    for t in targets:
        try:
            res = build_one(Path(t), keep_intermediates=args.keep_intermediates)
        except Exception as e:
            print(f"FAIL {t}: {e}")
            failures += 1
            continue
        if res.ok and res.pdf is not None:
            rel = res.pdf.relative_to(REPO_ROOT) if REPO_ROOT in res.pdf.parents else res.pdf
            size_kb = res.pdf.stat().st_size // 1024
            print(f"OK   {rel}  ({res.pages} pages, {size_kb} KB, via {res.engine})")
        else:
            print(f"FAIL {t}  (via {res.engine}): {res.detail}")
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
