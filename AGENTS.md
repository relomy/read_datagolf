# AGENTS.md

## Scope
These instructions are self-contained for this repository.
Apply them for all work under `read_datagolf/`.

## Repository Context
- Stack: Python
- Python: `>=3.11,<3.12`
- Package manager / runner: `uv`
- Source code: `src/`
- Tests: `tests/`
- Dependency: `dfs-common` from `relomy/dfs-common` (git dependency tracking
  `main`; see `pyproject.toml:[tool.uv.sources]`)

## Working Style
- Make the smallest safe change that solves the request.
- Prefer editing existing code over adding new abstractions.
- Avoid unrelated refactors.
- Ask before changing behavior that affects external integrations.

## Preferred Commands (Enforced-Lite)
Use these defaults unless blocked by an environment issue:
1. `uv sync`
2. `uv run pytest`
3. `uv run ruff format --check .`
4. `uv run ruff check`
5. `uv run ty check`

## dfs-common dependency

`dfs-common` installs from `relomy/dfs-common` over git; no sibling checkout
is needed. `uv sync` installs whatever commit `uv.lock` has recorded — it does
not silently advance to newer `main` commits. To refresh:

```bash
uv lock --upgrade-package dfs-common
uv sync
uv run pytest
```

Commit the resulting `uv.lock` diff once the refreshed dependency has been
tested. Use `uv sync --locked` for verification that must fail on lockfile
drift instead of rewriting it (this is what CI runs).

For temporary local development against unpublished `dfs_common` changes,
`[tool.uv.sources]` can be swapped for an editable sibling path
(`{ path = "../dfs_common", editable = true }`) — revert it before committing.

## Change Boundaries
- Keep edits in this repository unless the user explicitly asks for cross-repo changes.
- If a fix appears to require changes in `dfs_common`, stop and ask first.

## Verification Before Completion
Before claiming completion:
1. Run relevant tests for touched functionality.
2. Mandatory pre-merge gate: run `uv run ruff format --check .` with the same priority as tests.
3. Run lint and type checks relevant to touched files.
4. Report any failing checks with exact commands and failure summaries.

## Commit Message Style
- Required format: `type(scope): short summary`
- Use lowercase `type` (`feat`, `fix`, `test`, `docs`, `chore`, etc.)
- Keep summary imperative and concise.
- Non-conforming commit messages are not allowed.

## Output Expectations
In the final response, include:
1. What changed (files and behavior).
2. What commands were run.
3. What passed or failed.
4. Any follow-up risk or next step, if applicable.
