import selenium.webdriver.chrome.service as chrome_service
from bs4 import BeautifulSoup

from selenium import webdriver

from DFSsheet import DFSsheet


def get_datagolf_html():
    url = "https://datagolf.ca/live-predictive-model"
    # bin_chromedriver = "E:\\Programs\\chromedrive_chrome75\\chromedriver.exe"
    bin_chromedriver = r"C:\Users\alewando\Documents\chromedriver\chromedriver.exe"

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


def build_datagolf_players_dict(html):
    player_dict = {}

    # find our table in the html
    soup = BeautifulSoup(html, "html.parser")
    table_div = soup.find("div", {"class": "table"})

    # loop through the datarows
    datarows = table_div.find_all("div", {"class": "datarow"})
    for row in datarows:
        # the easiest way seemed to use the id column
        place = row.find(id="col_text0").text
        name = row.find(id="col_text1").text
        total_score = row.find(id="col_text2").text
        thru_hole = row.find(id="col_text3").text
        today_score = row.find(id="col_text4").text
        make_cut_perc = row.find(id="col_text5").text

        # split name by " ", reverse it, and convert to title case
        first_last = " ".join(name.split(" ", 1)[::-1])

        # temporary fix for split
        if name == "CABRERA BELLO RAFA":
            first_last = "RAFA CABRERA BELLO"
        if name == "VAN ROOYEN ERIK":
            first_last = "ERIK VAN ROOYEN"

        # i don't think there's a way around this
        if first_last == "MICHAEL LORENZO-VERA":
            first_last = "MIKE LORENZOVERA"
        if first_last == "DIMITRIOS PAPADATOS":
            first_last = "DIMI PAPADATOS"

        if "-" in first_last:
            first_last = first_last.replace("-", "")

        # add to dict
        player_dict[first_last] = {
            "place": place,
            "total_score": total_score,
            "thru_hole": thru_hole,
            "today_score": today_score,
            "make_cut_perc": make_cut_perc,
        }

    return player_dict


def get_dg_ranks(players, dict_players):

    if not players:
        raise ("No data found.")

    values = []
    for player in players:
        # convert to uppercase and remove dash if there is one
        player = player.upper().replace("-", "")

        if player in dict_players:
            values.append([dict_players[player]["place"]])
        else:
            values.append(["???"])
            print(f"{player}: ???")

    return values


def main():
    # html = get_datagolf_html()

    with open("content.html", mode="r", encoding="utf-8") as fp:
        html = fp.read()

        # parse datagolf html into a dict of players
        dict_players = build_datagolf_players_dict(html)

        # create DFSsheet object
        sport = "PGAMain"
        sheet = DFSsheet(sport)

        # get players from DFS sheet
        sheet_players = sheet.get_players()

        # look up players from sheet in datagolf dictionary
        dg_ranks = get_dg_ranks(sheet_players, dict_players)

        # write datagolf ranks to mc
        sheet.write_column("I", dg_ranks)


if __name__ == "__main__":
    main()

