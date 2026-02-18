"""Read from DataGolf live model API and upload results to DFS spreadsheet."""

from __future__ import annotations

import argparse
import json
import logging
import os
from os import getenv
from time import strftime
from typing import Iterable, Mapping

from dfs_common import config as common_config
from dfs_common import contests, state
from jellyfish import jaro_winkler_similarity

from read_datagolf import config as app_config
from read_datagolf import logging as app_logging
from read_datagolf.datagolf_api import build_cutline_probs, build_players_dict, fetch_main_data
from read_datagolf.sheets_service import build_dfs_sheet_service

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover

    def load_dotenv(*_args, **_kwargs):
        return False


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


def _normalize_player_name(name: str) -> str:
    return name.upper().replace("-", "").replace(".", "")


def _player_last_name(normalized_name: str) -> str:
    tokens = normalized_name.split()
    return tokens[-1] if tokens else ""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-run",
        action="store_true",
        help="Run without live-contest gating",
    )
    return parser.parse_args(argv)


def should_run(
    *,
    force_run: bool,
    settings: common_config.ReadDataGolfSettings | None = None,
) -> bool:
    cfg = settings or app_config.load_settings()
    use_contest_state = cfg.dg_use_contest_state
    has_state_dir = bool(cfg.dfs_state_dir or getenv("DFS_STATE_DIR"))

    if force_run:
        logger.info("--force-run enabled; skipping live-contest gating.")
        if use_contest_state and has_state_dir:
            try:
                _ = get_live_golf_contest()
            except RuntimeError:
                logger.warning(
                    "DFS_STATE_DIR set but contest lookup failed; continuing due to --force-run."
                )
        return True

    if not (use_contest_state and has_state_dir):
        logger.info(
            "Contest-state gating disabled (DG_USE_CONTEST_STATE/DFS_STATE_DIR not fully set); continuing."
        )
        return True

    try:
        return get_live_golf_contest() is not None
    except RuntimeError:
        logger.warning("DFS_STATE_DIR set but contest lookup failed; exiting.")
        return False


def get_dg_ranks(
    players: Iterable[str],
    dict_players: Mapping[str, Mapping[str, str]],
) -> list[list[str]]:
    """Compare DFS sheet player names against DataGolf stats.

    Args:
        players: Iterable of player names from the DFS sheet.
        dict_players: Mapping of normalized player names to DataGolf stats
            built by `datagolf_api.build_players_dict`.

    Returns:
        List of rows with [place, total_score, thru_hole, today_score,
        perc_make_cut] for each player in `players`. Unmatched rows are filled
        with placeholders.

    Notes:
        Uses Jaro-Winkler similarity to auto-match close names when the best
        score is > 0.85 (see `jellyfish.jaro_winkler_similarity`).
    """
    if not players:
        raise Exception("No data found.")

    values: list[list[str]] = []
    normalized_keys: dict[str, str] = {}
    for original_key in dict_players:
        normalized_key = _normalize_player_name(original_key)
        normalized_keys.setdefault(normalized_key, original_key)

    for player in players:
        # normalize punctuation so exact matches don't require fuzzy fallback
        player = _normalize_player_name(player)

        exact_key = normalized_keys.get(player)
        if exact_key is not None:
            values.append(
                [
                    dict_players[exact_key]["place"],
                    dict_players[exact_key]["total_score"],
                    dict_players[exact_key]["thru_hole"],
                    dict_players[exact_key]["today_score"],
                    dict_players[exact_key]["perc_make_cut"],
                ]
            )
        else:
            suggestions = []
            for candidate in normalized_keys:
                score = jaro_winkler_similarity(player, candidate)
                suggestions.append((score, candidate))
            suggestions.sort(reverse=True)
            best_score, best_candidate = suggestions[0] if suggestions else (0.0, None)
            if best_candidate and best_score > 0.85:
                matched_key = normalized_keys[best_candidate]
                logger.info(
                    "%s: auto-matched to %s (%.3f)",
                    player,
                    matched_key,
                    best_score,
                )
                values.append(
                    [
                        dict_players[matched_key]["place"],
                        dict_players[matched_key]["total_score"],
                        dict_players[matched_key]["thru_hole"],
                        dict_players[matched_key]["today_score"],
                        dict_players[matched_key]["perc_make_cut"],
                    ]
                )
            else:
                values.append(["???", "", "", "", ""])
                if best_candidate is not None:
                    best_candidate_name = normalized_keys[best_candidate]
                    logger.warning(
                        "%s unmatched; best candidate %s scored %.3f",
                        player,
                        best_candidate_name,
                        best_score,
                    )
                top_candidates = ", ".join(
                    f"{normalized_keys[candidate]} ({score:.3f})"
                    for score, candidate in suggestions[:3]
                )
                if top_candidates:
                    logger.warning("%s unmatched; top candidates: %s", player, top_candidates)
                last_name = _player_last_name(player)
                if last_name:
                    same_last = [
                        name
                        for name in normalized_keys.values()
                        if name.split() and name.split()[-1] == last_name
                    ]
                    if same_last:
                        logger.warning(
                            "%s unmatched; API contains last-name matches: %s",
                            player,
                            ", ".join(same_last[:5]),
                        )
                    else:
                        logger.warning(
                            "%s unmatched; API has no players with last name %s",
                            player,
                            last_name,
                        )
                close = [
                    (normalized_keys[candidate], score)
                    for score, candidate in suggestions[:5]
                    if score >= 0.85
                ]
                if close:
                    close_text = ", ".join(f"{name} ({score:.3f})" for name, score in close)
                    logger.warning(
                        "%s unmatched; suggestions above threshold: %s", player, close_text
                    )

    return values


