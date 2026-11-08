# Testing

## Repository Context

- Stack: Python
- Python: `>=3.13,<3.14`
- Package manager / runner: `uv`
- Source code: `src/`
- Tests: `tests/`
- Dependency groups: `test` is installed by default; `quality` contains Ruff,
  Ty, Xenon, and complexity-ratchet.
- Dependency: `dfs-common` from `relomy/dfs-common` (git dependency tracking
  `main`; see `pyproject.toml:[tool.uv.sources]`)

## Setup and Checks

Use these defaults unless blocked by an environment issue:

1. `uv sync`
2. `uv run pytest`
3. `scripts/check-quality.sh` — format check, lint, types, complexity floor, and
   the complexity ratchet against `origin/main`.

The README's `uv run --group quality ruff format .` command applies formatting
fixes. It is distinct from the format check inside `scripts/check-quality.sh`.

Before claiming completion, run relevant tests for touched functionality, the
mandatory pre-merge `scripts/check-quality.sh` gate with the same priority as
tests. Report failing checks with exact commands and failure summaries.

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
