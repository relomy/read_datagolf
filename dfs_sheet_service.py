"""Service layer for DFS sheet operations."""

from datetime import datetime
from typing import Any, Sequence

from dfs_sheet_domain import (
    build_values_for_vip_lineup,
    data_range_for_sport,
    header_range_for_sport,
    lineup_range_for_sport,
)
from dfs_sheet_repository import DfsSheetRepository


class DfsSheetService:
    """Service that orchestrates DFS sheet reads/writes."""

    def __init__(self, repo: DfsSheetRepository, sport: str) -> None:
        self.repo = repo
        self.sport = sport
        self.data_range = data_range_for_sport(sport)
        self.columns: list[str] | None = None
        self.values: list[list[Any]] | None = None

    def _ensure_loaded(self) -> None:
        if self.columns is None:
            self.columns = self.repo.read_range(header_range_for_sport(self.sport))[0]
        if self.values is None:
            self.values = self.repo.read_range(self.data_range)

    def clear_standings(self) -> None:
        self.repo.clear_range(self.data_range)

    def clear_lineups(self) -> None:
        self.repo.clear_range(lineup_range_for_sport(self.sport))

    def write_players(self, values: Sequence[Sequence[Any]]) -> None:
        self.repo.write_range(values, self.data_range)

    def write_column(
        self, column: str, values: Sequence[Sequence[Any]], start_row: int = 2
    ) -> None:
        cell_range = f"{self.sport}!{column}{start_row}:{column}"
        self.repo.write_range(values, cell_range)

    def write_columns(
        self,
        start_col: str,
        end_col: str,
        values: Sequence[Sequence[Any]],
        start_row: int = 2,
    ) -> None:
        cell_range = f"{self.sport}!{start_col}{start_row}:{end_col}"
        self.repo.write_range(values, cell_range)

    def write_lineup_range(self, values: Sequence[Sequence[Any]]) -> None:
        self.repo.write_range(values, lineup_range_for_sport(self.sport))

    def add_last_updated(self, dt_updated: datetime) -> None:
        cell_range = f"{self.sport}!L1:Q1"
        values = [["Last Updated", "", dt_updated.strftime("%Y-%m-%d %H:%M:%S")]]
        self.repo.write_range(values, cell_range)

    def add_contest_details(self, contest_name: str, positions_paid: Any) -> None:
        cell_range = f"{self.sport}!X1:Y1"
        values = [[positions_paid, contest_name]]
        self.repo.write_range(values, cell_range)

    def add_min_cash(self, min_cash: Any) -> None:
        cell_range = f"{self.sport}!W1:W1"
        values = [[min_cash]]
        self.repo.write_range(values, cell_range)

    def add_non_cashing_info(self, non_cashing_info: Sequence[Sequence[Any]]) -> None:
        cell_range = f"{self.sport}!X3:Y16"
        self.repo.write_range(non_cashing_info, cell_range)

    def add_train_info(self, train_info: Sequence[Sequence[Any]]) -> None:
        cell_range = f"{self.sport}!AA3:AM10"
        self.repo.write_range(train_info, cell_range)

    def build_values_for_vip_lineup(self, vip: Any) -> list[list[Any]]:
        return build_values_for_vip_lineup(self.sport, vip)

    def write_vip_lineups(self, vips: Sequence[Any]) -> None:
        lineup_mod = 5
        vips = list(vips)
        vips.sort(key=lambda x: x.name.lower())
        sport_mod = len(vips[0].lineup) + 3
        all_lineup_values: list[list[Any]] = []
        for i, vip in enumerate(vips):
            values = self.build_values_for_vip_lineup(vip)
            if i < lineup_mod:
                all_lineup_values.extend(values)
            else:
                for j, k in enumerate(values):
                    mod = (i % lineup_mod) + ((i % lineup_mod) * sport_mod) + j
                    all_lineup_values[mod].extend([""] + k)
            if i != lineup_mod:
                all_lineup_values.append([])
        self.repo.write_range(all_lineup_values, lineup_range_for_sport(self.sport))

    def get_players(self) -> list[str]:
        self._ensure_loaded()
        assert self.columns is not None
        assert self.values is not None
        return [row[self.columns.index("Name")] for row in self.values]

    def get_lineup_values(self) -> list[list[Any]]:
        return self.repo.read_range(lineup_range_for_sport(self.sport))
