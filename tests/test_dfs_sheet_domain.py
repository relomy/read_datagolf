from types import SimpleNamespace

from read_datagolf.dfs_sheet_domain import (
    build_values_for_vip_lineup,
    data_range_for_sport,
    end_col_for_sport,
    header_range_for_sport,
    lineup_range_for_sport,
)


def test_end_col_for_sport_golf_and_other():
    assert end_col_for_sport("GOLF") == "E"
    assert end_col_for_sport("PGAMain") == "E"
    assert end_col_for_sport("NBA") == "H"


def test_ranges_for_sport():
    assert data_range_for_sport("GOLF") == "GOLF!A2:E"
    assert header_range_for_sport("GOLF") == "GOLF!A1:E1"
    assert lineup_range_for_sport("GOLF") == "GOLF!L8:Z56"


def test_build_values_for_vip_lineup_golf_and_other():
    player = SimpleNamespace(
        name="P1",
        salary=100,
        fpts=10,
        value=1.0,
        ownership=0.1,
        pos="G",
    )
    vip = SimpleNamespace(name="VIP", pmr=1.2, lineup=[player], rank=1, pts=50)

    golf_values = build_values_for_vip_lineup("GOLF", vip)
    nba_values = build_values_for_vip_lineup("NBA", vip)

    assert golf_values[0][:4] == ["VIP", None, "PMR", 1.2]
    assert golf_values[1][0] == "Name"
    assert golf_values[-1][0] == "rank"

    assert nba_values[0][:4] == ["VIP", None, "PMR", 1.2]
    assert nba_values[1][0] == "Pos"
    assert nba_values[-1][0] == "rank"
