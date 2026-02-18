"""Helpers for reading and normalizing DataGolf live model API responses."""

import importlib
import json
import logging
import re
import time
from typing import Any

try:
    requests: Any = importlib.import_module("requests")
except ModuleNotFoundError:  # pragma: no cover - only used in offline test runs
    requests = None

BASE_URL = "https://letzig.datagolf.com/live-model"
DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.5

logger = logging.getLogger(__name__)


def _parse_jsonp(text: str) -> Any:
    """Parse JSONP payloads by stripping the callback wrapper."""
    start = text.find("(")
    end = text.rfind(")")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Invalid JSONP response")
    payload = text[start + 1 : end]
    return json.loads(payload)


def _parse_json_or_jsonp(text: str) -> Any:
    """Handle either plain JSON or JSONP."""
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(stripped)
    return _parse_jsonp(text)


def _request_jsonp(
    url: str,
    params: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    session: Any | None = None,
) -> Any:
    """Fetch JSONP from url with simple retry/backoff and parse to JSON."""
    if requests is None:
        raise ModuleNotFoundError("requests is required for live API calls")
    last_exc: Exception | None = None
    sess = session or requests.Session()
    for attempt in range(retries):
        try:
            if attempt == 0:
                logger.info("Requesting %s", url)
            else:
                logger.warning("Retrying %s (attempt %d)", url, attempt + 1)
            resp = sess.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return _parse_json_or_jsonp(resp.text)
        except Exception as exc:  # noqa: BLE001 - surface last failure after retries
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(backoff * (2**attempt))
    if last_exc is None:
        raise RuntimeError("request failed without exception")
    raise last_exc


def fetch_main_data(tour: str = "pga", mode: str = "mini") -> Any:
    """Fetch live model main data.

    Args:
        tour: DataGolf tour slug used in the URL when mode is not "mini".
        mode: "mini" hits the mini endpoint; any other value uses the tour
            endpoint.

    Returns:
        Parsed JSON payload from the DataGolf live model API.

    TODO(datagolf_api.fetch_main_data): Confirm supported tour values and
        response schema from the DataGolf API.
    """
    if mode == "mini":
        url = f"{BASE_URL}/get-main-data/mini"
    else:
        url = f"{BASE_URL}/get-main-data/{tour}"
    return _request_jsonp(url)


def fetch_player_data(players_last_first: list[str]) -> dict[str, Any]:
    """Fetch per-player data in a single batch request.

    Args:
        players_last_first: Player names formatted as "Last, First".

    Returns:
        Parsed JSON payload keyed by player name.
    """
    if not players_last_first:
        return {}
    url = f"{BASE_URL}/get-player-data"
    params = {"players": json.dumps(players_last_first)}
    return _request_jsonp(url, params=params)


def extract_players_last_first(main_data: Any, tour: str = "pga") -> list[str]:
    """Extract players in "Last, First" format for get-player-data.

    Handles the "mini" payload structure (uses `lb` rows under `tour`) and
    the full payload structure (uses `main` rows with `name` values).
    """
    if isinstance(main_data, dict):
        if mode_is_mini(main_data, tour):
            players = []
            for row in main_data.get(tour, {}).get("lb", []):
                first = row.get("f", "")
                last = row.get("l", "")
                if first and last:
                    players.append(f"{last}, {first}")
            return players
        if "main" in main_data:
            return [row.get("name", "") for row in main_data.get("main", []) if row.get("name")]
    return []


def build_players_dict(
    main_data: dict[str, Any],
    player_data: Any | None,
    correct_names: dict[str, str] | None = None,
) -> dict[str, dict[str, str]]:
    """Combine main + player data into a dict keyed by normalized display name.

    The output dict keys are normalized display names (uppercased, stripped of
    hyphens/parenthetical suffixes) and values are strings for:
    `place`, `total_score`, `thru_hole`, `today_score`, and `perc_make_cut`.
    """
    player_dict: dict[str, dict[str, str]] = {}
    correct_names = correct_names or {}
    today_map = _build_today_map(player_data)

    # Allow fallback from full main data if passed in player_data
    if isinstance(player_data, dict) and "main" in player_data:
        today_map.update(_build_today_map({"main": player_data["main"]}))

    for row in _iter_player_rows(main_data):
        display_name = _normalize_display_name(row["display_name"])
        if display_name in correct_names:
            display_name = correct_names[display_name]

        today_score = _lookup_today(
            today_map,
            row.get("last_first", ""),
            row.get("display_name", ""),
        )

        player_dict[display_name] = {
            "place": row.get("place", ""),
            "total_score": row.get("total_score", ""),
            "thru_hole": row.get("thru_hole", ""),
            "today_score": today_score or "",
            "perc_make_cut": row.get("perc_make_cut", ""),
        }

    return player_dict


