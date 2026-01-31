"""Read from DataGolf live model API and upload results to DFS spreadsheet."""

from datagolf_api import build_cutline_probs, build_players_dict, fetch_main_data
from dfssheet import DFSSheet
from jellyfish import jaro_winkler_similarity


def get_dg_ranks(players, dict_players):
    """Compare players from the DFS sheet with datagolf stats dictionary."""
    if not players:
        raise Exception("No data found.")

    values = []
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
                print(f"{player}: auto-matched to {best_candidate} ({best_score:.3f})")
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


def main():
    """Proceed."""
    correct_names = {
        "TED POTTER JR": "TED POTTER JR.",
        "BILLY HURLEY III": "BILLY HURLEY",
        "SAMUEL STEVENS": "SAM STEVENS",
        "MATTI SCHMID": "MATTIAS SCHMID",
    }

    # Fetch full data once; includes place/score/thru/today/cut for all players.
    full_data = fetch_main_data(mode="full", tour="pga")
    dict_players = build_players_dict(full_data, full_data, correct_names)

    # create DFSsheet object
    sport = "GOLF"
    sheet = DFSSheet(sport)

    # get players from DFS sheet
    sheet_players = sheet.get_players()

    # look up players from sheet in dg dict and write to sheet
    print(f"getting dg ranks for {len(dict_players)} players")
    dg_ranks = get_dg_ranks(sheet_players, dict_players)
    if dg_ranks:
        sheet.write_columns("F", "J", dg_ranks)

    # write datagolf probabilities to K/L
    dg_probs = build_cutline_probs(full_data)
    if dg_probs:
        sheet.write_columns("L", "N", dg_probs, start_row=4)


if __name__ == "__main__":
    main()
