"""Single place where the local Antigravity CLI (`agy -p`) is invoked.

Previously `call_agy_prompt` and the code extractor were copy-pasted into planner.py,
executor.py, summarizer.py and mutator.py, so a fix in one never reached the others.
"""

import logging
import re
import subprocess

logger = logging.getLogger(__name__)


class AgyError(RuntimeError):
    """The local LLM CLI failed, timed out, or is not installed."""


def call_agy_prompt(prompt: str, timeout_sec: float = 60.0) -> str:
    """Runs `agy -p <prompt>` and returns stdout.

    Raises AgyError instead of leaking CalledProcessError / FileNotFoundError /
    TimeoutExpired, so callers can treat "no LLM available" as one condition.
    """
    try:
        result = subprocess.run(
            ["agy", "-p", prompt],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout_sec,
        )
    except FileNotFoundError as exc:
        raise AgyError(
            "the `agy` CLI was not found on PATH; the LLM stages cannot run"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise AgyError(f"`agy -p` timed out after {timeout_sec}s") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise AgyError(f"`agy -p` exited {exc.returncode}: {stderr[:400]}") from exc
    return result.stdout.strip()


def extract_python_code(raw_output: str, expect_symbol: str = "def generate_graph") -> str:
    """Pulls a Python snippet out of an LLM reply.

    Tries a fenced ```python block, then any fenced block, then a bare function
    definition. Returns the raw text as a last resort so the caller's evaluator can
    produce the real syntax error rather than a silent empty candidate.
    """
    match = re.search(r"```python\s*\n(.*?)\n```", raw_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    match_any = re.search(r"```\s*\n(.*?)\n```", raw_output, re.DOTALL)
    if match_any:
        return match_any.group(1).strip()

    if expect_symbol in raw_output:
        lines = raw_output.splitlines()
        code_lines = []
        capturing = False
        for line in lines:
            if line.startswith(expect_symbol) or line.startswith("import ") or line.startswith("from "):
                capturing = True
            if capturing:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines).strip()

    return raw_output.strip()
