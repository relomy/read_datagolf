import json

from read_datagolf.datagolf_api import build_players_dict


def main() -> None:
    """Verify fixture mappings for build_players_dict.

    TODO(test_fixtures.main): Document where `mini.json` and
        `player_data_sample.json` fixtures are sourced and add them to the repo
        if they are required for normal development workflows.
    """
    with open("mini.json", encoding="utf-8") as fp:
        mini = json.load(fp)
    with open("player_data_sample.json", encoding="utf-8") as fp:
        player_data = json.load(fp)

    players = build_players_dict(mini, player_data, correct_names={})

    expected = {
        "JUSTIN ROSE": ["1", "-17", "F", "-7", "61.3%"],
        "SEAMUS POWER": ["2", "-13", "F", "-6", "8.3%"],
        "MAX MCGREEVY": ["T3", "-11", "F", "-5", "4.1%"],
    }

    for name, values in expected.items():
        got = players.get(name)
        assert got is not None, f"Missing player {name}"
        row = [
            got["place"],
            got["total_score"],
            got["thru_hole"],
            got["today_score"],
            got["perc_make_cut"],
        ]
        assert row == values, f"Mismatch for {name}: {row} != {values}"

    print("fixture mapping ok")


if __name__ == "__main__":
    main()
