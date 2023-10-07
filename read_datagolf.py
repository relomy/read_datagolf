"""Read from https://datagolf.ca/live-predictive-model and upload results to DFS spreadsheet."""

from os import getenv
import re

import selenium.webdriver.chrome.service as chrome_service
from bs4 import BeautifulSoup
from selenium import webdriver

from dfssheet import DFSSheet


def get_datagolf_html(save_to_file=False):
    """Use Chromedriver to get website's JS-generated HTML and write to file."""
    url = "https://datagolf.ca/live-predictive-model"
    bin_chromedriver = getenv("CHROMEDRIVER")

    if not getenv("CHROMEDRIVER"):
        raise ("Could not find CHROMEDRIVER in environment")

    # start headless webdriver
    service = chrome_service.Service(bin_chromedriver)
    service.start()
    options = webdriver.ChromeOptions()
    options.headless = True
    driver = webdriver.Remote(service.service_url, options=options)
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
        csvname = row.attrs["name"]
        last_name, first_name = csvname.split(",")

        # combine first and last name
        name = f"{first_name.strip().upper()} {last_name.strip().upper()}"

        # remove course from name, if there is one
        name = re.sub(r" *\(\w+\) *", "", name)
        name = name.replace("-", "")
        if name in correct_names:
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
        player = player.upper().replace("-", "")

        if player in dict_players:
            values.append(
                [
                    dict_players[player]["place"],
                    dict_players[player]["total_score"],
                    dict_players[player]["thru_hole"],
                    dict_players[player]["today_score"],
                ]
            )
        else:
            values.append(["???", "", "", ""])
            print(f"{player}: ???")

    return values


def build_cutline_probs(html):
    """Parse datagolf's HTML and return cutline probabilities."""
    values = []
    # find our div in the html
    soup = BeautifulSoup(html, "html.parser")
    sweat_div = soup.find("div", {"class": "cut-sweat"})

    # loop through the cut-cols
    datacols = sweat_div.find_all("div", {"class": "cut-col"})

    for col in datacols:
        cut_value_div = col.find("div", {"class": "cut-value"})
        cut_value = cut_value_div.find("span").text
        cut_percent = col.find("span", {"class": "cut-percent"}).text

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
            "SAMUEL STEVENS": "SAM STEVENS",
        }
        dict_players = build_datagolf_players_dict(html, correct_names)

        # create DFSsheet object
        sport = "GOLF"
        sheet = DFSSheet(sport)

        # get players from DFS sheet
        sheet_players = sheet.get_players()

        # look up players from sheet in dg dict and write to sheet
        dg_ranks = get_dg_ranks(sheet_players, dict_players)
        if dg_ranks:
            sheet.write_columns("F", "I", dg_ranks)

        # write datagolf probabilities to K/L
        dg_probs = build_cutline_probs(html)
        if dg_probs:
            sheet.write_columns("L", "N", dg_probs, start_row=4)


if __name__ == "__main__":
    main()
