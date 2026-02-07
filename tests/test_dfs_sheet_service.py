from __future__ import annotations

from datetime import datetime

from dfs_common.sheets import SheetClient

from dfs_sheet_repository import DfsSheetRepository
from dfs_sheet_service import DfsSheetService


class FakeService:
    def __init__(self, values_by_range=None, sheets_metadata=None):
        self.values_by_range = values_by_range or {}
        self.sheets_metadata = sheets_metadata or []
        self.updated = []
        self.cleared = []
        self._action = None
        self._range = None
        self._body = None

    def spreadsheets(self):
        return self

    def values(self):
        return self

    def get(self, spreadsheetId=None, range=None):
        self._action = "get"
        self._range = range
        return self

    def update(self, spreadsheetId=None, range=None, valueInputOption=None, body=None):
        self._action = "update"
        self._range = range
        self._body = body
        return self

    def clear(self, spreadsheetId=None, range=None, body=None):
        self._action = "clear"
        self._range = range
        return self

    def execute(self):
        if self._action == "get":
            if self._range is None:
                return {"sheets": self.sheets_metadata}
            return {"values": self.values_by_range.get(self._range, [])}
        if self._action == "update":
            self.updated.append((self._range, self._body))
            updated_cells = sum(len(row) for row in (self._body or {}).get("values", []))
            return {"updatedCells": updated_cells}
        if self._action == "clear":
            self.cleared.append(self._range)
            return {"clearedRange": self._range}
        raise AssertionError("Unexpected action")


def _make_service(sport, values_by_range=None):
    service = FakeService(values_by_range=values_by_range)
    client = SheetClient(spreadsheet_id="abc", service=service)
    repo = DfsSheetRepository(client)
    return DfsSheetService(repo, sport), service


def test_service_init_and_get_players():
    values_by_range = {
        "GOLF!A1:E1": [["Name", "Other"]],
        "GOLF!A2:E": [["Alice", "x"], ["Bob", "y"]],
    }
    sheet, _service = _make_service("GOLF", values_by_range=values_by_range)

    assert sheet.get_players() == ["Alice", "Bob"]


def test_service_clear_and_write_methods():
    values_by_range = {
        "GOLF!A1:E1": [["Name"]],
        "GOLF!A2:E": [["Alice"]],
    }
    sheet, service = _make_service("GOLF", values_by_range=values_by_range)

    sheet.clear_standings()
    sheet.clear_lineups()
    sheet.write_players([["A"]])
    sheet.write_column("F", [["B"]])
    sheet.write_columns("F", "J", [["C", "D", "E", "F", "G"]])
    sheet.write_lineup_range([["X"]])

    assert service.cleared == ["GOLF!A2:E", "GOLF!L8:Z56"]
    assert service.updated[0][0] == "GOLF!A2:E"
    assert service.updated[1][0] == "GOLF!F2:F"
    assert service.updated[2][0] == "GOLF!F2:J"
    assert service.updated[3][0] == "GOLF!L8:Z56"


def test_service_header_writes():
    values_by_range = {
        "GOLF!A1:E1": [["Name"]],
        "GOLF!A2:E": [["Alice"]],
    }
    sheet, service = _make_service("GOLF", values_by_range=values_by_range)

    sheet.add_last_updated(datetime(2024, 1, 2, 3, 4, 5))
    sheet.add_contest_details("Contest", 10)
    sheet.add_min_cash(5)
    sheet.add_non_cashing_info([["A", "B"]])
    sheet.add_train_info([["C", "D"]])

    ranges = [call[0] for call in service.updated]
    assert "GOLF!L1:Q1" in ranges
    assert "GOLF!X1:Y1" in ranges
    assert "GOLF!W1:W1" in ranges
    assert "GOLF!X3:Y16" in ranges
    assert "GOLF!AA3:AM10" in ranges


def test_get_lineup_values():
    values_by_range = {
        "GOLF!A1:E1": [["Name"]],
        "GOLF!A2:E": [["Alice"]],
        "GOLF!L8:Z56": [["L1"]],
    }
    sheet, _service = _make_service("GOLF", values_by_range=values_by_range)

    assert sheet.get_lineup_values() == [["L1"]]
