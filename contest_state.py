from __future__ import annotations

import logging

from dfs_common import contests, state

logger = logging.getLogger(__name__)


def get_live_golf_contest():
    try:
        db_path = state.contests_db_path()
    except RuntimeError:
        logger.debug("DFS_STATE_DIR is not configured; skipping contest lookup.")
        return None

    try:
        contest = contests.get_live_contest(db_path, sport="GOLF")
    except Exception as exc:
        raise RuntimeError("Contest lookup failed") from exc

    if contest and contest.status == "LIVE":
        return contest
    return None
