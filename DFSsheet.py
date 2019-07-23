from os import path

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import client, file, tools


class DFSsheet(object):
    def __init__(self, sport):
        self.sport = sport

        # authorize class to use sheets API
        self.service = self.setup_service()

        # unique ID for DFS Ownership/Value spreadsheet
        self.SPREADSHEET_ID = "1Jv5nT-yUoEarkzY5wa7RW0_y0Dqoj8_zDrjeDs-pHL4"

        self.range = f"{self.sport}!A2:I"

        # current PGA sheet columns
        self.columns = [
            "Position",
            "Name",
            "Team",
            "Matchup",
            "Salary",
            "Ownership",
            "Points",
            "Values",
            "mc",
        ]

        self.values = self.get_values_from_range(self.range)

        if self.values:
            self.max_rows = len(self.values)
            self.max_columns = len(self.values[0])
        else:
            raise f"No values from self.get_values_from_range({self.range})"

    def setup_service(self):
        SCOPES = "https://www.googleapis.com/auth/spreadsheets"
        dir = "."
        store = file.Storage(path.join(dir, "token.json"))
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(path.join(dir, "token.json"), SCOPES)
            creds = tools.run_flow(flow, store)
        return build("sheets", "v4", http=creds.authorize(Http()))

    def write_column(self, column, values):
        """Write a set of values to a column in a spreadsheet."""
        # set range based on column e.g. PGAMain!I2:I
        range = f"{self.sport}!{column}2:{column}"
        body = {"values": values}
        value_input_option = "USER_ENTERED"
        result = (
            self.service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self.SPREADSHEET_ID,
                range=range,
                valueInputOption=value_input_option,
                body=body,
            )
            .execute()
        )
        print("{0} cells updated.".format(result.get("updatedCells")))

    def find_sheet_id(self, title):
        sheet_metadata = (
            self.service.spreadsheets().get(spreadsheetId=self.SPREADSHEET_ID).execute()
        )
        sheets = sheet_metadata.get("sheets", "")
        for sheet in sheets:
            if title in sheet["properties"]["title"]:
                # logger.debug("Sheet ID for {} is {}".format(title, sheet["properties"]["sheetId"]))
                return sheet["properties"]["sheetId"]

    def get_values_from_self_range(self):
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.SPREADSHEET_ID, range=self.range)
            .execute()
        )
        return result.get("values", [])

    def get_values_from_range(self, range):
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.SPREADSHEET_ID, range=range)
            .execute()
        )
        return result.get("values", [])

    def get_players(self):
        return [row[1] for row in self.values]

    def sheet_letter_to_index(self, letter):
        """1-indexed"""
        return ord(letter.lower()) - 96

    def header_index_to_letter(self, header):
        """1-indexed"""
        return chr(self.columns.index(header) + 97).upper()
