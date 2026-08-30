# read_datagolf

Read DataGolf live model data and upload results to a DFS spreadsheet.

## Tooling

- Setup: `uv sync`
- Format: `uv run ruff format .`
- Lint: `uv run ruff check .`
- Types: `uv run ty check`
- Tests: `uv run pytest`
- Complexity ratchet: `uv run complexity-ratchet --base origin/main --worktree`

## Entry Points

- Cron-safe wrapper: `read_datagolf.py`
- Internal CLI: `src/read_datagolf/cli/read_datagolf.py`

## Requirements

- Python `>=3.11,<3.12`
- `client_secret.json` at repo root for Google Sheets access
- Network access to DataGolf live model endpoint (`src/read_datagolf/datagolf_api.py`)

## Shared Infrastructure

- Google Sheets primitives are provided by `dfs_common`.
- `dfs-common` is installed as a git dependency tracking `main` (see
  `pyproject.toml:[tool.uv.sources]`); no sibling checkout is required.

## Configuration

- `DFS_STATE_DIR`: shared state directory containing `contests.db`.
- `DG_USE_CONTEST_STATE`: when truthy, gate runs on live GOLF contest state.
- `DG_SAVE_API`: when truthy, saves the full API payload to `datagolf_full_YYYYmmdd_HHMMSS.json`.
- `SPREADSHEET_ID`: optional override for target spreadsheet.
- `LOG_LEVEL`: logging level (defaults to `DEBUG`).

## Running

```bash
python read_datagolf.py
python read_datagolf.py --force-run
```
