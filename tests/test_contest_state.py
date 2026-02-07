from dfs_common import contests
import contest_state


def _row(dk_id: int):
    return {
        "dk_id": dk_id,
        "sport": "GOLF",
        "name": "Contest",
        "start_date": "2024-01-01 00:00:00",
        "draft_group": 1,
        "total_prizes": 1000,
        "entries": 200,
        "positions_paid": 100,
        "entry_fee": 25,
        "entry_count": 0,
        "max_entry_count": 1,
        "completed": 0,
        "status": "LIVE",
    }


def test_contest_state_returns_none_without_env(monkeypatch):
    monkeypatch.delenv("DFS_STATE_DIR", raising=False)
    assert contest_state.get_live_golf_contest() is None


def test_contest_state_reads_live_contest(tmp_path, monkeypatch):
    monkeypatch.setenv("DFS_STATE_DIR", str(tmp_path))
    db_path = tmp_path / "contests.db"
    contests.init_schema(db_path)
    contests.upsert_contests(db_path, [_row(99)])
    row = contest_state.get_live_golf_contest()
    assert row is not None
    assert row.dk_id == 99


def test_contest_state_uses_live_only(tmp_path, monkeypatch):
    monkeypatch.setenv("DFS_STATE_DIR", str(tmp_path))
    db_path = tmp_path / "contests.db"
    contests.init_schema(db_path)
    non_live = _row(101) | {"status": "COMPLETE"}
    contests.upsert_contests(db_path, [non_live])
    assert contest_state.get_live_golf_contest() is None
