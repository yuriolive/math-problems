# `tools/paper` — shared LaTeX → PDF pipeline

One paper directory per problem; this module builds any of them. Reusable: adding a paper
to a new problem needs no new build code.

## Use

```bash
uv run python tools/paper/build.py problems/erdos/64/paper     # build one
uv run python tools/paper/build.py --all              # build every paper in the repo
uv run python tools/paper/build.py problems/erdos/64/paper --clean
```

Or from a problem directory that has the target wired up:

```bash
make paper
make paper-clean
```

## Adding a paper to another problem

1. Create `<problem>/paper/main.tex` starting with

   ```latex
   \documentclass[11pt,a4paper]{article}
   \input{preamble}
   ```

   `preamble` resolves to `tools/paper/shared/preamble.tex` — the builder puts that
   directory on `TEXINPUTS`, so no relative paths are needed and papers stay movable.

2. Optionally add `refs.bib` next to it; the builder runs BibTeX when a `.bib` is present.

3. Optionally add to that problem's `Makefile`:

   ```make
   paper:
   	cd ../.. && uv run python tools/paper/build.py <problem>/paper
   ```

`--all` discovers papers by scanning for a `.tex` containing `\documentclass`, so step 3
is only a convenience.

## What the builder does

- Picks an engine: `latexmk` (preferred — it decides the pass count and runs BibTeX
  itself), else `tectonic`, else a manual `pdflatex → bibtex → pdflatex → pdflatex` loop,
  else `xelatex`/`lualatex`. Reports which one it used.
- Puts `tools/paper/shared` on `TEXINPUTS` and `BIBINPUTS`.
- Verifies the output is a real PDF (exists, non-trivial size) and reports the page count,
  read straight out of the PDF with no extra dependency. A build that leaves a stale PDF
  from a previous run is therefore not mistaken for a success.
- On failure, prints the first actual TeX error line rather than the whole log.
- Deletes intermediates on success (`--keep-intermediates` to inspect them).

## Conventions

`shared/preamble.tex` carries the theorem environments, the graph-theory shorthands, and
`\checkedin{...}` — the marker used to attach a Lean identifier to a statement, so a
reader can find the machine-checked version of anything asserted in a paper. Keep it to
packages present in a default MiKTeX/TeX Live install; a paper needing something exotic
should load it itself.

Built PDFs are tracked in git so they are readable on GitHub; TeX intermediates are
ignored via the repository `.gitignore`.
