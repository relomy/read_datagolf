# Read Datagolf Sheets Refactor Design

**Date:** 2026-02-07

## Goal
Reduce duplication in the read_datagolf Sheets wrapper by using `dfs_common.sheets.SheetClient` directly, while preserving all existing sheet ranges, headers, and business logic.

## Non-Goals
- No changes to sheet ranges, header locations, or data outputs.
- No changes to partial vs exact sheet lookup behavior.
- No new dependencies.

## Current State
`DFSSheet` subclasses `Sheet` and relies on wrapper methods that mirror `SheetClient` operations (`write_values_to_sheet_range`, `clear_sheet_range`, `get_values_from_range`, `find_sheet_id`). Tests in this repo also verify those pass-through methods, duplicating coverage already in `dfs_common`.

## Proposed Architecture
- Keep `DFSSheet` as the public entrypoint and preserve its public methods and behaviors.
- Slim `Sheet` to be a constructor and owner of a single `SheetClient` instance, with a `service` property for test injection.
- `DFSSheet` calls `SheetClient` methods directly (`write_values`, `clear_range`, `get_values`, `find_sheet_id`) instead of relying on wrapper pass-throughs.
- Centralize spreadsheet ID resolution in one place in `Sheet.__init__`:
  - If `spreadsheet_id` is provided, use it.
  - Otherwise read `SPREADSHEET_ID` from environment; if unset, fall back to the existing hard-coded ID.
- Default credentials provider remains `service_account_provider("client_secret.json")`, but test injection of a fake `service` bypasses any Google client imports.

## Data Flow
`read_datagolf.main()` remains unchanged. `DFSSheet` still:
- Reads headers and values from the same ranges on initialization.
- Provides `get_players` from the "Name" column.
- Writes ranks and probabilities to the same ranges using the same value shapes.

## Error Handling
Error behavior is unchanged: missing credentials providers or missing client secrets still raise from `dfs_common.sheets` when service creation is attempted. Tests continue to inject a fake service to avoid real Google client usage.

## Testing Strategy
- Remove delegation-only tests in `read_datagolf/tests/test_dfssheet.py` that simply assert wrapper calls.
- Add/adjust repo-level tests to verify:
  - `DFSSheet` construction supports injected fake services.
  - Domain methods still target the same ranges and preserve outputs.
- Keep generic `SheetClient` behavior tests in `dfs_common` only.

## Implementation Notes
- Use small, local helper methods inside `DFSSheet` to reduce duplication and improve readability (pure helpers for ranges and value building).
- Maintain identical outputs from `build_values_for_vip_lineup` and related methods.
