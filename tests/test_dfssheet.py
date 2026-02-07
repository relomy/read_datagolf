from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import dfssheet
import pytest


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


def _make_dfssheet(monkeypatch, sport, values_by_range=None, sheets_metadata=None):
    service = FakeService(values_by_range=values_by_range, sheets_metadata=sheets_metadata)
    monkeypatch.setattr(
        dfssheet, "service_account_provider", lambda *args, **kwargs: (lambda: service)
    )
    return dfssheet.DFSSheet(sport), service


def test_fake_service_execute_unexpected_action():
    service = FakeService()
    with pytest.raises(AssertionError, match="Unexpected action"):
        service.execute()


def test_sheet_find_sheet_id():
    service = FakeService(
        sheets_metadata=[
            {"properties": {"title": "GOLF", "sheetId": 123}},
            {"properties": {"title": "NBA", "sheetId": 456}},
        ]
    )
    sheet = dfssheet.Sheet()
    sheet.service = service

    assert sheet.find_sheet_id("GOLF") == 123
    assert sheet.find_sheet_id("MLB") is None


def test_sheet_write_clear_and_get():
    service = FakeService(values_by_range={"GOLF!A1:B1": [["a", "b"]]})
    sheet = dfssheet.Sheet()
    sheet.service = service

    sheet.write_values_to_sheet_range([[1, 2]], "GOLF!A1:B1")
    sheet.clear_sheet_range("GOLF!A2:B2")
    assert sheet.get_values_from_range("GOLF!A1:B1") == [["a", "b"]]

    assert service.updated[0][0] == "GOLF!A1:B1"
    assert service.cleared == ["GOLF!A2:B2"]


def test_dfssheet_init_ranges_and_players(monkeypatch):
    values_by_range = {
        "GOLF!A1:E1": [["Name", "Other"]],
        "GOLF!A2:E": [["Alice", "x"], ["Bob", "y"]],
    }
    sheet, _service = _make_dfssheet(monkeypatch, "GOLF", values_by_range=values_by_range)

    assert sheet.end_col == "E"
    assert sheet.get_players() == ["Alice", "Bob"]


def test_dfssheet_init_non_golf_end_col(monkeypatch):
    values_by_range = {
        "NBA!A1:H1": [["Name", "Other"]],
        "NBA!A2:H": [["A", "x"]],
    }
    sheet, _service = _make_dfssheet(monkeypatch, "NBA", values_by_range=values_by_range)

    assert sheet.end_col == "H"


def test_dfssheet_clear_and_write_methods(monkeypatch):
    values_by_range = {
        "GOLF!A1:E1": [["Name"]],
        "GOLF!A2:E": [["Alice"]],
    }
    sheet, service = _make_dfssheet(monkeypatch, "GOLF", values_by_range=values_by_range)

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


def test_dfssheet_header_writes(monkeypatch):
    values_by_range = {
        "GOLF!A1:E1": [["Name"]],
        "GOLF!A2:E": [["Alice"]],
    }
    sheet, service = _make_dfssheet(monkeypatch, "GOLF", values_by_range=values_by_range)

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


def test_build_values_for_vip_lineup_golf_and_other(monkeypatch):
    values_by_range = {
        "GOLF!A1:E1": [["Name"]],
        "GOLF!A2:E": [["Alice"]],
        "NBA!A1:H1": [["Name"]],
        "NBA!A2:H": [["Alice"]],
    }
    golf_sheet, _ = _make_dfssheet(monkeypatch, "GOLF", values_by_range=values_by_range)
    nba_sheet, _ = _make_dfssheet(monkeypatch, "NBA", values_by_range=values_by_range)

    player = SimpleNamespace(name="P1", salary=100, fpts=10, value=1.0, ownership=0.1, pos="G")
    vip = SimpleNamespace(name="VIP", pmr=1.2, lineup=[player], rank=1, pts=50)

    golf_values = golf_sheet.build_values_for_vip_lineup(vip)
    nba_values = nba_sheet.build_values_for_vip_lineup(vip)

    assert golf_values[0][:4] == ["VIP", None, "PMR", 1.2]
    assert golf_values[1][0] == "Name"
    assert golf_values[-1][0] == "rank"

    assert nba_values[0][:4] == ["VIP", None, "PMR", 1.2]
    assert nba_values[1][0] == "Pos"
    assert nba_values[-1][0] == "rank"


def test_write_vip_lineups_splits_after_five(monkeypatch):
    values_by_range = {
        "NBA!A1:H1": [["Name"]],
        "NBA!A2:H": [["Alice"]],
    }
    sheet, service = _make_dfssheet(monkeypatch, "NBA", values_by_range=values_by_range)

    players = [
        SimpleNamespace(name="P1", salary=1, fpts=2, value=3, ownership=4, pos="G"),
        SimpleNamespace(name="P2", salary=1, fpts=2, value=3, ownership=4, pos="F"),
    ]

    vips = [
        SimpleNamespace(name="vipZ", pmr=1, lineup=list(players), rank=1, pts=10),
        SimpleNamespace(name="vipA", pmr=1, lineup=list(players), rank=1, pts=10),
        SimpleNamespace(name="vipM", pmr=1, lineup=list(players), rank=1, pts=10),
        SimpleNamespace(name="vipB", pmr=1, lineup=list(players), rank=1, pts=10),
        SimpleNamespace(name="vipC", pmr=1, lineup=list(players), rank=1, pts=10),
        SimpleNamespace(name="vipD", pmr=1, lineup=list(players), rank=1, pts=10),
    ]

    sheet.write_vip_lineups(vips)

    assert service.updated[0][0] == "NBA!J3:V61"
    written = service.updated[0][1]["values"]
    assert written[0][0] == "vipA"
    expected_rows = 5 * (len(players) + 4)
    assert len(written) == expected_rows


def test_get_lineup_values(monkeypatch):
    values_by_range = {
        "GOLF!A1:E1": [["Name"]],
        "GOLF!A2:E": [["Alice"]],
        "GOLF!L8:Z56": [["L1"]],
    }
    sheet, _service = _make_dfssheet(monkeypatch, "GOLF", values_by_range=values_by_range)

    assert sheet.get_lineup_values() == [["L1"]]
