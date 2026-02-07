import json
import logging
import runpy
import sys
from types import SimpleNamespace

import pytest

import datagolf_api
import read_datagolf
import sheets_service


class FakeSheetService:
    def __init__(self, _repo, sport):
        self.sport = sport
        self.writes = []

    def get_players(self):
        return ["JOHN DOE", "JANE ROE"]

    def write_columns(self, start_col, end_col, values, start_row=2):
        self.writes.append((start_col, end_col, values, start_row))


def test_get_dg_ranks_empty_players():
    with pytest.raises(Exception, match="No data found"):
        read_datagolf.get_dg_ranks([], {})


def test_get_dg_ranks_exact_match():
    dict_players = {
        "JOHN DOE": {
            "place": "1",
            "total_score": "-1",
            "thru_hole": "F",
            "today_score": "-2",
            "perc_make_cut": "10%",
        }
    }
    values = read_datagolf.get_dg_ranks(["John Doe"], dict_players)
    assert values == [["1", "-1", "F", "-2", "10%"]]


def test_get_dg_ranks_auto_match(monkeypatch, caplog):
    dict_players = {
        "JOHN DOE": {
            "place": "1",
            "total_score": "-1",
            "thru_hole": "F",
            "today_score": "-2",
            "perc_make_cut": "10%",
        }
    }

    def fake_similarity(_player, candidate):
        return 0.9 if candidate == "JOHN DOE" else 0.1

    monkeypatch.setattr(read_datagolf, "jaro_winkler_similarity", fake_similarity)

    with caplog.at_level(logging.INFO):
        values = read_datagolf.get_dg_ranks(["Jon Doe"], dict_players)
    assert values == [["1", "-1", "F", "-2", "10%"]]
    assert any("auto-matched" in record.message for record in caplog.records)


def test_get_dg_ranks_no_match_prints_suggestions(monkeypatch, capsys):
    dict_players = {
        "KNOWN": {
            "place": "1",
            "total_score": "-1",
            "thru_hole": "F",
            "today_score": "-2",
            "perc_make_cut": "10%",
        }
    }

    def fake_similarity(_player, _candidate):
        return 0.85

    monkeypatch.setattr(read_datagolf, "jaro_winkler_similarity", fake_similarity)

    values = read_datagolf.get_dg_ranks(["Unknown"], dict_players)
    assert values == [["???", "", "", "", ""]]

    out = capsys.readouterr().out
    assert "UNKNOWN: ???" in out
    assert "Suggestions:" in out


def test_get_dg_ranks_exact_match_ignores_periods(monkeypatch, caplog):
    dict_players = {
        "JJ SPAUN": {
            "place": "1",
            "total_score": "-1",
            "thru_hole": "F",
            "today_score": "-2",
            "perc_make_cut": "10%",
        }
    }

    def fail_similarity(_player, _candidate):
        raise AssertionError("fuzzy similarity should not be called for normalized exact match")

    monkeypatch.setattr(read_datagolf, "jaro_winkler_similarity", fail_similarity)

    with caplog.at_level(logging.INFO):
        values = read_datagolf.get_dg_ranks(["J.J. SPAUN"], dict_players)
    assert values == [["1", "-1", "F", "-2", "10%"]]
    assert not any("auto-matched" in record.message for record in caplog.records)


def test_get_dg_ranks_no_match_logs_top_candidates(monkeypatch, caplog):
    dict_players = {
        "JONATHAN SPAUN": {
            "place": "1",
            "total_score": "-1",
            "thru_hole": "F",
            "today_score": "-2",
            "perc_make_cut": "10%",
        },
        "JOHN SMITH": {
            "place": "2",
            "total_score": "E",
            "thru_hole": "12",
            "today_score": "+1",
            "perc_make_cut": "50%",
        },
    }

    scores = {"JONATHAN SPAUN": 0.83, "JOHN SMITH": 0.10}

    def fake_similarity(_player, candidate):
        return scores[candidate]

    monkeypatch.setattr(read_datagolf, "jaro_winkler_similarity", fake_similarity)

    with caplog.at_level(logging.WARNING):
        values = read_datagolf.get_dg_ranks(["J.J. SPAUN"], dict_players)

    assert values == [["???", "", "", "", ""]]
    assert any(
        "unmatched; best candidate JONATHAN SPAUN scored 0.830" in record.message
        for record in caplog.records
    )


def test_parse_args_force_run():
    args = read_datagolf.parse_args(["--force-run"])
    assert args.force_run is True


def test_should_run_with_live_contest(monkeypatch):
    monkeypatch.setenv("DG_USE_CONTEST_STATE", "1")
    monkeypatch.setattr(read_datagolf, "get_live_golf_contest", lambda: object())
    assert read_datagolf.should_run(force_run=False) is True


def test_should_not_run_without_live_contest(monkeypatch):
    monkeypatch.setenv("DG_USE_CONTEST_STATE", "1")
    monkeypatch.setenv("DFS_STATE_DIR", "/tmp/dfs_state")
    monkeypatch.setattr(read_datagolf, "get_live_golf_contest", lambda: None)
    assert read_datagolf.should_run(force_run=False) is False


