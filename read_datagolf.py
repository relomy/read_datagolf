"""Read from https://datagolf.ca/live-predictive-model and upload results to DFS spreadsheet."""

import re
from os import getenv

import selenium.webdriver.chrome.service as chrome_service
from selenium import webdriver
from bs4 import BeautifulSoup


from dfssheet import DFSSheet


def get_datagolf_html(save_to_file=False):
    """Use Chromedriver to get website's JS-generated HTML and write to file."""
    url = "https://datagolf.ca/live-predictive-model"
    bin_chromedriver = getenv("CHROMEDRIVER")

    if not getenv("CHROMEDRIVER"):
        raise "Could not find CHROMEDRIVER in environment"

    # start headless webdriver
    service = chrome_service.Service(bin_chromedriver)
    service.start()
    options = webdriver.ChromeOptions()
    options.headless = True
    driver = webdriver.Remote(
        service.service_url, desired_capabilities=options.to_capabilities()
    )
    driver.get(url)

    # print html for debugging
    if save_to_file:
        print(driver.page_source, file=open("content.html", "w", encoding="utf-8"))

    return driver.page_source


def build_datagolf_players_dict(html, correct_names=None):
    """Parse datagolf's HTML and add stats to dictionary."""
    player_dict = {}

    # find our table in the html
    soup = BeautifulSoup(html, "html.parser")
    table_div = soup.find("div", {"class": "table"})

    # loop through the datarows
    datarows = table_div.find_all("div", {"class": "datarow"})

    # the easiest way seemed to use the id column
    columns = {
        "place": "col_text0",
        "name": "col_text1",
        "total_score": "col_text2",
        "thru_hole": "col_text3",
        "today_score": "col_text4",
        "perc_make_cut": "col_text5",
    }
    for row in datarows:
        # find name row
        name_row = row.find(id=columns["name"])

        # pull first/last name from classes within name_row
        first_name = name_row.find(class_="name-first").text.strip()
        full_name = name_row.find(class_="name-span").text

        # pull last name from full name by removing first name
        last_name = full_name.replace(first_name, "").strip()

        # combine first and last name
        name = f"{first_name} {last_name}"

        # remove course from name, if there is one
        name = re.sub(r"\s*\(\w+\)\s*", "", name)

        # # fix name if it needs it
        # if name in correct_names:
        #     first_last = correct_names[name]
        # else:
        #     name = name.replace("-", "")
        #     first_last = " ".join(name.split(" ", 1)[::-1])

        # # add player data to dict
        # player_dict[first_last] = {}
        # for key in columns:
        #     player_dict[first_last][key] = row.find(id=columns[key]).text
        # fix name if it needs it
        if name in correct_names:
            # name = name.replace("-", "")
            name = correct_names[name]

        # add player data to dict
        player_dict[name] = {}
        for key in columns:
            player_dict[name][key] = row.find(id=columns[key]).text

    return player_dict


def get_dg_ranks(players, dict_players):
    """Compare players from the DFS sheet with datagolf stats dictionary."""
    if not players:
        raise Exception("No data found.")

    values = []
    for player in players:
        # convert to uppercase and remove dash if there is one
        # player = player.upper().replace("-", "")
        player = player.upper()

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
            values.append(["???", "", "", ""])
            print(f"{player}: ???")

    return values


def add_dg_values_to_lineups(lineup_values, dict_players):
    new_lineup_values = []
    # loop through each row (two columns) in the lineup values
    for row in lineup_values:
        # loop through each real with data
        if len(row) > 1:
            # check for player in 0th cell of row
            player = row[0].upper().replace("-", "")
            if player in dict_players:
                # add him to
                # print(f"found player {row[0]} in row [0] in dict_players!")

                if len(row) > 5:
                    # add dg data (place/total score) to index 5 and 6
                    row[5] = dict_players[player]["place"]
                    row[6] = dict_players[player]["total_score"]
                else:
                    # extend list to include place/total score
                    row.extend(
                        [
                            dict_players[player]["place"],
                            dict_players[player]["total_score"],
                        ]
                    )

            # also check the 8th cell (2nd column)
            if len(row) > 8:
                player = row[8].upper().replace("-", "")
                if player in dict_players:
                    # print(f"found player {row[8]} in row [9] in dict_players!")

                    if len(row) < 14:
                        # extend list to include place/total score
                        row.extend(
                            [
                                dict_players[player]["place"],
                                dict_players[player]["total_score"],
                            ]
                        )
                    else:
                        # add dg data (place/total score) to index 5 and 6
                        row[13] = dict_players[player]["place"]
                        row[14] = dict_players[player]["total_score"]

        new_lineup_values.append(row)
    return new_lineup_values


def build_cutline_probs(html):
    """Parse datagolf's HTML and return cutline probabilities."""
    values = []
    # find our div in the html
    soup = BeautifulSoup(html, "html.parser")
    sweat_div = soup.find("div", {"class": "cut-sweat"})

    # loop through the cut-cols
    datacols = sweat_div.find_all("div", {"class": "cut-col"})

    for col in datacols:
        cut_value = col.find("div", {"class": "cut-value"}).text
        cut_percent = col.find("div", {"class": "cut-percent"}).text

        values.append([cut_value, None, cut_percent])

    return values
    # return cutline_dict


def main():
    """Proceed."""
    html = get_datagolf_html(save_to_file=True)

    with open("content.html", mode="r", encoding="utf-8") as fp:
        html = fp.read()

        # parse datagolf html into a dict of players
        correct_names = {
            "TED POTTER JR": "TED POTTER JR.",
            "BILLY HURLEY III": "BILLY HURLEY",
            "KYOUNGHOON LEE": "KYOUNG-HOON LEE",
        }
        dict_players = build_datagolf_players_dict(html, correct_names)

        # create DFSsheet object
        # sport = "PGAMain"
        sport = "GOLF"
        sheet = DFSSheet(sport)

        # get players from DFS sheet
        sheet_players = sheet.get_players()

        # look up players from sheet in dg dict and write to sheet
        dg_ranks = get_dg_ranks(sheet_players, dict_players)
        if dg_ranks:
            sheet.write_columns("F", "J", dg_ranks)

        # get lineup_values from DFS sheet
        lineup_values = sheet.get_lineup_values()
        new_lineup_valus = add_dg_values_to_lineups(lineup_values, dict_players)
        if new_lineup_valus:
            sheet.write_lineup_range(new_lineup_valus)
            # sheet.write_columns("L", "AA", new_lineup_valus, start_row=8)

        # write datagolf probabilities to K/L
        dg_probs = build_cutline_probs(html)
        if dg_probs:
            sheet.write_columns("L", "N", dg_probs, start_row=4)


if __name__ == "__main__":
    main()
