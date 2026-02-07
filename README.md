# read_datagolf

Read DataGolf live model data and upload results to a DFS spreadsheet.

## Entry Point

- `read_datagolf.py` orchestrates fetching live model data and writing results
  to the DFS sheet. See `read_datagolf.py:main`.

## Requirements

- Python >=3.9 (see `pyproject.toml:[project].requires-python`).
- A Google service account credentials JSON at `client_secret.json`
  (see `dfssheet.py:Sheet.setup_service`).
- Logging configuration at `logging.ini`
  (see `read_datagolf.py:main` and `dfssheet.py` module import).
- Network access to the DataGolf live model endpoint configured in
  `datagolf_api.py:BASE_URL`.
- A target spreadsheet ID is hardcoded in `dfssheet.py:Sheet.__init__`.

## Shared Infrastructure

- Google Sheets primitives are provided by `dfs_common`.
- Local development expects `dfs_common` as a sibling directory (see `pyproject.toml:[tool.uv.sources]`).

## Configuration

- `DG_SAVE_API`: when set to a truthy value (`1`, `true`, or `yes`), saves the
  full API response to `datagolf_full_YYYYmmdd_HHMMSS.json`
  (see `read_datagolf.py:main`).
- `DG_USE_CONTEST_STATE`: when set to a truthy value, attempts to read the
  current live GOLF contest from the shared contest state and writes contest
  details to the sheet header (`read_datagolf.py:main`, `contest_state.py`).
- `DFS_STATE_DIR`: required when `DG_USE_CONTEST_STATE` is enabled; points to
  the shared state directory containing `contests.sqlite`.
- Name normalization overrides are defined in the `correct_names` mapping in
  `read_datagolf.py:main`.

## Running

- From the repository root, run:

```bash
python read_datagolf.py
```

## Output/Side Effects

- Reads player names from the `"Name"` column in the worksheet named by
  `sport` (currently `"GOLF"` in `read_datagolf.py:main`) via
  `dfssheet.DFSSheet.get_players`.
- Writes DataGolf rank/score columns to `F:J` and cutline probabilities to
  `L:N` (starting at row 4) for the same worksheet
  (see `read_datagolf.py:main` and `dfssheet.DFSSheet.write_columns`).
