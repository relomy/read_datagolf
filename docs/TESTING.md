# Testing

## Repository Context

- Stack: Python
- Python: `>=3.11,<3.12`
- Package manager / runner: `uv`
- Source code: `src/`
- Tests: `tests/`
- Dependency groups: `test` is installed by default; `quality` contains Ruff,
  Ty, Xenon, and complexity-ratchet.
- Complexity floor: `uv run --group quality xenon --max-absolute C src`
- Complexity ratchet: `uv run --group quality complexity-ratchet --base origin/main --worktree`
- Dependency: `dfs-common` from `relomy/dfs-common` (git dependency tracking
  `main`; see `pyproject.toml:[tool.uv.sources]`)

## Setup and Checks

Use these defaults unless blocked by an environment issue:

1. `uv sync`
2. `uv run pytest`
3. `uv run --group quality ruff format --check .`
4. `uv run --group quality ruff check`
5. `uv run --group quality ty check`

The README's `uv run --group quality ruff format .` command applies formatting
fixes. It is distinct from the mandatory `ruff format --check .` completion
gate above.

Before claiming completion, run relevant tests for touched functionality, the
mandatory pre-merge `uv run ruff format --check .` gate with the same priority
as tests, and lint and type checks relevant to touched files. Report failing
checks with exact commands and failure summaries.

## dfs-common Dependency

`dfs-common` installs from `relomy/dfs-common` over git; no sibling checkout
is needed. This requires non-interactive GitHub read access to the private
repo: a git credential helper for local dev (e.g. `gh auth login`), the
session's repo scope for Claude/Codex cloud sessions, and the
`DFS_COMMON_CHECKOUT_TOKEN` secret (rewritten into a git `insteadOf` URL) for
CI — see `.github/workflows/ci.yml`.

`uv sync` installs whatever commit `uv.lock` has recorded — it does not
silently advance to newer `main` commits. To refresh:

```bash
uv lock --upgrade-package dfs-common
uv sync
uv run pytest
```

Commit the resulting `uv.lock` diff once the refreshed dependency has been
tested. Use `uv sync --locked` (or `uv run --locked ...`) for verification
that must fail on lockfile drift instead of rewriting it (this is what CI
runs).

For temporary local development against unpublished `dfs_common` changes,
`[tool.uv.sources]` can be swapped for an editable sibling path
(`{ path = "../dfs_common", editable = true }`) — revert it before committing.
