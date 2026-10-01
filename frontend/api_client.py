"""HTTP client used by the Streamlit frontend to talk to the FastAPI backend."""

from __future__ import annotations

import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


class BackendUnavailable(RuntimeError):
    """Raised when the Streamlit frontend cannot reach the backend service."""


def _get(path: str, params: dict | None = None):
    try:
        response = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise BackendUnavailable(
            f"Backend tidak dapat dihubungi di {BACKEND_URL}. Pastikan service backend berjalan. ({exc})"
        ) from exc


@st.cache_data(ttl=900, show_spinner=False)
def get_leagues(season: int, refresh: bool = False):
    return _get(f"/api/leagues/{season}", params={"refresh": str(refresh).lower()})


@st.cache_data(ttl=900, show_spinner=False)
def get_competition(shortcut: str, season: int, refresh: bool = False):
    return _get(
        f"/api/competitions/{shortcut}/{season}",
        params={"refresh": str(refresh).lower()},
    )


@st.cache_data(ttl=86_400, max_entries=200, show_spinner=False)
def _fetch_team_logo_data_uri(image_url: str):
    """Fetch and cache a trusted remote logo via the backend proxy."""
    response = requests.get(
        f"{BACKEND_URL}/api/assets/team-logo",
        params={"url": image_url},
        timeout=15,
    )
    response.raise_for_status()
    media_type = response.headers.get("content-type", "image/png").split(";")[0]
    import base64

    encoded = base64.b64encode(response.content).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def get_team_logo_data_uri(image_url: str):
    """Return API-inline images directly; proxy and cache remote trusted logos."""
    if isinstance(image_url, str) and image_url.startswith("data:image/"):
        return image_url
    if not isinstance(image_url, str) or not image_url.startswith("https://"):
        return None
    try:
        return _fetch_team_logo_data_uri(image_url)
    except requests.RequestException:
        # Exceptions are deliberately caught outside the cached function so a
        # temporary proxy/network error is not cached as a missing logo.
        return None
