"""API-only data client for the Touchline backend.

The provider's JSON is parsed in memory, normalized, and discarded. Only the
normalized response is kept in the short-lived memory cache; no raw data files
or manually entered datasets are read or written.
"""

from __future__ import annotations

import copy
import threading
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

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


def _normalize_leagues(rows: list[dict]) -> list[dict]:
    clean = []
    for row in rows:
        sport = row.get("sport") or {}
        clean.append(
            {
                "leagueShortcut": row.get("leagueShortcut", ""),
                "leagueName": row.get("leagueName", "Kompetisi"),
                "leagueSeason": row.get("leagueSeason"),
                "sport": sport.get("sportName", "Fußball") if isinstance(sport, dict) else str(sport),
            }
        )
    return clean


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


def _normalize_standings(rows: list[dict]) -> list[dict]:
    clean = []
    for row in rows:
        clean.append(
            {
                "team_id": row.get("teamInfoId"),
                "team": row.get("teamName", "Tim"),
                "short_name": row.get("shortName") or row.get("teamName", "Tim"),
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
