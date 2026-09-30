"""REST API for the Touchline football dashboard."""

from fastapi import FastAPI, HTTPException, Path as PathParam
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
