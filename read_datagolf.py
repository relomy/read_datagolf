from os import path

import requests
import selenium.webdriver.chrome.service as chrome_service
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import client, file, tools
from selenium import webdriver


def get_datagolf_html():
    url = "https://datagolf.ca/live-predictive-model"
    bin_chromedriver = "E:\\Programs\\chromedrive_chrome75\\chromedriver.exe"

    # start headless webdriver
    service = chrome_service.Service(bin_chromedriver)
    service.start()
    options = webdriver.ChromeOptions()
    options.headless = True
    driver = webdriver.Remote(service.service_url, desired_capabilities=options.to_capabilities())
    driver.get(url)

    # print html for debugging
    print(driver.page_source, file=open("content.html", "w", encoding="utf-8"))

    return driver.page_source


def parse_html(html):
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


def write_column(service, spreadsheet_id, range_name, values):
    """Write a set of values to a spreadsheet."""
    body = {"values": values}
    value_input_option = "USER_ENTERED"
    result = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body,
        )
        .execute()
    )
    print("{0} cells updated.".format(result.get("updatedCells")))


def find_sheet_id(service, spreadsheet_id, title):
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get("sheets", "")
    for sheet in sheets:
        if title in sheet["properties"]["title"]:
            # logger.debug("Sheet ID for {} is {}".format(title, sheet["properties"]["sheetId"]))
            return sheet["properties"]["sheetId"]


def get_values_from_PGA_sheet():
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=RANGE_NAME)
        .execute()
    )
    values = result.get("values", [])

    cells = []
    if not values:
        exit("No data found.")
    else:
        for row in values:
            name = row[0].upper()

            # remove dash if there is one
            name = name.replace("-", "")

            if name in players:
                cells.append([players[name]["place"]])
            else:
                cells.append(["???"])
                print(f"{name}: ???")
    return cells


html = get_datagolf_html()
with open("content.html", mode="r", encoding="utf-8") as fp:
    html = fp.read()

    players = parse_html(html)

    dir = "C:\\Users\\Adam\\Documents\\git\\read_datagolf_live"
    SCOPES = "https://www.googleapis.com/auth/spreadsheets"
    store = file.Storage(path.join(dir, "token.json"))
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(path.join(dir, "token.json"), SCOPES)
        creds = tools.run_flow(flow, store)
    service = build("sheets", "v4", http=creds.authorize(Http()))

    # call the Sheets API
    spreadsheet_id = "1Jv5nT-yUoEarkzY5wa7RW0_y0Dqoj8_zDrjeDs-pHL4"
    sport = "PGAMain"
    RANGE_NAME = "{}!B2:I".format(sport)

    # sheet_id = find_sheet_id(service, spreadsheet_id, sport)

    values = get_values_from_PGA_sheet()
    rng = "{}!I2:{}".format(sport, len(values) + 1)
    write_column(service, spreadsheet_id, rng, values)
