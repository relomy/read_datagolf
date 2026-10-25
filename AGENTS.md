# AGENTS.md

## Scope
These instructions are self-contained for this repository.
Apply them for all work under `read_datagolf/`.

## Testing
For environment setup, dependency procedures, repository check commands, and
verification before completion, read [`docs/TESTING.md`](docs/TESTING.md).

## Working Style
- Make the smallest safe change that solves the request.
- Prefer editing existing code over adding new abstractions.
- Avoid unrelated refactors.
- Ask before changing behavior that affects external integrations.

## Change Boundaries
- Keep edits in this repository unless the user explicitly asks for cross-repo changes.
- If a fix appears to require changes in `dfs_common`, stop and ask first.

## Workflow
For commit message and handoff requirements, and when a task calls for branch,
PR, review, or merge work, read [`docs/WORKFLOW.md`](docs/WORKFLOW.md).
