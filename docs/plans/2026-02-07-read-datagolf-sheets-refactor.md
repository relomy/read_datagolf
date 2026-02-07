# Read Datagolf Sheets Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor `read_datagolf` sheet wrappers to use `dfs_common.sheets.SheetClient` directly while preserving all ranges, headers, and behaviors.

**Architecture:** Keep `DFSSheet` as the public class. Slim `Sheet` to own a single `SheetClient` instance and a `service` property for test injection. Replace pass-through wrapper methods with direct `SheetClient` calls inside `DFSSheet` and add small local helpers to reduce duplication.

**Tech Stack:** Python, pytest, dfs_common.sheets

---

### Task 1: Normalize SheetClient construction in `Sheet`

**Files:**
- Modify: `dfssheet.py`
- Test: `tests/test_dfssheet.py`

**Step 1: Write the failing test**

Add a test to `tests/test_dfssheet.py` that constructs a `DFSSheet` using a fake service without touching Google libraries, for example:

```python
service = FakeService(values_by_range={"GOLF!A1:E1": [["Name"]], "GOLF!A2:E": [["Alice"]]})
sheet = dfssheet.DFSSheet("GOLF", service=service)
assert sheet.service is service
```

**Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/test_dfssheet.py::test_dfssheet_init_accepts_service -v`
Expected: FAIL because `DFSSheet`/`Sheet` does not accept a `service` argument yet.

**Step 3: Write minimal implementation**

Update `dfssheet.py`:
- `Sheet.__init__` signature to accept `spreadsheet_id: str | None = None`, `service: Any | None = None`, and optional `credentials_provider`.
- Add a private `_resolve_spreadsheet_id()` helper (module or `Sheet` method) that reads `SPREADSHEET_ID` once and falls back to the existing hard-coded ID.
- Initialize `SheetClient` with `service=service` when provided; otherwise pass `credentials_provider=service_account_provider("client_secret.json")`.
- Keep `service` property for test injection (setter should update the client service).

**Step 4: Run test to verify it passes**

Run: `uv run --extra dev pytest tests/test_dfssheet.py::test_dfssheet_init_accepts_service -v`
Expected: PASS

**Step 5: Commit**

```bash
git add dfssheet.py tests/test_dfssheet.py
git commit -m "refactor: inject sheet service in dfssheet"
```

---

### Task 2: Remove wrapper pass-throughs and use `SheetClient` directly

**Files:**
- Modify: `dfssheet.py`
- Test: `tests/test_dfssheet.py`

**Step 1: Write/adjust tests**

Remove delegation-only tests from `tests/test_dfssheet.py` (e.g., tests that only check `Sheet` forwarding to `SheetClient`), and ensure remaining tests validate ranges and outputs for `DFSSheet` domain methods.

**Step 2: Run tests to verify failures**

Run: `uv run --extra dev pytest tests/test_dfssheet.py -v`
Expected: FAIL due to removed wrapper methods or updated method calls.

**Step 3: Implement minimal refactor**

In `dfssheet.py`:
- Remove or stop using `find_sheet_id`, `write_values_to_sheet_range`, `clear_sheet_range`, `get_values_from_range` wrapper methods.
- Update `DFSSheet` to call `self._client.get_values`, `self._client.write_values`, and `self._client.clear_range` directly.
- Add small helpers for repeated range formatting (e.g., `_standings_range()`, `_lineups_range()`) to reduce duplication without changing outputs.

**Step 4: Run tests to verify passes**

Run: `uv run --extra dev pytest tests/test_dfssheet.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add dfssheet.py tests/test_dfssheet.py
git commit -m "refactor: use SheetClient directly in DFSSheet"
```

---

### Task 3: Full test suite and cleanup

**Files:**
- Test: `tests/`

**Step 1: Run full test suite**

Run: `uv run --extra dev pytest`
Expected: PASS

**Step 2: Commit (if needed)**

If changes were required to fix tests beyond Task 2:

```bash
git add dfssheet.py tests/test_dfssheet.py
git commit -m "test: adjust dfssheet tests after refactor"
```
