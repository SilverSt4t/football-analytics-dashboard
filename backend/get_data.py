"""API-only data client for the Touchline backend.

The provider's JSON is parsed in memory, normalized, and discarded. Only the
normalized response is kept in the short-lived memory cache; no raw data files
or manually entered datasets are read or written.
"""

from __future__ import annotations

import base64
import binascii
import copy
import threading
import time
import unicodedata
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse
from zoneinfo import ZoneInfo

import requests

from backend.competition_catalog import TOP_COMPETITIONS

OPENLIGADB_BASE = "https://api.openligadb.de"
JAKARTA = ZoneInfo("Asia/Jakarta")
CACHE_TTL_SECONDS = 900
_normalized_cache: dict[str, tuple[float, object]] = {}
_cache_lock = threading.Lock()


class DataSourceError(RuntimeError):
    """Raised when the live football API cannot provide data."""


def _fetch_json(endpoint: str):
    """Fetch provider JSON for immediate in-memory normalization; no raw cache."""
    response = requests.get(f"{OPENLIGADB_BASE}/{endpoint.lstrip('/')}", timeout=18)
    response.raise_for_status()
    return response.json()


def _cached_normalized(key: str, loader, refresh: bool = False):
    """Cache only clean, frontend-ready objects—not provider JSON or files."""
    now = time.monotonic()
    if not refresh:
        with _cache_lock:
            cached = _normalized_cache.get(key)
            if cached and cached[0] > now:
                return copy.deepcopy(cached[1])

    normalized = loader()
    with _cache_lock:
        _normalized_cache[key] = (now + CACHE_TTL_SECONDS, copy.deepcopy(normalized))
    return normalized


def _compact(value: str) -> str:
    value = str(value).replace("ß", "ss").replace("ẞ", "SS")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return "".join(character.lower() for character in value if character.isalnum())


def _normalize_leagues(rows: list[dict]) -> list[dict]:
    """Keep only curated top competitions that are actually in the API result."""
    selected: dict[str, tuple[int, dict]] = {}
    for row in rows:
        sport = row.get("sport") or {}
        sport_name = sport.get("sportName", "") if isinstance(sport, dict) else str(sport)
        if sport_name and "fussball" not in _compact(sport_name) and "football" not in _compact(sport_name):
            continue

        shortcut = str(row.get("leagueShortcut", "")).strip()
        shortcut_key = shortcut.casefold()
        name_key = _compact(row.get("leagueName", ""))
        matched = None
        alias_rank = 999
        for rule in TOP_COMPETITIONS:
            aliases = [code.casefold() for code in rule["codes"]]
            code_match = shortcut_key in aliases
            name_match = any(_compact(key) in name_key for key in rule["name_keys"])
            if code_match or name_match:
                matched = rule
                alias_rank = aliases.index(shortcut_key) if code_match else len(aliases)
                break
        if matched is None:
            continue

        normalized = {
            "competitionId": matched["id"],
            "leagueShortcut": shortcut,
            "leagueName": matched["name"],
            "leagueSeason": row.get("leagueSeason"),
            "sport": "Fußball",
            "priority": matched["rank"],
        }
        current = selected.get(matched["id"])
        if current is None or alias_rank < current[0]:
            selected[matched["id"]] = (alias_rank, normalized)

    clean = [value[1] for value in selected.values()]
    return sorted(clean, key=lambda row: (row["priority"], row["leagueName"]))


def get_leagues(season: int, refresh: bool = False) -> list[dict]:
    """Fetch and normalize the available competitions for a season."""
    return _cached_normalized(
        f"leagues:{season}",
        lambda: _normalize_leagues(_fetch_json(f"getavailableleagues/{season}")),
        refresh=refresh,
    )


def _final_score(match: dict):
    results = match.get("matchResults") or []
    final_results = [result for result in results if result.get("resultTypeID", 0) >= 2]
    if final_results:
        result = sorted(
            final_results,
            key=lambda item: (item.get("resultTypeID", 0), item.get("resultOrderID", 0)),
        )[-1]
        return result.get("pointsTeam1"), result.get("pointsTeam2")

    # If no full-time result exists yet, derive the live score from goal events.
    goals = match.get("goals") or []
    if goals:
        last_goal = goals[-1]
        return last_goal.get("scoreTeam1"), last_goal.get("scoreTeam2")
    return None, None


