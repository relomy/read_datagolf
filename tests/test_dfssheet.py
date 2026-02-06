import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import dfssheet as dfssheet_module
from dfs_common import sheets as common_sheets


def test_sheet_write_values_delegates_to_client(monkeypatch):
    calls = {}

    def fake_write(self, values, cell_range, value_input_option="USER_ENTERED"):
        calls["values"] = values
        calls["range"] = cell_range
        calls["option"] = value_input_option

    monkeypatch.setattr(common_sheets.SheetClient, "write_values", fake_write)
    sheet = dfssheet_module.Sheet()

    sheet.write_values_to_sheet_range([["a"]], "A1")

    assert calls["range"] == "A1"
    assert calls["option"] == "USER_ENTERED"
