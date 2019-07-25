from os import getenv

import selenium.webdriver.chrome.service as chrome_service
from selenium import webdriver
from bs4 import BeautifulSoup

from DFSsheet import DFSsheet


def get_datagolf_html():
    url = "https://datagolf.ca/live-predictive-model"
    # bin_chromedriver = "E:\\Programs\\chromedrive_chrome75\\chromedriver.exe"
    # bin_chromedriver = r"C:\Users\alewando\Documents\chromedriver\chromedriver.exe"
    bin_chromedriver = getenv("CHROMEDRIVER")

    if not getenv("CHROMEDRIVER"):
        raise ("Could not find CHROMEDRIVER in environment")

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
    print(driver.page_source, file=open("content.html", "w", encoding="utf-8"))

    return driver.page_source


def build_datagolf_players_dict(html, correct_names=None):
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
        name = row.find(id=columns["name"]).text

        # fix name if it needs it
        if name in correct_names:
            first_last = correct_names[name]
        else:
            name = name.replace("-", "")
            first_last = " ".join(name.split(" ", 1)[::-1])

        # add player data to dict
        player_dict[first_last] = {}
        for key in columns:
            player_dict[first_last][key] = row.find(id=columns[key]).text

    return player_dict


def get_dg_ranks(players, dict_players):

    if not players:
        raise ("No data found.")

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


def main():
    html = get_datagolf_html()

    with open("content.html", mode="r", encoding="utf-8") as fp:
        html = fp.read()

        # parse datagolf html into a dict of players
        correct_names = {
            "CABRERA BELLO RAFA": "RAFA CABRERA BELLO",
            "VAN ROOYEN ERIK": "ERIK VAN ROOYEN",
            "LORENZO-VERA MICHAEL": "MIKE LORENZOVERA",
            "PAPADATOS DIMITRIOS": "DIMI PAPADATOS",
        }
        dict_players = build_datagolf_players_dict(html, correct_names)

        # create DFSsheet object
        sport = "PGAMain"
        sheet = DFSsheet(sport)

        # get players from DFS sheet
        sheet_players = sheet.get_players()

        # look up players from sheet in datagolf dictionary
        dg_ranks = get_dg_ranks(sheet_players, dict_players)

        # write datagolf ranks to mc
        sheet.write_columns("F", "I", dg_ranks)


if __name__ == "__main__":
    main()
