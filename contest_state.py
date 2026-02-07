from __future__ import annotations

import os

from dfs_common import contests


def get_live_golf_contest():
    if not os.getenv("DFS_STATE_DIR"):
        return None
    try:
        return contests.get_live_contest(None, sport="GOLF")
    except RuntimeError:
        return None