def _apply_settings_to_env(settings: common_config.ReadDataGolfSettings) -> None:
    if settings.dfs_state_dir and not getenv("DFS_STATE_DIR"):
        os.environ["DFS_STATE_DIR"] = settings.dfs_state_dir
    if settings.spreadsheet_id and not getenv("SPREADSHEET_ID"):
        os.environ["SPREADSHEET_ID"] = settings.spreadsheet_id


def main(argv: list[str] | None = None) -> None:
    """Fetch live model data and write standings to the DFS sheet.

    TODO(read_datagolf.main): Confirm expected worksheet names and column layout
        for the DFS sheet beyond the hardcoded "GOLF" usage.
    """
    args = parse_args(argv)
    settings = app_config.load_settings()
    _apply_settings_to_env(settings)
    if not should_run(force_run=args.force_run, settings=settings):
        logger.info("No live contests found; exiting.")
        return
    correct_names = {
        "TED POTTER JR": "TED POTTER JR.",
        "BILLY HURLEY III": "BILLY HURLEY",
        "SAMUEL STEVENS": "SAM STEVENS",
        "MATTI SCHMID": "MATTIAS SCHMID",
        "S.H. KIM": "SEONGHYEON KIM",
    }

    # Fetch full data once; includes place/score/thru/today/cut for all players.
    logger.info("Fetching full live-model data for PGA")
    full_data = fetch_main_data(mode="full", tour="pga")
    if settings.dg_save_api:
        ts = strftime("%Y%m%d_%H%M%S")
        path = f"datagolf_full_{ts}.json"
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(full_data, fp, ensure_ascii=False)
        logger.info("Saved API response to %s", path)
    dict_players = build_players_dict(full_data, full_data, correct_names)
    logger.info("Loaded %d players from API", len(dict_players))

    # create DFSsheet object
    sport = "GOLF"
    sheet = build_dfs_sheet_service(sport)
    logger.info("Opened DFS sheet for sport=%s", sport)

    if getenv("DG_USE_CONTEST_STATE", "").lower() in {"1", "true", "yes"}:
        live = get_live_golf_contest()
        if live:
            sheet.add_contest_details(live.name, live.positions_paid)

    # get players from DFS sheet
    sheet_players = sheet.get_players()
    logger.info("Loaded %d players from DFS sheet", len(sheet_players))

    # look up players from sheet in dg dict and write to sheet
    logger.info("Getting DG ranks for %d players", len(dict_players))
    dg_ranks = get_dg_ranks(sheet_players, dict_players)
    if dg_ranks:
        logger.info("Writing %d player rows to sheet", len(dg_ranks))
        sheet.write_columns("F", "J", dg_ranks)

    # write datagolf probabilities to K/L
    dg_probs = build_cutline_probs(full_data)
    if dg_probs:
        logger.info("Writing %d cutline rows to sheet", len(dg_probs))
        sheet.write_columns("L", "N", dg_probs, start_row=4)


def run_cli(argv: list[str] | None = None) -> None:
    app_logging.configure_logging()
    load_dotenv()
    main(argv)


if __name__ == "__main__":
    run_cli()