def build_cutline_probs(main_data: dict[str, Any]) -> list[list[str | None]]:
    """Build cutline probability rows in [strokes, None, probability] format."""
    values: list[list[str | None]] = []
    cuts = []
    if isinstance(main_data, dict):
        cuts = main_data.get("cuts", []) or []
    for row in cuts:
        score = _format_score(row.get("Score"))
        prob = _format_percent(row.get("prob"))
        values.append([score, None, prob])
    return values


def mode_is_mini(main_data: Any, tour: str = "pga") -> bool:
    """Return True when the payload matches the mini leaderboard shape."""
    return isinstance(main_data, dict) and tour in main_data and "lb" in main_data[tour]


def _iter_player_rows(main_data: dict[str, Any]) -> list[dict[str, str]]:
    if mode_is_mini(main_data):
        rows = []
        for row in main_data.get("pga", {}).get("lb", []):
            first = row.get("f", "")
            last = row.get("l", "")
            display = f"{first} {last}".strip()
            rows.append(
                {
                    "display_name": display,
                    "last_first": f"{last}, {first}".strip(),
                    "place": row.get("p", ""),
                    "total_score": row.get("s", ""),
                    "thru_hole": row.get("t", ""),
                    "perc_make_cut": row.get("w", ""),
                }
            )
        return rows

    rows = []
    for row in main_data.get("main", []):
        last_first = row.get("name", "")
        display = _last_first_to_display(last_first)
        thru = row.get("thru", "")
        teetime = row.get("teetime")
        if str(thru) == "0":
            if teetime not in (None, "", 0, "0"):
                thru = teetime
            else:
                thru = "-"
        rows.append(
            {
                "display_name": display,
                "last_first": last_first,
                "place": row.get("current_pos", ""),
                "total_score": _format_score(row.get("current_score")),
                "thru_hole": thru,
                "perc_make_cut": _format_percent(row.get("cut")),
            }
        )
    return rows


def _build_today_map(player_data: Any | None) -> dict[str, str]:
    today_map: dict[str, str] = {}
    if not player_data:
        return today_map

    if isinstance(player_data, dict):
        if "main" in player_data:
            for row in player_data.get("main", []):
                name = row.get("name", "")
                today = row.get("today")
                if name and today is not None:
                    today_map[_name_key(name)] = _format_score(today)
            return today_map

        for key, value in player_data.items():
            if key in {"players", "main", "meta"}:
                continue
            today = _find_today_in_value(value)
            if today is not None:
                today_map[_name_key(key)] = _format_score(today)
        if "players" in player_data:
            for key, value in player_data.get("players", {}).items():
                today = _find_today_in_value(value)
                if today is not None:
                    today_map[_name_key(key)] = _format_score(today)
    elif isinstance(player_data, list):
        for row in player_data:
            name = row.get("name", "")
            today = row.get("today")
            if name and today is not None:
                today_map[_name_key(name)] = _format_score(today)
    return today_map


def _find_today_in_value(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("today", "today_score", "score_today", "current_today"):
            if key in value:
                return value.get(key)
        return None
    if isinstance(value, list):
        for row in reversed(value):
            if isinstance(row, dict):
                for key in ("today", "today_score", "score_today", "current_today"):
                    if key in row:
                        return row.get(key)
    return None


def _lookup_today(today_map: dict[str, str], last_first: str, display_name: str) -> str | None:
    for key in (_name_key(last_first), _name_key(display_name)):
        if key and key in today_map:
            return today_map[key]
    return None


def _normalize_display_name(name: str) -> str:
    name = re.sub(r" *\\(\\w+\\) *", "", name)
    name = name.upper().replace("-", "")
    name = re.sub(r"\\s+", " ", name).strip()
    return name


def _last_first_to_display(name: str) -> str:
    if "," in name:
        last, first = [part.strip() for part in name.split(",", 1)]
        return f"{first} {last}".strip()
    return name


def _name_key(name: str) -> str:
    key = name.replace(", ", "")
    key = key.replace(" ", "")
    key = key.replace(".", "")
    key = key.replace("'", "")
    return key.lower()


def _format_percent(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str) and "%" in value:
        return value
    try:
        pct = float(value) * 100
    except (TypeError, ValueError):
        return ""
    if abs(pct - round(pct)) < 0.05:
        return f"{pct:.0f}%"
    return f"{pct:.1f}%"


def _format_score(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        num = float(value)
    except (TypeError, ValueError):
        return ""
    if num != num:
        return ""
    if abs(num) < 1e-9:
        return "E"
    if abs(num - int(num)) < 1e-9:
        num = int(num)
    if isinstance(num, int) and num > 0:
        return f"+{num}"
    return f"{num}"
