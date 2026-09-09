"""Check the markdown docs for rendering bugs that are easy to introduce and silent.

GitHub renders `$...$` and `$$...$$` with KaTeX, which fails differently from a local
LaTeX run, so a doc can look fine in an editor and render broken on the web. Three
failure modes have actually occurred in this repository:

1. **`#` inside math.** KaTeX rejects it outright: "You can't use 'macro parameter
   character #' in math mode". Write `\\operatorname{...}` or prose instead.
2. **A lost backslash.** Writing docs through a shell heredoc can swallow one level of
   escaping, turning `\\text{...}` into a literal tab plus `ext{...}`, or `\\#\\{` into
   `#{`. The result is a control character in the file, or a LaTeX word with no
   backslash.
3. **An unescaped `$`.** A stray dollar (`$1000`, a shell snippet outside a code fence)
   opens a math span that runs on until the next `$`, dragging paragraphs of prose into
   math mode and taking any `#` in between with it.

    uv run python tools/check_docs.py            # whole repo
    uv run python tools/check_docs.py path.md    # specific files

Exits non-zero when anything is found, so it can gate a commit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_PARTS = {".lake", ".venv", ".git", "__pycache__", "target", "node_modules"}

# LaTeX control words that are meaningless without their backslash, so seeing one bare
# and directly followed by a brace or paren means an escape level went missing.
LATEX_WORDS = [
    "text", "sum", "prod", "frac", "tfrac", "dfrac", "approx", "lvert", "rvert",
    "operatorname", "Longrightarrow", "Rightarrow", "qquad", "quad", "cdot", "times",
    "le", "ge", "mathbb", "mathcal", "textstyle", "displaystyle",
]


def iter_docs(paths: list[str] | None) -> list[Path]:
    if paths:
        return [Path(p) for p in paths]
    return [p for p in sorted(REPO_ROOT.rglob("*.md"))
            if not any(part in SKIP_PARTS for part in p.parts)]


def math_spans(line: str) -> list[str]:
    """Math spans contained in a single line; display math must be alone on its line."""
    disp = re.fullmatch(r"\s*\$\$(.*)\$\$\s*", line)
    if disp:
        return [disp.group(1)]
    return re.findall(r"(?<!\\)\$([^$\n]+?)(?<!\\)\$", line)


def check(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return [f"{path}: unreadable ({e})"]

    for n, ch in enumerate(text):
        if ord(ch) < 32 and ch not in "\n\r\t":
            line = text[:n].count("\n") + 1
            problems.append(
                f"{path}:{line}: control character {ord(ch)} — a swallowed backslash "
                f"(e.g. \\text became TAB+ext)")
            break

    in_fence = False
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        # An odd count of unescaped dollars leaves a span open across the document.
        unescaped = len(re.findall(r"(?<!\\)\$", line.replace("$$", "")))
        if unescaped % 2 == 1:
            problems.append(
                f"{path}:{i}: odd number of unescaped '$' — escape a literal dollar as "
                f"\\$ or put it in a code span: {line.strip()[:70]}")

        for span in math_spans(line):
            if "#" in span:
                problems.append(
                    f"{path}:{i}: '#' inside math — KaTeX will refuse to render: "
                    f"{span.strip()[:70]}")
            for w in LATEX_WORDS:
                if re.search(r"(?<![\\A-Za-z])" + w + r"[{(]", span):
                    problems.append(
                        f"{path}:{i}: '{w}' without its backslash: {span.strip()[:70]}")
    return problems


def main(argv: list[str]) -> int:
    docs = iter_docs(argv or None)
    if not docs:
        print("no markdown files found")
        return 1
    problems: list[str] = []
    for d in docs:
        problems += check(d)
    if problems:
        print(f"{len(problems)} problem(s) found:")
        for p in problems:
            print("  " + p)
        return 1
    print(f"{len(docs)} markdown file(s) checked, no rendering problems found")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
