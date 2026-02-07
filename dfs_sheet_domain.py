"""Pure helpers for DFS sheet ranges and value formatting."""

from typing import Any, Protocol, Sequence

START_COL = "A"

LINEUP_RANGES = {
    "NBA": "J3:V61",
    "CFB": "J3:V61",
    "NFL": "J3:V66",
    "NFLShowdown": "J3:V66",
    "GOLF": "L8:Z56",
    "PGAMain": "L8:X56",
    "PGAWeekend": "L3:Q41",
    "PGAShowdown": "L3:Q41",
    "TEN": "J3:V61",
    "MLB": "J3:V71",
    "XFL": "J3:V56",
    "MMA": "J3:V61",
    "LOL": "J3:V61",
    "NAS": "J3:V61",
    "USFL": "J3:V66",
}


class _VipPlayer(Protocol):
    name: str
    salary: Any
    fpts: Any
    value: Any
    ownership: Any
    pos: str


class _Vip(Protocol):
    name: str
    pmr: Any
    lineup: Sequence[_VipPlayer]
    rank: Any
    pts: Any


def end_col_for_sport(sport: str) -> str:
    if "PGA" in sport or sport == "GOLF":
        return "E"
    return "H"


def data_range_for_sport(sport: str) -> str:
    end_col = end_col_for_sport(sport)
    return f"{sport}!{START_COL}2:{end_col}"


def header_range_for_sport(sport: str) -> str:
    end_col = end_col_for_sport(sport)
    return f"{sport}!{START_COL}1:{end_col}1"


def lineup_range_for_sport(sport: str) -> str:
    return f"{sport}!{LINEUP_RANGES[sport]}"


def build_values_for_vip_lineup(sport: str, vip: _Vip) -> list[list[Any]]:
    if "GOLF" in sport:
        values: list[list[Any]] = [[vip.name, None, "PMR", vip.pmr, None, None, None]]
        values.append(["Name", "Salary", "Pts", "Value", "Own", "Pos", "Score"])
        for player in vip.lineup:
            values.append(
                [
                    player.name,
                    player.salary,
                    player.fpts,
                    player.value,
                    player.ownership,
                    None,
                    None,
                ]
            )
        values.append(["rank", vip.rank, vip.pts, None, None, None, None])
    else:
        values = [[vip.name, None, "PMR", vip.pmr, None, None]]
        values.append(["Pos", "Name", "Salary", "Pts", "Value", "Own"])
        for player in vip.lineup:
            values.append(
                [
                    player.pos,
                    player.name,
                    player.salary,
                    player.fpts,
                    player.value,
                    player.ownership,
                ]
            )
        values.append(["rank", vip.rank, None, vip.pts, None, None])
    return values
