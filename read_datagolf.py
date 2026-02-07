"""Read from DataGolf live model API and upload results to DFS spreadsheet."""

import argparse
import json
import logging
import logging.config
from os import getenv
from time import strftime
from typing import Iterable, Mapping

from jellyfish import jaro_winkler_similarity

from datagolf_api import build_cutline_probs, build_players_dict, fetch_main_data
from dfs_sheet_repository import DfsSheetRepository
from dfs_sheet_service import DfsSheetService
from sheets_service import make_sheet_client
from contest_state import get_live_golf_contest

logger = logging.getLogger(__name__)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-run",
        action="store_true",
        help="Run without live-contest gating",
    )
    return parser.parse_args(argv)


def should_run(*, force_run: bool) -> bool:
    if force_run:
        logger.info("--force-run enabled; skipping live-contest gating.")
        if getenv("DFS_STATE_DIR"):
            try:
                _ = get_live_golf_contest()
            except RuntimeError:
                logger.warning(
                    "DFS_STATE_DIR set but contest lookup failed; "
                    "continuing due to --force-run."
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
    normalized_keys = {k: k for k in dict_players}
    for player in players:
        # convert to uppercase and remove dash if there is one
        player = player.upper().replace("-", "")

        if player in dict_players:
            values.append(
                [
                    dict_players[player]["place"],
                    dict_players[player]["total_score"],
                    dict_players[player]["thru_hole"],
                    dict_players[player]["today_score"],
                    dict_players[player]["perc_make_cut"],
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
                logger.info(
                    "%s: auto-matched to %s (%.3f)",
                    player,
                    best_candidate,
                    best_score,
                )
                values.append(
                    [
                        dict_players[best_candidate]["place"],
                        dict_players[best_candidate]["total_score"],
                        dict_players[best_candidate]["thru_hole"],
                        dict_players[best_candidate]["today_score"],
                        dict_players[best_candidate]["perc_make_cut"],
                    ]
                )
            else:
                values.append(["???", "", "", "", ""])
                print(f"{player}: ???")
                close = [(c, s) for s, c in suggestions[:5] if s >= 0.85]
                if close:
                    print("  Suggestions:")
                    for name, score in close:
                        print(f"   - {name}: {score:.3f}")

    return values


def build_sheet_service(sport: str) -> DfsSheetService:
    client = make_sheet_client()
    repo = DfsSheetRepository(client)
    return DfsSheetService(repo, sport)


def main(argv=None) -> None:
    """Fetch live model data and write standings to the DFS sheet.

    TODO(read_datagolf.main): Confirm expected worksheet names and column layout
        for the DFS sheet beyond the hardcoded "GOLF" usage.
    """
    logging.config.fileConfig("logging.ini", disable_existing_loggers=False)
    args = parse_args(argv)
    if not should_run(force_run=args.force_run):
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
    if getenv("DG_SAVE_API", "").lower() in {"1", "true", "yes"}:
        ts = strftime("%Y%m%d_%H%M%S")
        path = f"datagolf_full_{ts}.json"
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(full_data, fp, ensure_ascii=False)
        logger.info("Saved API response to %s", path)
    dict_players = build_players_dict(full_data, full_data, correct_names)
    logger.info("Loaded %d players from API", len(dict_players))

    # create DFSsheet object
    sport = "GOLF"
    sheet = build_sheet_service(sport)
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


if __name__ == "__main__":
    main()
