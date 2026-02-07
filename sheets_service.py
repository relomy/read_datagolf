"""Factory for building a SheetClient for this repo."""

import logging
from os import getenv
from typing import Any

from dfs_common.sheets import SheetClient, service_account_provider

DEFAULT_SPREADSHEET_ID = "1Jv5nT-yUoEarkzY5wa7RW0_y0Dqoj8_zDrjeDs-pHL4"


def _resolve_spreadsheet_id(spreadsheet_id: str | None) -> str:
    if spreadsheet_id:
        return spreadsheet_id
    env_spreadsheet_id = getenv("SPREADSHEET_ID")
    if env_spreadsheet_id:
        return env_spreadsheet_id
    return DEFAULT_SPREADSHEET_ID


def make_sheet_client(
    spreadsheet_id: str | None = None,
    *,
    service: Any | None = None,
    credentials_provider: Any | None = None,
    logger: logging.Logger | None = None,
) -> SheetClient:
    resolved_spreadsheet_id = _resolve_spreadsheet_id(spreadsheet_id)
    if credentials_provider is None and service is None:
        credentials_provider = service_account_provider("client_secret.json")
    return SheetClient(
        spreadsheet_id=resolved_spreadsheet_id,
        service=service,
        credentials_provider=credentials_provider,
        logger=logger,
    )
