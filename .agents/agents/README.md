# Subagents

Four roles worth delegating, each one a job this repository has already got wrong once:

| Agent | Exists because |
| :--- | :--- |
| [`literature-scout`](./literature-scout.md) | A GPU campaign swept n = 32…52 for Erdős #64 before anyone read that f(4) ≥ 54 made every one of those orders provably empty. |
| [`claim-auditor`](./claim-auditor.md) | The published candidate table was once an instrumentation artifact: a capped counter and a short-circuiting verifier that serialized "not checked" as `false`. |
| [`lean-prover`](./lean-prover.md) | An unsound `DecidablePred` instance was written here to close a goal, and had to be removed. |
| [`candidate-screener`](./candidate-screener.md) | Every problem this repository has picked badly was picked without one. It rejected 18 of 20 candidates in the first pass, three times because the scout's own objective was mathematically wrong. |

The format follows Antigravity's documented convention
(<https://antigravity.google/docs/subagents/>): one Markdown file per agent with YAML
frontmatter, discovered from `.agents/agents/<name>.md` at workspace scope. Fields used
here are `name`, `description`, `tools`, `model`, `commandExecutionPolicy`, `subagent`,
`mainAgent` and `skills`.

## What is verified and what is not

`agy` 1.1.28 **does** pick up this repository's skill from `.agents/skills/` with no
configuration — confirmed by asking it to list its available skills, which returns
`neuro-symbolic-math`.

Discovery of these agent files is **not** confirmed. On this install, `agy agents` prints
nothing, and a headless `agy --print` session reports no custom subagents, with the files
in place at `.agents/agents/`, `.gemini/agents/` and `.agy/agents/`. `agy agents` also
lists nothing for an installed plugin that ships agent definitions, so the subcommand may
not report what the docs describe, or subagents may only resolve in an interactive
session. Treat these files as specifications of the roles, useful to any agent runner,
rather than as a wired-up feature.

`candidate-screener` has been run in anger, via `agy --print` with the prompt form in
[`tools/intake/screening-prompt.txt`](../../tools/intake/screening-prompt.txt); its results
are in [`problems/CANDIDATES.md`](../../problems/CANDIDATES.md). The other three have not
been exercised as subagents.

They are written to be read by a person too. Nothing here depends on them.
