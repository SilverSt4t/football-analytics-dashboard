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
