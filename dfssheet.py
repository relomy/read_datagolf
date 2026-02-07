"""Google Sheets helpers for DFS spreadsheets."""

import logging
import logging.config
from datetime import datetime
from os import getenv
from typing import Any, Protocol, Sequence

from dfs_common.sheets import SheetClient, service_account_provider

logging.config.fileConfig("logging.ini", disable_existing_loggers=False)

DEFAULT_SPREADSHEET_ID = "1Jv5nT-yUoEarkzY5wa7RW0_y0Dqoj8_zDrjeDs-pHL4"


def _resolve_spreadsheet_id(spreadsheet_id: str | None) -> str:
    if spreadsheet_id:
        return spreadsheet_id
    env_spreadsheet_id = getenv("SPREADSHEET_ID")
    if env_spreadsheet_id:
        return env_spreadsheet_id
    return DEFAULT_SPREADSHEET_ID


class _VipPlayer(Protocol):
    name: str
    salary: Any
    fpts: Any
    value: Any
    ownership: Any
    pos: str


class _Vip(Protocol):
    name: str
    pmr: Any
    lineup: Sequence[_VipPlayer]
    rank: Any
    pts: Any


class Sheet:
    """Google Sheets wrapper bound to a single spreadsheet."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        *,
        spreadsheet_id: str | None = None,
        service: Any | None = None,
        credentials_provider: Any | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)

        # unique ID for DFS Ownership/Value spreadsheet
        self.spreadsheet_id = _resolve_spreadsheet_id(spreadsheet_id)
        if credentials_provider is None and service is None:
            credentials_provider = service_account_provider("client_secret.json")
        self._client = SheetClient(
            spreadsheet_id=self.spreadsheet_id,
            service=service,
            credentials_provider=credentials_provider,
            logger=self.logger,
        )

    def setup_service(self) -> Any:
        """Return the configured Sheets API service."""
        return self._client.service

    @property
    def service(self) -> Any:
        return self._client.service

    @service.setter
    def service(self, value: Any) -> None:
        self._client._service = value


class DFSSheet(Sheet):
    """Sheet helpers for DFS worksheets keyed by sport name.

    The `sport` argument must match a worksheet title and have a header row
    containing a "Name" column (used by `get_players`).
    """

    LINEUP_RANGES = {
        "NBA": "J3:V61",
        "CFB": "J3:V61",
        "NFL": "J3:V66",
        "NFLShowdown": "J3:V66",
        "GOLF": "L8:Z56",
        "PGAMain": "L8:X56",
        "PGAWeekend": "L3:Q41",
        "PGAShowdown": "L3:Q41",
        "TEN": "J3:V61",
        "MLB": "J3:V71",
        "XFL": "J3:V56",
        "MMA": "J3:V61",
        "LOL": "J3:V61",
        "NAS": "J3:V61",
        "USFL": "J3:V66",
    }

    def __init__(
        self,
        sport: str,
        *,
        spreadsheet_id: str | None = None,
        service: Any | None = None,
        credentials_provider: Any | None = None,
    ) -> None:
        """Initialize sheet ranges based on the sport worksheet name."""
        self.sport = sport

        # set ranges based on sport
        self.start_col = "A"
        if "PGA" in self.sport or self.sport == "GOLF":
            self.end_col = "E"
        else:
            self.end_col = "H"
        self.data_range = "{0}!{1}2:{2}".format(
            self.sport, self.start_col, self.end_col
        )

        # init Sheet (super) class
        super().__init__(
            spreadsheet_id=spreadsheet_id,
            service=service,
            credentials_provider=credentials_provider,
        )

        # get columns from first row
        self.columns = self._read_values(self._header_range())[0]

        self.values = self._read_values(self.data_range)

        # if self.values:
        #     self.max_rows = len(self.values)
        #     self.max_columns = len(self.values[0])
        # else:
        #     raise f"No values from self._read_values({self.cell_range})"

    def _header_range(self) -> str:
        return f"{self.sport}!{self.start_col}1:{self.end_col}1"

    def _lineups_range(self) -> str:
        return f"{self.sport}!{self.LINEUP_RANGES[self.sport]}"

    def _read_values(self, cell_range: str) -> list[list[Any]]:
        return self._client.get_values(cell_range)

    def _write_values(
        self, values: Sequence[Sequence[Any]], cell_range: str
    ) -> None:
        self._client.write_values([list(row) for row in values], cell_range)

    def _clear_range(self, cell_range: str) -> None:
        self._client.clear_range(cell_range)

    def clear_standings(self) -> None:
        """Clear the standings range for the current sport worksheet."""
        self._clear_range(self.data_range)

    def clear_lineups(self) -> None:
        """Clear the lineup range for the current sport worksheet.

        Requires `sport` to exist in `LINEUP_RANGES`.
        """
        self._clear_range(self._lineups_range())

    def write_players(self, values: Sequence[Sequence[Any]]) -> None:
        """Write player rows (from standings) to the DFS sheet."""
        cell_range = f"{self.data_range}"
        self._write_values(values, cell_range)

    def write_column(
        self, column: str, values: Sequence[Sequence[Any]], start_row: int = 2
    ) -> None:
        """Write values to a single column starting at start_row."""
        # set range based on column e.g. PGAMain!I2:I
        cell_range = f"{self.sport}!{column}{start_row}:{column}"
        self._write_values(values, cell_range)

    def write_columns(
        self,
        start_col: str,
        end_col: str,
        values: Sequence[Sequence[Any]],
        start_row: int = 2,
    ) -> None:
        """Write values across multiple columns starting at start_row."""
        # set range based on column e.g. PGAMain!I2:I
        cell_range = f"{self.sport}!{start_col}{start_row}:{end_col}"
        self._write_values(values, cell_range)

    def write_lineup_range(self, values: Sequence[Sequence[Any]]) -> None:
        """Write values to the lineup range for the current sport worksheet.

        Requires `sport` to exist in `LINEUP_RANGES`.
        """
        self._write_values(values, self._lineups_range())

    def add_last_updated(self, dt_updated: datetime) -> None:
        """Write a last-updated timestamp into the sheet header."""
        cell_range = f"{self.sport}!L1:Q1"
        values = [["Last Updated", "", dt_updated.strftime("%Y-%m-%d %H:%M:%S")]]
        self._write_values(values, cell_range)

    def add_contest_details(self, contest_name: str, positions_paid: Any) -> None:
        """Write contest metadata into the sheet header."""
        cell_range = f"{self.sport}!X1:Y1"
        values = [[positions_paid, contest_name]]
        self._write_values(values, cell_range)

    def add_min_cash(self, min_cash: Any) -> None:
        """Write the minimum cash amount into the sheet header."""
        cell_range = f"{self.sport}!W1:W1"
        values = [[min_cash]]
        self._write_values(values, cell_range)

    def add_non_cashing_info(self, non_cashing_info: Sequence[Sequence[Any]]) -> None:
        """Write non-cashing info rows into the sheet."""
        cell_range = f"{self.sport}!X3:Y16"
        values = non_cashing_info
        self._write_values(values, cell_range)

    def add_train_info(self, train_info: Sequence[Sequence[Any]]) -> None:
        """Write training info rows into the sheet."""
        cell_range = f"{self.sport}!AA3:AM10"
        values = train_info
        self._write_values(values, cell_range)

    def build_values_for_vip_lineup(self, vip: _Vip) -> list[list[Any]]:
        """Build the values block for a single VIP lineup."""
        if "GOLF" in self.sport:
            values = [[vip.name, None, "PMR", vip.pmr, None, None, None]]
            values.append(["Name", "Salary", "Pts", "Value", "Own", "Pos", "Score"])
            for player in vip.lineup:
                values.append(
                    [
                        player.name,
                        player.salary,
                        player.fpts,
                        player.value,
                        player.ownership,
                        None,
                        None,
                    ]
                )
            values.append(["rank", vip.rank, vip.pts, None, None, None, None])
        else:
            values = [[vip.name, None, "PMR", vip.pmr, None, None]]
            values.append(["Pos", "Name", "Salary", "Pts", "Value", "Own"])
            for player in vip.lineup:
                values.append(
                    [
                        player.pos,
                        player.name,
                        player.salary,
                        player.fpts,
                        player.value,
                        player.ownership,
                    ]
                )
            values.append(["rank", vip.rank, None, vip.pts, None, None])
        return values

    def write_vip_lineups(self, vips: Sequence[_Vip]) -> None:
        """Write multiple VIP lineups into the lineup range.

        Requires `sport` to exist in `LINEUP_RANGES`.
        """
        cell_range = self.LINEUP_RANGES[self.sport]
        lineup_mod = 5
        # sort VIPs based on name
        vips.sort(key=lambda x: x.name.lower())
        # add size of lineup + 3 for extra rows
        sport_mod = len(vips[0].lineup) + 3
        all_lineup_values = []
        for i, vip in enumerate(vips):
            values = self.build_values_for_vip_lineup(vip)
            # determine if we have to split list horizontally
            if i < lineup_mod:
                all_lineup_values.extend(values)
            elif i >= lineup_mod:
                for j, k in enumerate(values):
                    mod = (i % lineup_mod) + ((i % lineup_mod) * sport_mod) + j
                    all_lineup_values[mod].extend([""] + k)

            # add extra row to values for spacing if needed
            if i != lineup_mod:
                all_lineup_values.append([])
        self._write_values(all_lineup_values, f"{self.sport}!{cell_range}")

    def get_players(self) -> list[str]:
        """Return player names from the "Name" column in the standings range."""
        return [row[self.columns.index("Name")] for row in self.values]

    def get_lineup_values(self) -> list[list[Any]]:
        """Return lineup values from the lineup range."""
        return self._read_values(self._lineups_range())
