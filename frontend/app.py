from __future__ import annotations

from html import escape
import math

import pandas as pd
import streamlit as st

from api_client import BackendUnavailable, get_competition, get_leagues, get_team_logo_data_uri


# -----------------------------------------------------------------------------
# App configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Touchline | Football Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SEASON_OPTIONS = [2026, 2025, 2024, 2023]
TEAM_LOGOS = {}
force_refresh = bool(st.session_state.pop("force_refresh", False))


# -----------------------------------------------------------------------------
# Visual system
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink:#f3f6fb; --muted:#8491a5; --green:#8cf28a; --panel:#111c2c; --line:#233149; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp { background: radial-gradient(ellipse at 82% 0%, rgba(24,81,65,.20), transparent 32%), #08111d; color:var(--ink); }
    [data-testid="stHeader"] { background:rgba(8,17,29,.72); }
    [data-testid="stSidebar"] { background:#0b1523; border-right:1px solid #1b2a3d; }
    [data-testid="stSidebar"] > div:first-child { padding-top:1.1rem; }
    .block-container { padding-top:2rem; padding-bottom:2.6rem; max-width:1480px; }
    h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.035em; color:#f3f6fb !important; }
    p, label, .stMarkdown { color:#c5cfdd; }
    [data-testid="stMetric"] { background:linear-gradient(145deg,#111d2d,#0d1827); border:1px solid #203149; padding:18px 20px; border-radius:16px; min-height:112px; }
    [data-testid="stMetricLabel"] { color:#9aa8bb !important; font-size:.83rem; }
    [data-testid="stMetricValue"] { color:#f5f8fc !important; font-family:'Space Grotesk',sans-serif; }
    [data-testid="stMetricDelta"] { color:#8cf28a !important; }
    div[data-testid="stSelectbox"] label, div[data-testid="stTextInput"] label { color:#9aa8bb; }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    div[data-testid="stTextInput"] input { background:#101b2b; border-color:#283850; border-radius:10px; color:#eef4fb; }
    .stButton button { background:#101b2b; color:#c5cfdd; border:1px solid #293a52; border-radius:10px; font-weight:650; min-height:42px; transition:all .18s ease; }
    .stButton button[kind="primary"], .stButton button[data-testid="baseButton-primary"] { background:#8cf28a !important; color:#0b1721 !important; border:1px solid #8cf28a !important; font-weight:750; }
    .stButton button[kind="secondary"]:hover, .stButton button[data-testid="baseButton-secondary"]:hover { background:#17263a; color:#f3f6fb; border-color:#6aa978; }
    div[data-testid="stRadio"] label { color:#c8d3e0; }
    [data-testid="stDataFrame"] { border:1px solid #203149; border-radius:12px; overflow:hidden; }
    hr { border-color:#203149 !important; }
    .brand { font:700 1.25rem 'Space Grotesk',sans-serif; letter-spacing:-.04em; color:#f3f6fb; padding:4px 2px 10px; }
    .brand > span:not(.brand-mark) { color:#8cf28a; }
    .brand-mark { display:inline-flex; width:31px; height:31px; border-radius:10px; align-items:center; justify-content:center; background:#8cf28a; color:#09151c; margin-right:9px; font-size:18px; vertical-align:middle; }
    .brand-tagline { color:#8292a8; font-size:.78rem; margin:-4px 0 16px 42px; }
    .nav-caption { color:#8292a8; font-size:.72rem; margin:2px 0 8px 3px; letter-spacing:.08em; text-transform:uppercase; }
    .hero { display:flex; align-items:flex-start; justify-content:space-between; gap:18px; padding:4px 0 20px; }
    .eyebrow { color:#8cf28a; text-transform:uppercase; letter-spacing:.14em; font-size:.72rem; font-weight:700; margin-bottom:7px; }
    .hero-title { font:700 2.25rem 'Space Grotesk',sans-serif; letter-spacing:-.055em; color:#f5f8fc; line-height:1.05; }
    .hero-sub { color:#92a1b5; margin-top:8px; font-size:.95rem; }
    .source-pill { border:1px solid #284234; background:rgba(140,242,138,.08); color:#9cf19c; padding:8px 12px; border-radius:999px; font-size:.78rem; font-weight:600; white-space:nowrap; margin-top:7px; }
    .section-label { color:#8d9cb0; text-transform:uppercase; letter-spacing:.12em; font-size:.72rem; font-weight:700; margin:8px 0 12px; }
    .panel { background:linear-gradient(145deg,#111d2d,#0d1827); border:1px solid #203149; border-radius:16px; padding:16px 18px; }
    .match-card { background:linear-gradient(145deg,#111d2d,#0e1928); border:1px solid #22324a; border-radius:14px; padding:14px 16px; margin:0 0 10px 0; }
    .match-meta { display:flex; justify-content:space-between; color:#8796aa; font-size:.75rem; margin-bottom:11px; }
    .match-row { display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:12px; }
    .match-team { color:#edf3fa; font-weight:600; font-size:.92rem; }
    .match-away { text-align:right; }
    .match-score { color:#fff; font:700 1.12rem 'Space Grotesk',sans-serif; background:#1c2a3d; border:1px solid #30425a; border-radius:9px; padding:7px 12px; min-width:66px; text-align:center; }
    .match-vs { color:#718096; font-size:.78rem; font-weight:700; padding:0 12px; }
    .team-dot { display:inline-flex; width:28px; height:28px; border-radius:50%; background:#1d3241; color:#a4f59e; align-items:center; justify-content:center; font-size:.65rem; font-weight:700; margin-right:8px; flex:0 0 auto; }
    .team-logo { width:29px; height:29px; object-fit:contain; background:#f8fafc; border-radius:50%; padding:3px; margin-right:8px; vertical-align:middle; flex:0 0 auto; }
    .team-logo-away { margin-right:0; margin-left:8px; }
    .spotlight-title { display:flex; align-items:center; gap:8px; color:#f4f7fb; font:600 1rem 'Space Grotesk',sans-serif; margin:2px 0 9px; }
    .form-strip { display:flex; gap:7px; align-items:center; margin:8px 0 14px; }
    .form-chip { display:inline-flex; width:29px; height:29px; border-radius:9px; align-items:center; justify-content:center; font-size:.72rem; font-weight:800; color:#07131d; }
    .form-W { background:#8cf28a; } .form-D { background:#facc72; } .form-L { background:#fb7185; }
    .callout { background:rgba(140,242,138,.06); border:1px solid rgba(140,242,138,.18); border-radius:13px; color:#bfd0c3; padding:12px 15px; font-size:.82rem; }
    .sidebar-note { color:#708097; font-size:.72rem; line-height:1.5; }
    .empty { padding:26px; border:1px dashed #31435b; border-radius:14px; color:#91a0b4; text-align:center; }
    .visual-card { background:linear-gradient(145deg,rgba(17,29,45,.92),rgba(10,22,36,.95)); border:1px solid #22344c; border-radius:15px; padding:16px 17px; }
    .visual-card-sub { color:#8191a7; font-size:.77rem; margin:-2px 0 14px; }
    .outcome-stack { height:14px; display:flex; overflow:hidden; border-radius:999px; background:#1c2b3e; margin:12px 0 18px; }
    .outcome-segment { height:100%; min-width:2px; }
    .outcome-legend { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px; }
    .outcome-item { background:rgba(255,255,255,.025); border:1px solid #22334a; border-radius:11px; padding:11px 12px; }
    .outcome-label { display:flex; gap:7px; align-items:center; color:#9aa9bc; font-size:.72rem; }
    .outcome-dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
    .outcome-value { color:#f2f6fb; font:700 1.15rem 'Space Grotesk',sans-serif; margin-top:5px; }
    .chart-list { display:flex; flex-direction:column; gap:12px; padding:5px 1px 3px; }
    .chart-row { min-width:0; }
    .chart-row-head { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:6px; }
    .chart-label { color:#c9d4e2; font-size:.82rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .chart-value { color:#f5f8fc; font:700 .82rem 'Space Grotesk',sans-serif; white-space:nowrap; }
    .chart-track { position:relative; height:8px; background:#1b293b; border-radius:999px; overflow:hidden; }
    .chart-fill { height:100%; border-radius:999px; box-shadow:0 0 12px rgba(140,242,138,.25); }
    .trend-svg { display:block; width:100%; height:auto; overflow:visible; }
    .trend-grid { stroke:#25354b; stroke-width:1; stroke-dasharray:3 5; }
    .trend-axis-label { fill:#7f8fa5; font:11px 'DM Sans',sans-serif; }
    .trend-point-label { fill:#dce7f3; font:600 10px 'DM Sans',sans-serif; }
    .standings-scroll { width:100%; overflow:auto; border-radius:13px; }
    .standings-table { width:100%; min-width:660px; border-collapse:separate; border-spacing:0 5px; color:#dce5f0; font-size:.8rem; }
    .standings-table.compact { min-width:500px; }
    .standings-table.compact .table-team { min-width:140px; }
    .standings-table th { padding:8px 9px; text-align:right; color:#8292a7; text-transform:uppercase; font-size:.65rem; letter-spacing:.09em; font-weight:700; }
    .standings-table th:nth-child(2) { text-align:left; }
    .standings-table td { padding:9px; text-align:right; background:#111d2c; border-top:1px solid #203149; border-bottom:1px solid #203149; white-space:nowrap; }
    .standings-table td:first-child { border-left:1px solid #203149; border-radius:10px 0 0 10px; text-align:center; }
    .standings-table td:last-child { border-right:1px solid #203149; border-radius:0 10px 10px 0; }
    .standings-table tr.rank-top td { background:linear-gradient(90deg,rgba(140,242,138,.075),#111d2c 58%); }
    .standings-table tr.rank-bottom td { background:linear-gradient(90deg,rgba(251,113,133,.055),#111d2c 58%); }
    .rank-badge { display:inline-flex; width:27px; height:27px; align-items:center; justify-content:center; border-radius:9px; background:#1e2c3f; color:#c8d4e2; font-weight:800; }
    .rank-top .rank-badge { background:rgba(140,242,138,.14); color:#a8ffa2; }
    .rank-bottom .rank-badge { background:rgba(251,113,133,.12); color:#fb9aaa; }
    .table-team { display:flex; align-items:center; gap:9px; text-align:left; min-width:175px; }
    .table-team img,.table-team .team-dot { width:27px; height:27px; object-fit:contain; border-radius:50%; background:#f8fafc; padding:3px; flex:0 0 auto; }
    .table-team .team-dot { display:inline-flex; background:#1d3241; color:#a4f59e; font-size:.62rem; align-items:center; justify-content:center; padding:0; }
    .table-team-name { display:flex; flex-direction:column; gap:2px; }
    .table-team-name strong { color:#f2f6fb; font-size:.78rem; font-weight:650; }
    .table-team-name small { color:#76869b; font-size:.66rem; }
    .points-cell { min-width:72px; }
    .points-track { height:4px; background:#26354a; border-radius:99px; margin-top:5px; overflow:hidden; }
    .points-track span { display:block; height:100%; border-radius:99px; background:linear-gradient(90deg,#3ba976,#8cf28a); }
    .scorer-board { display:flex; flex-direction:column; gap:8px; }
    .scorer-row { display:grid; grid-template-columns:30px 38px minmax(0,1fr) 50px; gap:9px; align-items:center; padding:10px 12px; background:linear-gradient(100deg,#142235,#101b2b); border:1px solid #203149; border-radius:12px; }
    .scorer-rank { width:27px; height:27px; border-radius:9px; display:flex; align-items:center; justify-content:center; background:#1d2d41; color:#9eafc3; font-size:.72rem; font-weight:800; }
    .scorer-row:nth-child(1) .scorer-rank { background:rgba(255,205,94,.16); color:#ffd166; }
    .scorer-row:nth-child(2) .scorer-rank { background:rgba(193,207,222,.13); color:#d4deea; }
    .scorer-row:nth-child(3) .scorer-rank { background:rgba(222,150,94,.14); color:#e6a46c; }
    .player-avatar { display:inline-flex; flex:0 0 auto; align-items:center; justify-content:center; width:32px; height:32px; overflow:hidden; border:1px solid rgba(157,246,197,.35); border-radius:50%; background:#173c48; box-shadow:0 0 16px rgba(72,196,145,.12); }
    .player-avatar svg { display:block; width:100%; height:100%; }
    .player-avatar-sm { width:29px; height:29px; }
    .player-avatar-lg { width:56px; height:56px; border-width:2px; }
    .player-profile { display:flex; align-items:center; gap:13px; padding:12px 0 15px; }
    .player-profile-main { display:flex; flex-direction:column; gap:5px; min-width:0; }
    .player-profile-name { color:#f3f7fc; font:700 1.08rem 'Space Grotesk',sans-serif; }
    .chart-label-with-avatar { display:flex; align-items:center; gap:8px; min-width:0; }
    .scorer-main { min-width:0; }
    .scorer-name { color:#e7eef7; font-weight:650; font-size:.83rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .scorer-track { height:5px; margin-top:7px; background:#25344a; border-radius:99px; overflow:hidden; }
    .scorer-track span { display:block; height:100%; border-radius:99px; background:linear-gradient(90deg,#36a66b,#8cf28a); }
    .scorer-goals { color:#f5f8fc; font:700 1rem 'Space Grotesk',sans-serif; text-align:right; }
    .player-id-pill { display:inline-flex; align-items:center; border:1px solid #2b4059; border-radius:999px; padding:6px 10px; color:#9fb0c5; background:#101b2b; font-size:.72rem; }
    @media (max-width: 700px) { .hero-title { font-size:1.7rem; } .source-pill { font-size:.68rem; } .outcome-legend { grid-template-columns:1fr; } }
    </style>
    """,
    unsafe_allow_html=True,
)


def team_initials(name: str) -> str:
    words = [word for word in str(name).replace("FC ", "").split() if word]
    return "".join(word[0] for word in words[:2]).upper() or "FC"


def player_avatar_html(name: str, size: str = "sm") -> str:
    safe_name = escape(str(name), quote=True)
    face_icon = (
        '<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false">'
        '<circle cx="16" cy="16" r="15" fill="#173c48"/>'
        '<path d="M7.5 13.8c0-6.1 3.4-9.8 8.5-9.8s8.5 3.7 8.5 9.8v4.1c0 5-3.7 9-8.5 9s-8.5-4-8.5-9z" fill="#d6f4e5"/>'
        '<path d="M7.6 13.8c.2-6.1 3.4-9.7 8.4-9.7 5.2 0 8.3 3.7 8.4 9.5-2.2-.5-4.1-1.7-5.4-3.6-2.7 2.1-6.1 3.4-11.4 3.8z" fill="#8cf28a"/>'
        '<ellipse cx="12.5" cy="16.6" rx=".9" ry="1.2" fill="#18363c"/>'
        '<ellipse cx="19.5" cy="16.6" rx=".9" ry="1.2" fill="#18363c"/>'
        '<path d="M13 21c1.8 1.6 4.2 1.6 6 0" fill="none" stroke="#43836d" stroke-width="1.2" stroke-linecap="round"/>'
        '</svg>'
    )
    return f'<span class="player-avatar player-avatar-{size}" title="{safe_name}" aria-label="Ikon wajah pemain {safe_name}">{face_icon}</span>'


def team_identity_html(name: str, logo_url: str | None = None, side: str = "home") -> str:
    safe_name = escape(str(name))
    if isinstance(logo_url, str) and logo_url.startswith("data:image/"):
        logo_data = logo_url
    elif logo_url:
        logo_data = get_team_logo_data_uri(logo_url)
    else:
        logo_data = None
    if logo_data:
        side_class = " team-logo-away" if side == "away" else ""
        avatar = f'<img class="team-logo{side_class}" src="{logo_data}" alt="Logo {safe_name}" title="{safe_name}">'
    else:
        initials = team_initials(name)
        side_style = " style=\"margin:0 0 0 8px\"" if side == "away" else ""
        avatar = f'<span class="team-dot"{side_style}>{escape(initials)}</span>'
    if side == "away":
        return f'{safe_name}{avatar}'
    return f'{avatar}{safe_name}'


def render_outcome_chart(home_wins: int, draws: int, away_wins: int):
    items = [
        ("Menang kandang", int(home_wins), "#8cf28a"),
        ("Seri", int(draws), "#facc72"),
        ("Menang tandang", int(away_wins), "#60c8f5"),
    ]
    total = sum(value for _, value, _ in items)
    if total == 0:
        st.info("Belum ada hasil untuk rentang ini.")
        return
    segments = "".join(
        f'<span class="outcome-segment" style="width:{value / total * 100:.2f}%;background:{color}" title="{label}: {value}"></span>'
        for label, value, color in items
    )
    legend = "".join(
        f'<div class="outcome-item"><div class="outcome-label"><span class="outcome-dot" style="background:{color}"></span>{label}</div>'
        f'<div class="outcome-value">{value} <small style="color:#8292a7;font:500 .72rem DM Sans,sans-serif">{value / total * 100:.0f}%</small></div></div>'
        for label, value, color in items
    )
    st.markdown(
        f'<div class="visual-card"><div class="visual-card-sub">{total} pertandingan selesai</div>'
        f'<div class="outcome-stack">{segments}</div><div class="outcome-legend">{legend}</div></div>',
        unsafe_allow_html=True,
    )


def render_trend_chart(data: pd.DataFrame, label_col: str, value_col: str):
    labels = data[label_col].astype(str).tolist()
    values = pd.to_numeric(data[value_col], errors="coerce").fillna(0).astype(float).tolist()
    if not values:
        st.info("Belum ada data tren untuk divisualisasikan.")
        return

    width, height = 820, 280
    left, right, top, bottom = 46, 20, 20, 38
    plot_width, plot_height = width - left - right, height - top - bottom
    max_value = max(values) or 1.0
    points = []
    for index, value in enumerate(values):
        x = left + (plot_width * index / max(1, len(values) - 1))
        y = top + plot_height * (1 - value / max_value)
        points.append((x, y))

    baseline = top + plot_height
    line_path = " ".join(("M" if index == 0 else "L") + f"{x:.1f},{y:.1f}" for index, (x, y) in enumerate(points))
    area_path = f"{line_path} L{points[-1][0]:.1f},{baseline:.1f} L{points[0][0]:.1f},{baseline:.1f} Z"
    grid = []
    for tick in range(4):
        value = max_value * tick / 3
        y = top + plot_height * (1 - tick / 3)
        label = f"{value:.0f}" if float(value).is_integer() else f"{value:.1f}"
        grid.append(f'<line class="trend-grid" x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}"/><text class="trend-axis-label" x="{left-9}" y="{y+4:.1f}" text-anchor="end">{label}</text>')

    label_step = max(1, math.ceil((len(labels) - 1) / 5))
    x_labels = []
    for index in range(0, len(labels), label_step):
        x, _ = points[index]
        x_labels.append(f'<text class="trend-axis-label" x="{x:.1f}" y="{height-8}" text-anchor="middle">{escape(labels[index])}</text>')
    if len(labels) > 1 and (len(labels) - 1) % label_step:
        x, _ = points[-1]
        x_labels.append(f'<text class="trend-axis-label" x="{x:.1f}" y="{height-8}" text-anchor="end">{escape(labels[-1])}</text>')

    circles = []
    for (x, y), label, value in zip(points, labels, values):
        display_value = f"{value:.2f}" if not value.is_integer() else f"{int(value)}"
        circles.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#091622" stroke="#a8ffa2" stroke-width="2">'
            f'<title>{escape(label)} · {display_value}</title></circle>'
        )
    svg = (
        f'<svg class="trend-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Tren gol per pekan">'
        '<defs><linearGradient id="touchlineTrendFill" x1="0" x2="0" y1="0" y2="1">'
        '<stop offset="0%" stop-color="#8cf28a" stop-opacity=".30"/><stop offset="100%" stop-color="#8cf28a" stop-opacity=".01"/>'
        '</linearGradient></defs>'
        f'{"".join(grid)}<path d="{area_path}" fill="url(#touchlineTrendFill)"/>'
        f'<path d="{line_path}" fill="none" stroke="#8cf28a" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
        f'{"".join(circles)}{"".join(x_labels)}</svg>'
    )
    st.markdown(f'<div class="visual-card">{svg}</div>', unsafe_allow_html=True)


def render_bar_list(data: pd.DataFrame, label_col: str, value_col: str, unit: str = "", highlight: str | None = None, player_icons: bool = False):
    if data.empty:
        st.info("Belum ada data untuk dibandingkan.")
        return
    records = []
    for _, row in data.iterrows():
        try:
            value = float(row[value_col])
        except (TypeError, ValueError):
            continue
        records.append((str(row[label_col]), value))
    if not records:
        st.info("Belum ada data untuk dibandingkan.")
        return
    maximum = max(abs(value) for _, value in records) or 1.0
    signed = min(value for _, value in records) < 0
    lines = []
    for label, value in records:
        shown = f"{value:+g}" if signed else f"{value:g}"
        if signed:
            percentage = min(50, abs(value) / maximum * 50)
            left = 50 if value >= 0 else 50 - percentage
            color = "#8cf28a" if value >= 0 else "#fb7185"
        else:
            percentage = min(100, max(0, value / maximum * 100))
            left, color = 0, "#8cf28a"
        if highlight is not None:
            color = "#60c8f5" if label == highlight else ("#fb7185" if value < 0 else "#456b5b")
        label_markup = (
            f'<span class="chart-label-with-avatar">{player_avatar_html(label)}<span class="chart-label">{escape(label)}</span></span>'
            if player_icons else f'<span class="chart-label">{escape(label)}</span>'
        )
        zero_axis = '<span style="position:absolute;left:50%;top:0;height:100%;width:1px;background:#4b5d73"></span>' if signed else ""
        lines.append(
            f'<div class="chart-row"><div class="chart-row-head">{label_markup}'
            f'<span class="chart-value">{shown}{escape(unit)}</span></div>'
            f'<div class="chart-track"><div class="chart-fill" style="position:absolute;left:{left:.1f}%;width:{percentage:.1f}%;background:linear-gradient(90deg,{color}99,{color})"></div>'
            f'{zero_axis}</div></div>'
        )
    st.markdown(f'<div class="visual-card"><div class="chart-list">{"".join(lines)}</div></div>', unsafe_allow_html=True)


def render_standings_table(data: pd.DataFrame, compact: bool = False):
    if data.empty:
        st.info("Klasemen belum tersedia.")
        return
    rows = data.reset_index(drop=True)
    maximum_points = max(1, int(pd.to_numeric(rows["points"], errors="coerce").fillna(0).max()))
    headings = ["#", "Tim", "Main", "SG", "Poin"] if compact else ["#", "Tim", "Main", "M", "S", "K", "GM", "GK", "SG", "Poin"]
    header = "".join(f"<th>{escape(label)}</th>" for label in headings)
    body = []
    for position, (_, row) in enumerate(rows.iterrows(), start=1):
        total_rows = len(rows)
        row_class = "rank-top" if position <= 4 else ("rank-bottom" if not compact and position > total_rows - 3 else "")
        team = str(row.get("team", "Tim"))
        short_name = str(row.get("short_name", team))
        logo_url = row.get("logo_url")
        logo = logo_url if isinstance(logo_url, str) and logo_url.startswith("data:image/") else get_team_logo_data_uri(logo_url) if isinstance(logo_url, str) and logo_url else None
        if logo:
            avatar = f'<img src="{escape(logo, quote=True)}" alt="" loading="lazy">'
        else:
            avatar = f'<span class="team-dot">{escape(team_initials(team))}</span>'
        team_cell = f'<div class="table-team">{avatar}<span class="table-team-name"><strong>{escape(short_name)}</strong><small>{escape(team)}</small></span></div>'
        points = int(row.get("points", 0) or 0)
        point_width = max(0, min(100, points / maximum_points * 100))
        cells = [f'<td><span class="rank-badge">{position}</span></td>', f'<td>{team_cell}</td>']
        if compact:
            values = [row.get("played", 0), row.get("goal_diff", 0)]
        else:
            values = [row.get("played", 0), row.get("won", 0), row.get("draw", 0), row.get("lost", 0), row.get("goals_for", 0), row.get("goals_against", 0), row.get("goal_diff", 0)]
        cells.extend(f"<td>{int(value or 0):+d}</td>" if label == "SG" else f"<td>{int(value or 0)}</td>" for label, value in zip(headings[2:-1], values))
        cells.append(f'<td class="points-cell"><strong>{points}</strong><div class="points-track"><span style="width:{point_width:.1f}%"></span></div></td>')
        body.append(f'<tr class="{row_class}">{"".join(cells)}</tr>')
    table_modifier = " compact" if compact else ""
    st.markdown(
        f'<div class="standings-scroll"><table class="standings-table{table_modifier}"><thead><tr>{header}</tr></thead><tbody>{"".join(body)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render_scorer_board(data: pd.DataFrame):
    if data.empty:
        st.info("Belum ada pencetak gol untuk ditampilkan.")
        return
    maximum = max(1, int(pd.to_numeric(data["goals"], errors="coerce").fillna(0).max()))
    rows = []
    for rank, (_, row) in enumerate(data.iterrows(), start=1):
        name = str(row.get("name", "Pemain"))
        goals = int(row.get("goals", 0) or 0)
        width = max(0, min(100, goals / maximum * 100))
        rows.append(
            f'<div class="scorer-row"><span class="scorer-rank">{rank:02d}</span>{player_avatar_html(name)}'
            f'<div class="scorer-main"><div class="scorer-name">{escape(name)}</div>'
            f'<div class="scorer-track"><span style="width:{width:.1f}%"></span></div></div>'
            f'<span class="scorer-goals">{goals}<small style="color:#8494a9;font:500 .65rem DM Sans,sans-serif"> gol</small></span></div>'
        )
    st.markdown(f'<div class="scorer-board">{"".join(rows)}</div>', unsafe_allow_html=True)


def render_match_card(row):
    date = row.get("date")
    date_label = date.strftime("%d %b %Y · %H:%M WIB") if pd.notna(date) else "Jadwal belum tersedia"
    round_label = row.get("round") or "Pertandingan"
    if row.get("finished") and pd.notna(row.get("home_goals")) and pd.notna(row.get("away_goals")):
        score_html = f'<div class="match-score">{int(row["home_goals"])} : {int(row["away_goals"])}</div>'
        status = "SELESAI"
    else:
        score_html = '<div class="match-vs">VS</div>'
        status = "AKAN DATANG"
    st.markdown(
        f"""<div class="match-card">
          <div class="match-meta"><span>{round_label}</span><span>{date_label} &nbsp; · &nbsp; {status}</span></div>
          <div class="match-row">
            <div class="match-team">{team_identity_html(row['home'], row.get('home_logo_url') or TEAM_LOGOS.get(row['home']), 'home')}</div>
            {score_html}
            <div class="match-team match-away">{team_identity_html(row['away'], row.get('away_logo_url') or TEAM_LOGOS.get(row['away']), 'away')}</div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def section_title(eyebrow: str, title: str, description: str = ""):
    st.markdown(f'<div class="section-label">{eyebrow}</div><h2 style="margin:0 0 5px">{title}</h2>', unsafe_allow_html=True)
    if description:
        st.caption(description)


# -----------------------------------------------------------------------------
# Main toolbar: keep selectors and primary navigation in the content area.
# -----------------------------------------------------------------------------
st.markdown(
    '<div class="brand"><span class="brand-mark">⚽</span>touchline<span>.</span></div>'
    '<div class="brand-tagline">Football insights, tersusun untuk fokus.</div>',
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.markdown('<div class="nav-caption">PILIH KOMPETISI</div>', unsafe_allow_html=True)
    season_col, competition_col, refresh_col = st.columns([0.9, 2.1, 0.85], vertical_alignment="bottom")
    with season_col:
        season = st.selectbox(
            "Musim",
            SEASON_OPTIONS,
            index=0,
            format_func=lambda year: f"{year}/{year + 1}",
            key="season_choice",
        )

    try:
        # The curated catalog is filtered by actual availability in OpenLigaDB.
        league_rows = get_leagues(season, refresh=force_refresh)
    except BackendUnavailable as exc:
        st.error(f"Tidak dapat mengambil daftar kompetisi dari backend: {exc}")
        st.stop()

    if not league_rows:
        st.error("API tidak mengembalikan daftar kompetisi untuk musim ini.")
        st.stop()

    league_codes = [row["leagueShortcut"] for row in league_rows]
    default_code = "pl" if "pl" in league_codes else ("bl1" if "bl1" in league_codes else league_codes[0])
    remembered_code = st.session_state.get("competition_choice")
    if remembered_code not in league_codes:
        st.session_state.pop("competition_choice", None)
        remembered_code = None
    selected_default = remembered_code or default_code
    with competition_col:
        selected_code = st.selectbox(
            "Kompetisi",
            league_codes,
            index=league_codes.index(selected_default),
            format_func=lambda code: next((row.get("leagueName", code) for row in league_rows if row.get("leagueShortcut") == code), code),
            key="competition_choice",
        )
    with refresh_col:
        st.markdown("<div style='height:1.65rem'></div>", unsafe_allow_html=True)
        if st.button("↻  Muat ulang", width="stretch", key="refresh_data"):
            st.cache_data.clear()
            st.session_state["force_refresh"] = True
            st.rerun()

st.markdown('<div class="nav-caption">NAVIGASI</div>', unsafe_allow_html=True)
page_items = [
    ("Ringkasan", "▦  Ringkasan"),
    ("Pertandingan", "⚽  Pertandingan"),
    ("Klasemen", "🏆  Klasemen"),
    ("Pencetak gol", "🥅  Pencetak gol"),
    ("Panel personal", "✦  Personal"),
]
page_options = [name for name, _ in page_items]
if st.session_state.get("active_page") not in page_options:
    st.session_state["active_page"] = "Ringkasan"
nav_columns = st.columns([1, 1.2, 1, 1.2, 1], gap="small")
for nav_index, (nav_column, (page_name, nav_label)) in enumerate(zip(nav_columns, page_items)):
    with nav_column:
        if st.button(
            nav_label,
            key=f"nav_page_{nav_index}",
            type="primary" if st.session_state["active_page"] == page_name else "secondary",
            width="stretch",
        ):
            st.session_state["active_page"] = page_name
            st.rerun()
page = st.session_state["active_page"]

selected_league = next((row for row in league_rows if row.get("leagueShortcut") == selected_code), {})
league_name = selected_league.get("leagueName", selected_code.upper())

with st.spinner("Mengambil data pertandingan melalui backend..."):
    try:
        payload = get_competition(selected_code, season, refresh=force_refresh)
        matches_df = pd.DataFrame(payload.get("matches", []))
        if "date" in matches_df.columns:
            matches_df["date"] = pd.to_datetime(matches_df["date"], errors="coerce")
        standings_df = pd.DataFrame(payload.get("standings", []))
        scorers_df = pd.DataFrame(payload.get("scorers", []))
        data_mode = payload.get("source", "live")
        data_error = payload.get("warning")
    except BackendUnavailable as exc:
        matches_df, standings_df, scorers_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        data_mode, data_error = "offline", str(exc)

if not standings_df.empty and "team" in standings_df.columns:
    TEAM_LOGOS = dict(zip(standings_df["team"], standings_df.get("logo_url", pd.Series([None] * len(standings_df)))))

if data_mode == "offline" and data_error:
    st.warning(f"Backend tidak dapat mengambil data: {data_error}")

source_label = "● DATA LIVE · OpenLigaDB" if data_mode == "live" else "○ API tidak tersedia"

# -----------------------------------------------------------------------------
# Page heading
# -----------------------------------------------------------------------------
st.markdown(
    f"""<div class="hero">
      <div><div class="eyebrow">FOOTBALL ANALYTICS · {season}/{season + 1}</div>
      <div class="hero-title">{league_name}</div>
      <div class="hero-sub">Pantau hasil, performa tim, dan cerita di balik angka.</div></div>
      <div class="source-pill">{source_label}</div>
    </div>""",
    unsafe_allow_html=True,
)

if matches_df.empty:
    st.markdown('<div class="empty">Data pertandingan belum tersedia untuk pilihan ini. Coba kompetisi atau musim lain.</div>', unsafe_allow_html=True)
    st.stop()

played_df = matches_df[matches_df["finished"] & matches_df["home_goals"].notna() & matches_df["away_goals"].notna()].copy()
played_df["total_goals"] = played_df["home_goals"].astype(float) + played_df["away_goals"].astype(float)
upcoming_df = matches_df[~matches_df["finished"]].copy()

total_goals = int(played_df["total_goals"].sum()) if not played_df.empty else 0
avg_goals = float(played_df["total_goals"].mean()) if not played_df.empty else 0.0
home_wins = int((played_df["home_goals"] > played_df["away_goals"]).sum()) if not played_df.empty else 0
draws = int((played_df["home_goals"] == played_df["away_goals"]).sum()) if not played_df.empty else 0
away_wins = int((played_df["home_goals"] < played_df["away_goals"]).sum()) if not played_df.empty else 0
home_win_pct = home_wins / len(played_df) * 100 if len(played_df) else 0

# -----------------------------------------------------------------------------
# Page: overview
# -----------------------------------------------------------------------------
if page == "Ringkasan":
    st.markdown('<div class="section-label">RINGKASAN KOMPETISI</div>', unsafe_allow_html=True)

    # Group 1: season KPIs and the selected analysis period.
    with st.container(border=True):
        st.subheader("1 · Ikhtisar musim")
        st.caption("Angka utama untuk kompetisi dan rentang waktu yang dipilih.")
        scope_col, _ = st.columns([1, 2])
        with scope_col:
            overview_scope = st.selectbox("Rentang statistik", ["Musim penuh", "5 pekan terakhir"], key="overview_scope")
        overview_df = played_df.copy()
        if overview_scope == "5 pekan terakhir" and not overview_df.empty:
            last_rounds = sorted(overview_df["round_id"].dropna().unique())[-5:]
            overview_df = overview_df[overview_df["round_id"].isin(last_rounds)]
        overview_goals = int(overview_df["total_goals"].sum()) if not overview_df.empty else 0
        overview_avg = float(overview_df["total_goals"].mean()) if not overview_df.empty else 0.0
        overview_home_wins = int((overview_df["home_goals"] > overview_df["away_goals"]).sum()) if not overview_df.empty else 0
        overview_draws = int((overview_df["home_goals"] == overview_df["away_goals"]).sum()) if not overview_df.empty else 0
        overview_away_wins = int((overview_df["home_goals"] < overview_df["away_goals"]).sum()) if not overview_df.empty else 0
        overview_home_pct = overview_home_wins / len(overview_df) * 100 if len(overview_df) else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Pertandingan selesai", f"{len(overview_df):,}")
        k2.metric("Total gol", f"{overview_goals:,}")
        k3.metric("Rata-rata gol / laga", f"{overview_avg:.2f}")
        k4.metric("Menang kandang", f"{overview_home_pct:.1f}%", f"{overview_home_wins} laga")

    # Group 2: outcomes and the next fixtures.
    with st.container(border=True):
        st.subheader("2 · Hasil & agenda")
        st.caption("Distribusi hasil pertandingan dan laga yang akan datang.")
        result_col, schedule_col = st.columns([1, 1.15], gap="large")
        with result_col:
            st.markdown('<div class="section-label">HASIL PERTANDINGAN</div>', unsafe_allow_html=True)
            if not overview_df.empty:
                render_outcome_chart(overview_home_wins, overview_draws, overview_away_wins)
            else:
                st.info("Belum ada pertandingan selesai untuk divisualisasikan.")
        with schedule_col:
            st.markdown('<div class="section-label">JADWAL BERIKUTNYA</div>', unsafe_allow_html=True)
            if upcoming_df.empty:
                st.markdown('<div class="empty">Semua pertandingan musim ini telah selesai.</div>', unsafe_allow_html=True)
            else:
                next_matches = upcoming_df.sort_values("date").head(4)
                for _, row in next_matches.iterrows():
                    render_match_card(row)

    # Group 3: league-level trends and standings preview.
    with st.container(border=True):
        st.subheader("3 · Tren & klasemen")
        st.caption("Bandingkan produktivitas gol dengan posisi tim teratas.")
        trend_col, standings_col = st.columns([1.1, 1], gap="large")
        with trend_col:
            st.markdown('<div class="section-label">TREN GOL PER PEKAN</div>', unsafe_allow_html=True)
            if not overview_df.empty:
                trend_mode = st.selectbox("Metrik tren", ["Total gol", "Rata-rata gol per laga"], key="trend_mode")
                trend = overview_df.groupby("round_id", dropna=True).agg(goals=("total_goals", "sum"), matches=("match_id", "count")).reset_index().sort_values("round_id")
                trend["week_label"] = trend["round_id"].apply(lambda x: f"P{x:g}" if pd.notna(x) else "-")
                if trend_mode == "Rata-rata gol per laga":
                    trend["metric_value"] = trend["goals"] / trend["matches"]
                else:
                    trend["metric_value"] = trend["goals"]
                render_trend_chart(trend, "week_label", "metric_value")
            else:
                st.info("Grafik akan muncul setelah pertandingan selesai.")
        with standings_col:
            st.markdown('<div class="section-label">5 TIM TERATAS</div>', unsafe_allow_html=True)
            if not standings_df.empty:
                top = standings_df.sort_values(["points", "goal_diff"], ascending=[False, False]).head(5).copy()
                render_standings_table(top, compact=True)
            else:
                st.info("Klasemen belum tersedia untuk kompetisi ini.")

# -----------------------------------------------------------------------------
# Page: matches
# -----------------------------------------------------------------------------
elif page == "Pertandingan":
    section_title("MATCH CENTRE", "Jadwal & hasil", "Gunakan filter, lalu buka grup pekan untuk melihat pertandingan.")
    with st.container(border=True):
        st.subheader("Filter pertandingan")
        f1, f2, f3 = st.columns([1.35, 1, 1])
        with f1:
            query = st.text_input("Cari tim", placeholder="Contoh: Arsenal")
        with f2:
            rounds = sorted([int(x) for x in matches_df["round_id"].dropna().unique()])
            round_choice = st.selectbox("Pekan", ["Semua pekan"] + rounds, format_func=lambda x: x if isinstance(x, str) else f"Pekan {x}")
        with f3:
            status_choice = st.selectbox("Status", ["Semua", "Selesai", "Akan datang"])

    filtered = matches_df.copy()
    if query.strip():
        filtered = filtered[filtered["home"].str.contains(query, case=False, na=False) | filtered["away"].str.contains(query, case=False, na=False)]
    if round_choice != "Semua pekan":
        filtered = filtered[filtered["round_id"] == round_choice]
    if status_choice == "Selesai":
        filtered = filtered[filtered["finished"]]
    elif status_choice == "Akan datang":
        filtered = filtered[~filtered["finished"]]

    st.caption(f"{len(filtered)} pertandingan cocok dengan filter · waktu Asia/Jakarta (WIB)")
    if filtered.empty:
        st.markdown('<div class="empty">Tidak ada pertandingan yang cocok dengan filter.</div>', unsafe_allow_html=True)
    else:
        visible = filtered.sort_values("date").head(30)
        if "round_id" in visible.columns and "round" in visible.columns:
            groups = list(visible.groupby(["round_id", "round"], dropna=False, sort=True))
            for index, ((round_id, round_name), match_group) in enumerate(groups):
                label = "Pertandingan" if pd.isna(round_name) else str(round_name)
                if pd.notna(round_id):
                    label = f"Pekan {int(round_id)} · {label}"
                with st.expander(f"{label} · {len(match_group)} pertandingan", expanded=(index == 0)):
                    for _, row in match_group.iterrows():
                        render_match_card(row)
        else:
            for _, row in visible.iterrows():
                render_match_card(row)
        if len(filtered) > len(visible):
            st.caption(f"Menampilkan {len(visible)} dari {len(filtered)} pertandingan. Persempit pencarian untuk melihat laga lainnya.")

# -----------------------------------------------------------------------------
# Page: standings
# -----------------------------------------------------------------------------
elif page == "Klasemen":
    section_title("TEAM PERFORMANCE", "Klasemen liga", "Lihat posisi seluruh tim, lalu bandingkan satu metrik performa.")
    if standings_df.empty:
        st.markdown('<div class="empty">Data klasemen belum tersedia untuk kompetisi ini.</div>', unsafe_allow_html=True)
    else:
        with st.container(border=True):
            st.subheader("1 · Posisi tim")
            st.caption("Poin, hasil pertandingan, dan produktivitas gol sepanjang musim.")
            table = standings_df.sort_values(["points", "goal_diff", "goals_for"], ascending=[False, False, False]).reset_index(drop=True).copy()
            render_standings_table(table, compact=False)

        with st.container(border=True):
            st.subheader("2 · Perbandingan performa")
            st.caption("Grafik menampilkan sepuluh tim teratas untuk metrik yang dipilih.")
            metric_labels = {
                "Gol dicetak": "goals_for",
                "Poin": "points",
                "Selisih gol": "goal_diff",
                "Gol kebobolan": "goals_against",
                "Menang": "won",
            }
            selected_metric = st.selectbox("Pilih metrik", list(metric_labels), key="standings_metric")
            metric_col = metric_labels[selected_metric]
            team_chart = standings_df.nlargest(10, metric_col).sort_values(metric_col, ascending=False).copy()
            render_bar_list(team_chart, "short_name", metric_col)

# -----------------------------------------------------------------------------
# Page: top scorers
# -----------------------------------------------------------------------------
elif page == "Pencetak gol":
    section_title("PLAYER SPOTLIGHT", "Pencetak gol", "Sorotan pemimpin daftar, peringkat pemain, dan perbandingan jumlah gol.")
    if scorers_df.empty:
        st.markdown('<div class="empty">Data pencetak gol belum tersedia di API untuk kompetisi ini.</div>', unsafe_allow_html=True)
    else:
        scorer_name_col = "name"
        scorer_goals_col = "goals"
        all_scorers = scorers_df.sort_values(scorer_goals_col, ascending=False).copy()
        leader = all_scorers.iloc[0]
        top_counts = [count for count in [5, 10, 15, 20] if count < len(all_scorers)] + [len(all_scorers)]
        top_counts = sorted(set(top_counts))

        with st.container(border=True):
            st.subheader("1 · Sorotan pencetak gol")
            st.caption("Ringkasan kompetisi berdasarkan data pencetak gol yang tersedia.")
            p1, p2, p3 = st.columns(3)
            p1.metric("Nama Pemain", str(leader[scorer_name_col]))
            p2.metric("Gol terbanyak", int(leader[scorer_goals_col]))
            p3.metric("Pemain terdaftar", len(all_scorers))
            top_count = st.selectbox(
                "Jumlah pemain yang ditampilkan",
                top_counts,
                index=min(1, len(top_counts) - 1),
                key="scorer_count",
            )

        visible_scorers = all_scorers.head(top_count).copy()
        ranking_tab, chart_tab, player_tab = st.tabs(["Daftar peringkat", "Grafik gol", "Statistik pemain"])
        with ranking_tab:
            with st.container(border=True):
                st.subheader(f"2 · Peringkat {len(visible_scorers)} pemain")
                render_scorer_board(visible_scorers)
        with chart_tab:
            with st.container(border=True):
                st.subheader("3 · Perbandingan gol")
                st.caption("Urutkan visual pemain sesuai jumlah gol pada daftar di atas.")
                chart_scorers = visible_scorers.sort_values(scorer_goals_col, ascending=False)
                render_bar_list(chart_scorers, scorer_name_col, scorer_goals_col, unit=" gol", player_icons=True)
        with player_tab:
            with st.container(border=True):
                st.subheader("4 · Statistik pemain")
                st.caption("Pilih pemain untuk melihat peringkat dan statistik gol yang tersedia dari OpenLigaDB.")
                player_indexes = list(range(len(all_scorers)))
                selected_player_index = st.selectbox(
                    "Pilih pemain",
                    player_indexes,
                    format_func=lambda index: f"{all_scorers.iloc[index][scorer_name_col]}",
                    key="player_stats_choice",
                )
                selected_player = all_scorers.iloc[selected_player_index]
                selected_name = str(selected_player[scorer_name_col])
                selected_goals = int(selected_player[scorer_goals_col])
                leader_goals = int(all_scorers[scorer_goals_col].max())
                player_id = selected_player.get("player_id")
                id_label = str(player_id) if pd.notna(player_id) else "tidak tersedia"
                st.markdown(
                    f'<div class="player-profile">{player_avatar_html(selected_name, "lg")}<div class="player-profile-main">'
                    f'<span class="player-profile-name">{escape(selected_name)}</span>',
                    unsafe_allow_html=True,
                )
                s1, s2, s3 = st.columns(3)
                s1.metric("Peringkat", f"#{selected_player_index + 1}")
                s2.metric("Gol", selected_goals)
                s3.metric("Selisih dari pemimpin", f"{selected_goals - leader_goals:+d} gol")

            with st.container(border=True):
                st.subheader("Perbandingan dengan pencetak gol teratas")
                comparison = all_scorers.head(10).copy()
                if pd.notna(player_id) and player_id not in comparison["player_id"].values:
                    comparison = pd.concat([comparison, all_scorers.iloc[[selected_player_index]]], ignore_index=True)
                elif pd.isna(player_id) and selected_name not in comparison[scorer_name_col].values:
                    comparison = pd.concat([comparison, all_scorers.iloc[[selected_player_index]]], ignore_index=True)
                comparison = comparison.sort_values(scorer_goals_col, ascending=False)
                render_bar_list(comparison, scorer_name_col, scorer_goals_col, unit=" gol", highlight=selected_name, player_icons=True)
            st.caption("OpenLigaDB pada kompetisi/musim terpilih menyediakan ID pemain, nama pencetak gol, dan jumlah gol; atribut lain tidak ditambahkan jika tidak tersedia dari API.")

else:
    section_title("PERSONAL SPACE",  "Panel personal", "Ruang khusus untuk mengikuti satu tim tanpa memenuhi ringkasan kompetisi.")
    if standings_df.empty:
        st.markdown('<div class="empty">Data tim belum tersedia untuk kompetisi ini.</div>', unsafe_allow_html=True)
    else:
        ranked_teams = standings_df.sort_values(["points", "goal_diff", "goals_for"], ascending=[False, False, False]).reset_index(drop=True)
        team_names = ranked_teams["team"].dropna().tolist()
        team_labels = dict(zip(ranked_teams["team"], ranked_teams["short_name"]))
        team_logos = dict(zip(ranked_teams["team"], ranked_teams.get("logo_url", pd.Series([None] * len(ranked_teams)))))

        with st.container(border=True):
            st.subheader("1 · Tim yang diikuti")
            st.caption("Pilihan ini tersimpan selama sesi dashboard dan hanya mengatur panel personal.")
            selected_team = st.selectbox(
                "Pilih tim",
                team_names,
                format_func=lambda name: f"{team_labels.get(name, name)} · {name}",
                key="personal_team",
            )
            team_row = ranked_teams[ranked_teams["team"] == selected_team].iloc[0]
            team_rank = int(ranked_teams.index[ranked_teams["team"] == selected_team][0]) + 1
            st.markdown(
                f'<div class="spotlight-title">{team_identity_html(selected_team, team_logos.get(selected_team))}'
                f'<span>Posisi {team_rank} · {int(team_row["points"])} poin</span></div>',
                unsafe_allow_html=True,
            )

        team_games = played_df[(played_df["home"] == selected_team) | (played_df["away"] == selected_team)].sort_values("date")
        team_wins = team_draws = team_losses = team_gf = team_ga = team_points = 0
        recent_form = []
        for _, match in team_games.iterrows():
            if match["home"] == selected_team:
                scored, conceded = int(match["home_goals"]), int(match["away_goals"])
            else:
                scored, conceded = int(match["away_goals"]), int(match["home_goals"])
            team_gf += scored
            team_ga += conceded
            if scored > conceded:
                team_wins += 1
                team_points += 3
                result = "W"
            elif scored == conceded:
                team_draws += 1
                team_points += 1
                result = "D"
            else:
                team_losses += 1
                result = "L"
            recent_form.append((result, match["home"], match["away"], match["home_goals"], match["away_goals"]))

        with st.container(border=True):
            st.subheader("2 · Performa musim ini")
            st.caption("Statistik dihitung dari pertandingan selesai yang tersedia pada kompetisi ini.")
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Poin dari laga selesai", team_points)
            t2.metric("Rekor M–S–K", f"{team_wins}–{team_draws}–{team_losses}")
            t3.metric("Gol dicetak", team_gf)
            t4.metric("Selisih gol", f"{team_gf - team_ga:+d}")
            st.markdown('<div class="section-label">5 HASIL TERAKHIR · TERLAMA KE TERBARU</div>', unsafe_allow_html=True)
            recent_form = recent_form[-5:]
            form_html = "".join(
                f'<span class="form-chip form-{result}" title="{escape(str(home))} {int(hg)}–{int(ag)} {escape(str(away))}">{result}</span>'
                for result, home, away, hg, ag in recent_form
            ) or '<span class="sidebar-note">Belum ada hasil.</span>'
            st.markdown(f'<div class="form-strip">{form_html}</div>', unsafe_allow_html=True)

        team_upcoming = upcoming_df[(upcoming_df["home"] == selected_team) | (upcoming_df["away"] == selected_team)].sort_values("date")
        with st.container(border=True):
            st.subheader("3 · Agenda tim")
            st.caption("Hasil terbaru dan pertandingan terdekat untuk tim pilihan.")
            recent_col, next_col = st.columns(2, gap="large")
            with recent_col:
                st.markdown('<div class="section-label">HASIL TERBARU</div>', unsafe_allow_html=True)
                if team_games.empty:
                    st.info("Belum ada pertandingan selesai yang tercatat.")
                else:
                    for _, row in team_games.sort_values("date", ascending=False).head(3).iterrows():
                        render_match_card(row)
            with next_col:
                st.markdown('<div class="section-label">PERTANDINGAN MENDATANG</div>', unsafe_allow_html=True)
                if team_upcoming.empty:
                    st.info("Tidak ada jadwal mendatang untuk tim ini.")
                else:
                    for _, row in team_upcoming.head(3).iterrows():
                        render_match_card(row)

# -----------------------------------------------------------------------------
# Footer / attribution
# -----------------------------------------------------------------------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    '<div class="sidebar-note">Sumber: <a href="https://www.openligadb.de/" target="_blank" style="color:#8cf28a">OpenLigaDB</a>.</div>',
    unsafe_allow_html=True,
)