def test_should_run_skips_lookup_when_contest_state_disabled(monkeypatch):
    def _fail():
        raise AssertionError("contest lookup should not run")

    monkeypatch.delenv("DG_USE_CONTEST_STATE", raising=False)
    monkeypatch.delenv("DFS_STATE_DIR", raising=False)
    monkeypatch.setattr(read_datagolf, "get_live_golf_contest", _fail)
    assert read_datagolf.should_run(force_run=False) is True


def test_force_run_skips_lookup_logs(monkeypatch, caplog):
    def _fail():
        raise RuntimeError("boom")

    monkeypatch.setenv("DFS_STATE_DIR", "/tmp/dfs-state")
    monkeypatch.setattr(read_datagolf, "get_live_golf_contest", _fail)
    with caplog.at_level(logging.INFO):
        assert read_datagolf.should_run(force_run=True) is True
    assert "--force-run enabled" in caplog.text


def test_main_exits_without_live_contest(monkeypatch, caplog):
    monkeypatch.setattr(read_datagolf.logging.config, "fileConfig", lambda *args, **kwargs: None)
    monkeypatch.setenv("DG_USE_CONTEST_STATE", "1")
    monkeypatch.setenv("DFS_STATE_DIR", "/tmp/dfs_state")
    monkeypatch.setattr(read_datagolf, "get_live_golf_contest", lambda: None)

    def _boom(*_args, **_kwargs):
        raise AssertionError("fetch_main_data should not run")

    monkeypatch.setattr(read_datagolf, "fetch_main_data", _boom)
    with caplog.at_level(logging.INFO):
        read_datagolf.main([])
    assert "No live contests found; exiting." in caplog.text


def test_main_writes_data_and_saves_api(monkeypatch, tmp_path):
    full_data = {"full": "data"}
    dict_players = {"JOHN DOE": {"place": "1", "total_score": "-1", "thru_hole": "F", "today_score": "-2", "perc_make_cut": "10%"}}
    dg_ranks = [["1", "-1", "F", "-2", "10%"]]
    dg_probs = [["-1", None, "10%"]]

    monkeypatch.setenv("DG_SAVE_API", "1")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(read_datagolf.logging.config, "fileConfig", lambda *args, **kwargs: None)
    monkeypatch.setattr(read_datagolf, "fetch_main_data", lambda *args, **kwargs: full_data)
    monkeypatch.setattr(read_datagolf, "build_players_dict", lambda *args, **kwargs: dict_players)
    monkeypatch.setattr(read_datagolf, "get_dg_ranks", lambda *args, **kwargs: dg_ranks)
    monkeypatch.setattr(read_datagolf, "build_cutline_probs", lambda *args, **kwargs: dg_probs)
    monkeypatch.setattr(
        sheets_service,
        "build_dfs_sheet_service",
        lambda sport, **_kwargs: FakeSheetService(None, sport),
    )
    monkeypatch.setattr(
        read_datagolf,
        "build_dfs_sheet_service",
        lambda sport, **_kwargs: FakeSheetService(None, sport),
    )
    monkeypatch.setattr(read_datagolf, "strftime", lambda *_args, **_kwargs: "20240203_040506")

    read_datagolf.main(["--force-run"])

    saved = tmp_path / "datagolf_full_20240203_040506.json"
    assert saved.exists()
    assert json.loads(saved.read_text()) == full_data


def test_main_skips_empty_writes(monkeypatch):
    monkeypatch.setattr(read_datagolf.logging.config, "fileConfig", lambda *args, **kwargs: None)
    monkeypatch.setattr(read_datagolf, "fetch_main_data", lambda *args, **kwargs: {"full": "data"})
    monkeypatch.setattr(read_datagolf, "build_players_dict", lambda *args, **kwargs: {"JOHN DOE": {}})
    monkeypatch.setattr(read_datagolf, "get_dg_ranks", lambda *args, **kwargs: [])
    monkeypatch.setattr(read_datagolf, "build_cutline_probs", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        read_datagolf,
        "build_dfs_sheet_service",
        lambda sport, **_kwargs: FakeSheetService(None, sport),
    )

    read_datagolf.main(["--force-run"])


def test_main_block_runs(monkeypatch):
    monkeypatch.setenv("DG_SAVE_API", "0")
    monkeypatch.setattr(logging.config, "fileConfig", lambda *args, **kwargs: None)
    monkeypatch.setattr(sys, "argv", ["read_datagolf.py", "--force-run"])
    monkeypatch.setattr(datagolf_api, "fetch_main_data", lambda *args, **kwargs: {"full": "data"})
    monkeypatch.setattr(datagolf_api, "build_players_dict", lambda *args, **kwargs: {"JOHN DOE": {"place": "1", "total_score": "-1", "thru_hole": "F", "today_score": "-2", "perc_make_cut": "10%"}})
    monkeypatch.setattr(datagolf_api, "build_cutline_probs", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        sheets_service,
        "build_dfs_sheet_service",
        lambda sport, **_kwargs: FakeSheetService(None, sport),
    )

    runpy.run_path(str(read_datagolf.__file__), run_name="__main__")
