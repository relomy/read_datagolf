import json
import math
from types import SimpleNamespace

import pytest

import datagolf_api as api


class FakeResponse:
    def __init__(self, text, status_error=None):
        self.text = text
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error


class FakeSession:
    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        result = self._results[len(self.calls) - 1]
        if isinstance(result, Exception):
            raise result
        return result


def _ensure_requests(monkeypatch):
    if api.requests is None:
        monkeypatch.setattr(api, "requests", SimpleNamespace(Session=lambda: None))


def test_parse_jsonp_valid():
    assert api._parse_jsonp("cb({\"a\": 1})") == {"a": 1}


def test_parse_jsonp_invalid():
    with pytest.raises(ValueError):
        api._parse_jsonp("no parens")


def test_parse_json_or_jsonp_json():
    assert api._parse_json_or_jsonp("  {\"a\": 2} ") == {"a": 2}


def test_parse_json_or_jsonp_jsonp():
    assert api._parse_json_or_jsonp("cb([1, 2])") == [1, 2]


def test_request_jsonp_requires_requests(monkeypatch):
    monkeypatch.setattr(api, "requests", None)
    with pytest.raises(ModuleNotFoundError):
        api._request_jsonp("http://example.com")


def test_ensure_requests_sets_session(monkeypatch):
    monkeypatch.setattr(api, "requests", None)
    _ensure_requests(monkeypatch)
    assert api.requests is not None
    assert callable(api.requests.Session)


