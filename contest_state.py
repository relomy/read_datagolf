from __future__ import annotations

import os
from pathlib import Path

from dfs_common import contests


def get_live_golf_contest():
    state_dir = os.getenv("DFS_STATE_DIR")
    if not state_dir:
        return None
    db_path = Path(state_dir) / "contests.db"
    try:
        contest = contests.get_live_contest(db_path, sport="GOLF")
    except Exception as exc:
        raise RuntimeError("Contest lookup failed") from exc
    if contest and contest.status == "LIVE":
        return contest
    return None
