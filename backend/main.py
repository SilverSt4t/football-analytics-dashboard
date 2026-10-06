"""REST API for the Touchline football dashboard."""

import threading
import time
from urllib.parse import urlparse

import requests
from fastapi import FastAPI, HTTPException, Path as PathParam, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.get_data import DataSourceError, get_competition, get_leagues

app = FastAPI(
    title="Touchline Football Data API",
    description="Backend API that serves football data from OpenLigaDB to the Streamlit frontend.",
    version="1.0.0",
)

# Read-only endpoints; permissive CORS also allows experimenting with the API
# from a separate local frontend. The Streamlit app itself calls it server-side.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

_LOGO_CACHE_TTL = 86_400
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
_logo_cache: dict[str, tuple[float, bytes, str]] = {}
_logo_lock = threading.Lock()


@app.get("/", tags=["Status"])
def root():
    return {
        "service": "Touchline Football Data API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Status"])
def health():
    return {"status": "ok", "data_provider": "OpenLigaDB"}


@app.get("/api/leagues/{season}", tags=["Football data"])
def leagues(season: int = PathParam(ge=2000, le=2100), refresh: bool = False):
    try:
        return get_leagues(season, refresh=refresh)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gagal mengambil daftar kompetisi: {exc}") from exc


@app.get("/api/competitions/{shortcut}/{season}", tags=["Football data"])
def competition(
    shortcut: str,
    season: int = PathParam(ge=2000, le=2100),
    refresh: bool = False,
):
    try:
        return get_competition(shortcut, season, refresh=refresh)
    except DataSourceError as exc:
        raise HTTPException(status_code=502, detail=f"Sumber data sedang tidak tersedia: {exc}") from exc


@app.get("/api/assets/team-logo", tags=["Assets"])
def team_logo(url: str = Query(..., min_length=10, max_length=2000)):
    """Safely proxy Wikimedia and approved API-provided team-logo hosts."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_LOGO_HOSTS or not parsed.path.startswith("/"):
        raise HTTPException(status_code=400, detail="Sumber logo tidak diizinkan.")

    now = time.monotonic()
    with _logo_lock:
        cached = _logo_cache.get(url)
        if cached and cached[0] > now:
            _, content, media_type = cached
            return Response(content=content, media_type=media_type, headers={"Cache-Control": "public, max-age=86400"})

    request_headers = {"User-Agent": "TouchlineDashboard/1.0 (+https://api.openligadb.de/)"}
    if parsed.hostname == "upload.wikimedia.org":
        # Wikimedia's robot policy requires a recognizable requester and a
        # page referer for direct media requests.
        request_headers["Referer"] = "https://en.wikipedia.org/"

    try:
        response = requests.get(
            url,
            timeout=12,
            allow_redirects=True,
            headers=request_headers,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Logo tidak dapat diambil dari sumber yang disetujui.") from exc

    final_host = urlparse(response.url).hostname
    media_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if final_host not in _ALLOWED_LOGO_HOSTS or not media_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Respons sumber logo bukan gambar yang valid.")
    content = response.content
    if len(content) > 2_000_000:
        raise HTTPException(status_code=413, detail="Ukuran logo melebihi batas 2 MB.")

    with _logo_lock:
        _logo_cache[url] = (time.monotonic() + _LOGO_CACHE_TTL, content, media_type)
    return Response(content=content, media_type=media_type, headers={"Cache-Control": "public, max-age=86400"})
