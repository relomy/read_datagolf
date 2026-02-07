# Read Datagolf Sheets Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace `DFSSheet` with a repository + domain + service architecture that requires a `SheetClient` to be passed in directly, while preserving all ranges, headers, and business logic.

**Architecture:** Introduce a pure domain module for range/value helpers, a repository that wraps `SheetClient` IO, and a service that orchestrates domain logic + repository IO. Entry points construct `SheetClient` via a small `sheets_service` factory and use the new service.

**Tech Stack:** Python, pytest, dfs_common.sheets

---

### Task 1: Add domain helpers for ranges and value building

**Files:**
- Create: `dfs_sheet_domain.py`
- Test: `tests/test_dfs_sheet_domain.py`

**Step 1: Write the failing tests**

Create `tests/test_dfs_sheet_domain.py` with tests for:
- `end_col_for_sport("GOLF") == "E"` and non-golf returns `"H"`
- `data_range_for_sport("GOLF") == "GOLF!A2:E"`
- `header_range_for_sport("GOLF") == "GOLF!A1:E1"`
- `lineup_range_for_sport("GOLF") == "GOLF!L8:Z56"` (using the existing ranges)
- `build_values_for_vip_lineup` reproduces the existing golf/non-golf outputs (reuse `SimpleNamespace` as in current tests)

**Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/test_dfs_sheet_domain.py -v`
Expected: FAIL (module/functions missing)

**Step 3: Write minimal implementation**

Implement `dfs_sheet_domain.py`:
- `LINEUP_RANGES` copied exactly from current `dfssheet.py`
- `end_col_for_sport(sport: str) -> str`
- `data_range_for_sport(sport: str) -> str`
- `header_range_for_sport(sport: str) -> str`
- `lineup_range_for_sport(sport: str) -> str`
- `build_values_for_vip_lineup(sport: str, vip) -> list[list[Any]]` (logic identical to current)

**Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/test_dfs_sheet_domain.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add dfs_sheet_domain.py tests/test_dfs_sheet_domain.py
git commit -m "feat: add dfs sheet domain helpers"
```

---

### Task 2: Add repository + service and migrate DFSSheet behaviors

**Files:**
- Create: `dfs_sheet_repository.py`
- Create: `dfs_sheet_service.py`
- Modify: `read_datagolf.py`
- Test: `tests/test_dfs_sheet_service.py`

**Step 1: Write the failing tests**

Create `tests/test_dfs_sheet_service.py`:
- Build a `FakeService` (copy from current `tests/test_dfssheet.py`) and wrap in `SheetClient(service=FakeService(...))`.
- Construct `DfsSheetRepository(client)` and `DfsSheetService(repo, sport="GOLF")`.
- Assert methods call correct ranges:
  - `clear_standings()` clears `GOLF!A2:E`
  - `clear_lineups()` clears `GOLF!L8:Z56`
  - `write_columns("F", "J", values)` writes to `GOLF!F2:J`
  - `get_lineup_values()` reads `GOLF!L8:Z56`
  - `add_last_updated`, `add_contest_details`, `add_min_cash`, `add_non_cashing_info`, `add_train_info` write to the same ranges as before
- Verify `get_players()` returns names from the "Name" column using preloaded `values_by_range` for header + data

**Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/test_dfs_sheet_service.py -v`
Expected: FAIL (modules missing)

**Step 3: Write minimal implementation**

Implement:
- `dfs_sheet_repository.py` with `DfsSheetRepository(client)` and methods:
  - `read_range(cell_range)`
  - `write_range(values, cell_range)`
  - `clear_range(cell_range)`
- `dfs_sheet_service.py` with `DfsSheetService(repo, sport)` and methods mirroring current `DFSSheet` behaviors.
  - Use domain helpers for ranges and value building.
  - Preserve range strings exactly.
  - Keep `get_players()` logic identical (Name column lookup).
- Update `read_datagolf.py` to build a `SheetClient` via `sheets_service.make_sheet_client()` and then construct repo + service (replace `DFSSheet`).

**Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/test_dfs_sheet_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add dfs_sheet_repository.py dfs_sheet_service.py read_datagolf.py tests/test_dfs_sheet_service.py
git commit -m "feat: add dfs sheet repository and service"
```

---

### Task 3: Remove legacy DFSSheet and update tests

**Files:**
- Delete: `dfssheet.py`
- Modify: `tests/test_read_datagolf.py`
- Remove/replace: `tests/test_dfssheet.py`

**Step 1: Write the failing tests**

Update tests to import the new service and domain modules instead of `dfssheet`:
- Replace `tests/test_dfssheet.py` with targeted tests for service + domain (from Tasks 1/2).
- Update `tests/test_read_datagolf.py` to patch the new service entrypoints as needed.

**Step 2: Run tests to verify failures**

Run: `uv run --extra dev pytest -v`
Expected: FAIL due to removed `dfssheet` references

**Step 3: Implement minimal changes**

- Remove `dfssheet.py`.
- Update imports in `read_datagolf.py` and tests.
- Ensure all ranges/outputs match previous behavior.

**Step 4: Run full test suite**

Run: `uv run --extra dev pytest`
Expected: PASS

**Step 5: Commit**

```bash
git add read_datagolf.py tests dfssheet.py
git commit -m "refactor: replace DFSSheet with repository/service"
```

---

### Task 4: Final verification

**Files:**
- Test: `tests/`

**Step 1: Run full test suite**

Run: `uv run --extra dev pytest`
Expected: PASS

**Step 2: Commit (if needed)**

If any fixes were required:

```bash
git add dfs_sheet_repository.py dfs_sheet_service.py dfs_sheet_domain.py read_datagolf.py tests
git commit -m "fix: stabilize sheets service refactor"
```