def _normalize_matches(matches: list[dict]) -> list[dict]:
    """Flatten API fixtures to the small set of fields used by the dashboard."""
    rows = []
    for match in matches:
        home_score, away_score = _final_score(match)
        raw_date = match.get("matchDateTimeUTC") or match.get("matchDateTime")
        try:
            match_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            if match_date.tzinfo is None:
                match_date = match_date.replace(tzinfo=timezone.utc)
            date_label = match_date.astimezone(JAKARTA).isoformat()
        except (TypeError, ValueError, AttributeError):
            date_label = None

        home = match.get("team1") or {}
        away = match.get("team2") or {}
        rows.append(
            {
                "date": date_label,
                "round": (match.get("group") or {}).get("groupName", "Pertandingan"),
                "round_id": (match.get("group") or {}).get("groupOrderID"),
                "home": home.get("teamName", "Tim kandang"),
                "away": away.get("teamName", "Tim tandang"),
                "home_logo_url": _team_logo_url(home.get("teamIconUrl")),
                "away_logo_url": _team_logo_url(away.get("teamIconUrl")),
                "home_goals": home_score,
                "away_goals": away_score,
                "finished": bool(match.get("matchIsFinished")),
                "match_id": match.get("matchID"),
            }
        )
    return sorted(rows, key=lambda row: row.get("date") or "9999")


def _to_int(value, default=0):
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


_ALLOWED_LOGO_HOSTS = {
    "upload.wikimedia.org",
    "img.uefa.com",
    "i.imgur.com",
    "assets.dfb.de",
    "mediadb.kicker.de",
    "s.hs-data.com",
    "ssl.gstatic.com",
    "www.bundesliga-reisefuehrer.de",
    "preview.redd.it",
}


def _team_logo_url(value, allow_embedded: bool = False) -> str | None:
    """Prefer Wikimedia/approved API hosts; accept small API-inline icons as last resort."""
    if not isinstance(value, str):
        return None
    if allow_embedded and value.startswith("data:image/") and len(value) <= 300_000:
        try:
            header, encoded = value.split(",", 1)
            media_type = header[5:].split(";", 1)[0].lower()
            if media_type not in {"image/png", "image/jpeg", "image/webp"} or "base64" not in header:
                return None
            decoded = base64.b64decode(encoded, validate=True)
            if decoded and len(decoded) <= 200_000:
                return f"data:{media_type};base64,{encoded}"
        except (ValueError, binascii.Error):
            return None
    if not value.startswith(("http://", "https://")):
        return None
    parsed = urlparse(value)
    if parsed.hostname not in _ALLOWED_LOGO_HOSTS or not parsed.path:
        return None
    # Preserve only the signed/display query parameters Reddit needs; other
    # API-provided image URLs are normalized to a clean path.
    query = ""
    if parsed.hostname == "preview.redd.it":
        allowed_query = {"width", "height", "crop", "format", "auto", "s"}
        safe_params = [(key, val) for key, val in parse_qsl(parsed.query, keep_blank_values=False) if key in allowed_query]
        query = urlencode(safe_params)
    suffix = f"?{query}" if query else ""
    return f"https://{parsed.hostname}{parsed.path}{suffix}"


def _normalize_standings(rows: list[dict]) -> list[dict]:
    clean = []
    for row in rows:
        clean.append(
            {
                "team_id": row.get("teamInfoId"),
                "team": row.get("teamName", "Tim"),
                "short_name": row.get("shortName") or row.get("teamName", "Tim"),
                "logo_url": _team_logo_url(row.get("teamIconUrl"), allow_embedded=True),
                "played": _to_int(row.get("matches")),
                "won": _to_int(row.get("won")),
                "draw": _to_int(row.get("draw")),
                "lost": _to_int(row.get("lost")),
                "goals_for": _to_int(row.get("goals")),
                "goals_against": _to_int(row.get("opponentGoals")),
                "goal_diff": _to_int(row.get("goalDiff")),
                "points": _to_int(row.get("points")),
            }
        )
    return sorted(clean, key=lambda row: (row["points"], row["goal_diff"], row["goals_for"]), reverse=True)


def _normalize_scorers(rows: list[dict]) -> list[dict]:
    clean = [
        {
            "player_id": row.get("goalGetterId"),
            "name": row.get("goalGetterName", "Pemain"),
            "goals": _to_int(row.get("goalCount")),
        }
        for row in rows
    ]
    return sorted(clean, key=lambda row: row["goals"], reverse=True)


def _load_competition_from_api(shortcut: str, season: int) -> dict:
    """Fetch all provider payloads, normalize in memory, and return clean data."""
    raw_matches = _fetch_json(f"getmatchdata/{shortcut}/{season}")
    raw_standings = _fetch_json(f"getbltable/{shortcut}/{season}")
    try:
        raw_scorers = _fetch_json(f"getgoalgetters/{shortcut}/{season}")
    except requests.RequestException:
        raw_scorers = []

    return {
        "matches": _normalize_matches(raw_matches),
        "standings": _normalize_standings(raw_standings),
        "scorers": _normalize_scorers(raw_scorers),
        "source": "live",
        "warning": None,
    }


def get_competition(shortcut: str, season: int, refresh: bool = False) -> dict:
    """Fetch live API data and return only normalized dashboard records."""
    try:
        return _cached_normalized(
            f"competition:{shortcut}:{season}",
            lambda: _load_competition_from_api(shortcut, season),
            refresh=refresh,
        )
    except requests.RequestException as api_error:
        raise DataSourceError(str(api_error)) from api_error
