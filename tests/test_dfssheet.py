import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import dfssheet as dfssheet_module


def test_sheet_write_values_delegates_to_client(monkeypatch):
    calls = {}

    class _Client:
        def write_values(self, values, cell_range, value_input_option="USER_ENTERED"):
            calls["values"] = values
            calls["range"] = cell_range
            calls["option"] = value_input_option

    class _Service:
        def spreadsheets(self):
            raise AssertionError("service should not be used directly")

    monkeypatch.setattr(dfssheet_module.Sheet, "setup_service", lambda self: None)
    sheet = dfssheet_module.Sheet()
    sheet._client = _Client()
    sheet.service = _Service()

    sheet.write_values_to_sheet_range([["a"]], "A1")

    assert calls["range"] == "A1"
    assert calls["option"] == "USER_ENTERED"
