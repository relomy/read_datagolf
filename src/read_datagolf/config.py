"""Central config defaults and environment overrides for read_datagolf."""

from __future__ import annotations

import os
from pathlib import Path

from dfs_common import config as common_config

from read_datagolf.paths import repo_file


def _path_from_env(var_name: str, default: Path) -> Path:
    raw = os.getenv(var_name)
    if not raw:
        return default
    path = Path(raw)
    if path.is_absolute():
        return path
    return repo_file(raw)


def config_json_path() -> Path:
    return _path_from_env("READ_DATAGOLF_CONFIG_FILE", repo_file("config.json"))


def service_account_path() -> Path:
    return _path_from_env("READ_DATAGOLF_SERVICE_ACCOUNT_FILE", repo_file("client_secret.json"))


def load_settings() -> common_config.ReadDataGolfSettings:
    loaded = common_config.load_json_config(str(config_json_path()))
    return common_config.resolve_read_datagolf_settings(loaded)