def test_request_jsonp_retries_and_backoff(monkeypatch):
    _ensure_requests(monkeypatch)
    session = FakeSession(
        [
            RuntimeError("boom"),
            RuntimeError("still boom"),
            FakeResponse("{\"ok\": true}"),
        ]
    )
    sleeps = []
    monkeypatch.setattr(api.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = api._request_jsonp(
        "http://example.com",
        session=session,
        retries=3,
        backoff=0.5,
    )

    assert result == {"ok": True}
    assert len(session.calls) == 3
    assert sleeps == [0.5, 1.0]


def test_request_jsonp_raises_last_error(monkeypatch):
    _ensure_requests(monkeypatch)
    session = FakeSession([RuntimeError("boom"), RuntimeError("still boom")])
    sleeps = []
    monkeypatch.setattr(api.time, "sleep", lambda seconds: sleeps.append(seconds))

    with pytest.raises(RuntimeError, match="still boom"):
        api._request_jsonp(
            "http://example.com",
            session=session,
            retries=2,
            backoff=0.25,
        )

    assert len(session.calls) == 2
    assert sleeps == [0.25]


def test_request_jsonp_handles_http_error(monkeypatch):
    _ensure_requests(monkeypatch)
    session = FakeSession(
        [
            FakeResponse("{\"ok\": true}", status_error=RuntimeError("http")),
            FakeResponse("{\"ok\": true}"),
        ]
    )
    sleeps = []
    monkeypatch.setattr(api.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = api._request_jsonp(
        "http://example.com",
        session=session,
        retries=2,
        backoff=0.1,
    )

    assert result == {"ok": True}
    assert len(session.calls) == 2
    assert sleeps == [0.1]


def test_fetch_main_data_url_selection(monkeypatch):
    seen = []

    def fake_request(url, **_kwargs):
        seen.append(url)
        return {"ok": True}

    monkeypatch.setattr(api, "_request_jsonp", fake_request)

    assert api.fetch_main_data() == {"ok": True}
    assert api.fetch_main_data(mode="full", tour="korn") == {"ok": True}

    assert seen == [
        f"{api.BASE_URL}/get-main-data/mini",
        f"{api.BASE_URL}/get-main-data/korn",
    ]


def test_fetch_player_data_empty_short_circuits(monkeypatch):
    monkeypatch.setattr(api, "_request_jsonp", lambda *_args, **_kwargs: None)
    assert api.fetch_player_data([]) == {}


def test_fetch_player_data_builds_params(monkeypatch):
    seen = {}

    def fake_request(url, params=None, **_kwargs):
        seen["url"] = url
        seen["params"] = params
        return {"ok": True}

    monkeypatch.setattr(api, "_request_jsonp", fake_request)

    players = ["Doe, John", "Roe, Jane"]
    assert api.fetch_player_data(players) == {"ok": True}

    assert seen["url"] == f"{api.BASE_URL}/get-player-data"
    assert json.loads(seen["params"]["players"]) == players


def test_extract_players_last_first_mini():
    data = {"pga": {"lb": [{"f": "Ann", "l": "A"}, {"f": "", "l": "B"}]}}
    assert api.extract_players_last_first(data, tour="pga") == ["A, Ann"]


def test_extract_players_last_first_full():
    data = {"main": [{"name": "Smith, Bob"}, {"name": ""}, {}]}
    assert api.extract_players_last_first(data) == ["Smith, Bob"]


def test_extract_players_last_first_non_dict():
    assert api.extract_players_last_first(["not", "a", "dict"]) == []


def test_build_players_dict_corrects_names_and_today(monkeypatch):
    main_data = {
        "main": [
            {
                "name": "Doe, John",
                "current_pos": "1",
                "current_score": -1,
                "thru": "5",
                "cut": 0.12,
            },
            {
                "name": "Roe, Jane",
                "current_pos": "2",
                "current_score": 0,
                "thru": 0,
                "teetime": "9:00",
                "cut": None,
            },
        ]
    }
    player_data = {"main": [{"name": "Doe, John", "today": -2}]}
    correct_names = {"JOHN DOE": "JOHN DOE JR"}

    players = api.build_players_dict(main_data, player_data, correct_names)

    assert sorted(players.keys()) == ["JANE ROE", "JOHN DOE JR"]
    assert players["JOHN DOE JR"]["today_score"] == "-2"
    assert players["JANE ROE"]["today_score"] == ""
    assert players["JANE ROE"]["thru_hole"] == "9:00"
    assert players["JOHN DOE JR"]["perc_make_cut"] == "12%"


def test_build_cutline_probs_formats_values():
    data = {"cuts": [{"Score": -1, "prob": 0.1}, {"Score": None, "prob": "50%"}]}
    assert api.build_cutline_probs(data) == [["-1", None, "10%"], ["", None, "50%"]]


def test_mode_is_mini():
    assert api.mode_is_mini({"pga": {"lb": []}}) is True
    assert api.mode_is_mini({"pga": {"lb": []}}, tour="korn") is False
    assert api.mode_is_mini({}) is False


def test_iter_player_rows_mini():
    data = {
        "pga": {
            "lb": [
                {"f": "A", "l": "B", "p": "T1", "s": "-3", "t": "F", "w": "50%"}
            ]
        }
    }
    rows = api._iter_player_rows(data)
    assert rows == [
        {
            "display_name": "A B",
            "last_first": "B, A",
            "place": "T1",
            "total_score": "-3",
            "thru_hole": "F",
            "perc_make_cut": "50%",
        }
    ]


def test_iter_player_rows_full_thru_and_teetime():
    data = {
        "main": [
            {
                "name": "Doe, John",
                "current_pos": "1",
                "current_score": 1,
                "thru": 0,
                "teetime": "9:00",
                "cut": 0.1,
            },
            {
                "name": "Roe, Jane",
                "current_pos": "2",
                "current_score": 0,
                "thru": 0,
                "teetime": "",
                "cut": 0.2,
            },
            {
                "name": "Poe, Joe",
                "current_pos": "3",
                "current_score": -2,
                "thru": 7,
                "cut": None,
            },
        ]
    }
    rows = api._iter_player_rows(data)
    assert rows[0]["thru_hole"] == "9:00"
    assert rows[1]["thru_hole"] == "-"
    assert rows[2]["thru_hole"] == 7
    assert rows[0]["total_score"] == "+1"
    assert rows[1]["total_score"] == "E"
    assert rows[2]["total_score"] == "-2"


def test_build_today_map_none():
    assert api._build_today_map(None) == {}


def test_build_today_map_main():
    data = {"main": [{"name": "A, B", "today": 0}]}
    assert api._build_today_map(data) == {"ab": "E"}


def test_build_today_map_dict_and_players():
    data = {
        "Someone, One": {"today_score": -1},
        "History Guy": [{"today": -2}, {"today": -3}],
        "meta": {"ignored": True},
        "players": {"Other, Two": {"score_today": 2}, "Skip": {}},
    }
    result = api._build_today_map(data)
    assert result["someoneone"] == "-1"
    assert result["historyguy"] == "-3"
    assert result["othertwo"] == "+2"


def test_build_today_map_list():
    data = [{"name": "A, B", "today": 1}, {"name": "", "today": 2}]
    assert api._build_today_map(data) == {"ab": "+1"}


def test_find_today_in_value_dict_and_list():
    assert api._find_today_in_value({"today": 2, "score_today": 3}) == 2
    assert (
        api._find_today_in_value([
            {"today": -1},
            {"current_today": 4},
        ])
        == 4
    )


def test_find_today_in_value_list_no_match():
    assert api._find_today_in_value([{"nope": 1}, {"also": 2}]) is None


def test_lookup_today():
    today_map = {"doejohn": "E"}
    assert api._lookup_today(today_map, "Doe, John", "John Doe") == "E"
    assert api._lookup_today(today_map, "Nope", "Nope") is None


def test_normalize_display_name():
    assert api._normalize_display_name("John  Doe (AM) -Smith") == "JOHN  DOE (AM) SMITH"


def test_last_first_to_display():
    assert api._last_first_to_display("Doe, John") == "John Doe"
    assert api._last_first_to_display("Single") == "Single"


def test_name_key():
    assert api._name_key("O'Neil, Jr.") == "oneiljr"


def test_format_percent():
    assert api._format_percent(None) == ""
    assert api._format_percent("50%") == "50%"
    assert api._format_percent("bad") == ""
    assert api._format_percent(0.1004) == "10%"
    assert api._format_percent(0.105) == "10.5%"


def test_format_score():
    assert api._format_score(None) == ""
    assert api._format_score("E") == "E"
    assert api._format_score(float("nan")) == ""
    assert api._format_score(0) == "E"
    assert api._format_score(1.0) == "+1"
    assert api._format_score(-2) == "-2"
    assert api._format_score(2.5) == "2.5"


def test_format_score_unparseable():
    assert api._format_score(object()) == ""
