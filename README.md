# read_datagolf

Read DataGolf live model data and upload results to a DFS spreadsheet.

## Entry Point

- `read_datagolf.py` orchestrates fetching live model data and writing results
  to the DFS sheet. See `read_datagolf.py:main`.

## Requirements

- Python >=3.8 (see `pyproject.toml:[project].requires-python`).
- A Google service account credentials JSON at `client_secret.json`
  (see `dfssheet.py:Sheet.setup_service`).
- Logging configuration at `logging.ini`
  (see `read_datagolf.py:main` and `dfssheet.py` module import).
- Network access to the DataGolf live model endpoint configured in
  `datagolf_api.py:BASE_URL`.
- A target spreadsheet ID is hardcoded in `dfssheet.py:Sheet.__init__`.

## Configuration

- `DG_SAVE_API`: when set to a truthy value (`1`, `true`, or `yes`), saves the
  full API response to `datagolf_full_YYYYmmdd_HHMMSS.json`
  (see `read_datagolf.py:main`).
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
