import builtins
import io
import runpy

import read_datagolf.datagolf_api as datagolf_api
import read_datagolf.test_fixtures as test_fixtures


def _fake_open(*_args, **_kwargs):
    return io.StringIO("{}")


def _expected_player_dict():
    return {
        "JUSTIN ROSE": {
            "place": "1",
            "total_score": "-17",
            "thru_hole": "F",
            "today_score": "-7",
            "perc_make_cut": "61.3%",
        },
        "SEAMUS POWER": {
            "place": "2",
            "total_score": "-13",
            "thru_hole": "F",
            "today_score": "-6",
            "perc_make_cut": "8.3%",
        },
        "MAX MCGREEVY": {
            "place": "T3",
            "total_score": "-11",
            "thru_hole": "F",
            "today_score": "-5",
            "perc_make_cut": "4.1%",
        },
    }


def test_main_runs_with_patched_fixtures(monkeypatch):
    monkeypatch.setattr(builtins, "open", _fake_open)
    monkeypatch.setattr(
        test_fixtures, "build_players_dict", lambda *_args, **_kwargs: _expected_player_dict()
    )

    test_fixtures.main()


def test_module_main_block(monkeypatch):
    monkeypatch.setattr(builtins, "open", _fake_open)
    monkeypatch.setattr(
        datagolf_api, "build_players_dict", lambda *_args, **_kwargs: _expected_player_dict()
    )

    runpy.run_path(str(test_fixtures.__file__), run_name="__main__")
