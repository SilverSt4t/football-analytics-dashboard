from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import BackendUnavailable, get_competition, get_leagues


# -----------------------------------------------------------------------------
# App configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Touchline | Football Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

SEASON_OPTIONS = [2026, 2025, 2024, 2023]
force_refresh = bool(st.session_state.pop("force_refresh", False))
POPULAR_LEAGUES = ["pl", "bl1", "bl2", "bl3", "dfb", "cl", "el", "wm"]


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
    .stButton button { background:#8cf28a; color:#0b1721; border:0; border-radius:10px; font-weight:700; }
    .stButton button:hover { background:#a8ffa2; color:#08111d; border:0; }
    div[data-testid="stRadio"] label { color:#c8d3e0; }
    [data-testid="stDataFrame"] { border:1px solid #203149; border-radius:12px; overflow:hidden; }
    hr { border-color:#203149 !important; }
    .brand { font:700 1.25rem 'Space Grotesk',sans-serif; letter-spacing:-.04em; color:#f3f6fb; padding:4px 2px 18px; }
    .brand span { color:#8cf28a; }
    .brand-mark { display:inline-flex; width:31px; height:31px; border-radius:10px; align-items:center; justify-content:center; background:#8cf28a; color:#09151c; margin-right:9px; font-size:18px; vertical-align:middle; }
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
    .team-dot { display:inline-flex; width:26px; height:26px; border-radius:50%; background:#1d3241; color:#a4f59e; align-items:center; justify-content:center; font-size:.65rem; font-weight:700; margin-right:7px; }
    .callout { background:rgba(140,242,138,.06); border:1px solid rgba(140,242,138,.18); border-radius:13px; color:#bfd0c3; padding:12px 15px; font-size:.82rem; }
    .sidebar-note { color:#708097; font-size:.72rem; line-height:1.5; }
    .empty { padding:26px; border:1px dashed #31435b; border-radius:14px; color:#91a0b4; text-align:center; }
    @media (max-width: 700px) { .hero-title { font-size:1.7rem; } .source-pill { font-size:.68rem; } }
    </style>
    """,
    unsafe_allow_html=True,
)


def team_initials(name: str) -> str:
    words = [word for word in str(name).replace("FC ", "").split() if word]
    return "".join(word[0] for word in words[:2]).upper() or "FC"


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
            <div class="match-team"><span class="team-dot">{team_initials(row['home'])}</span>{row['home']}</div>
            {score_html}
            <div class="match-team match-away">{row['away']}<span class="team-dot" style="margin:0 0 0 7px">{team_initials(row['away'])}</span></div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def plot_theme(fig, height=310):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color="#aab7c8", size=11),
        margin=dict(l=8, r=8, t=22, b=8),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#aab7c8")),
        xaxis=dict(gridcolor="#1d2a3c", zerolinecolor="#1d2a3c", linecolor="#1d2a3c"),
        yaxis=dict(gridcolor="#1d2a3c", zerolinecolor="#1d2a3c", linecolor="#1d2a3c"),
    )
    return fig


def section_title(eyebrow: str, title: str, description: str = ""):
    st.markdown(f'<div class="section-label">{eyebrow}</div><h2 style="margin:0 0 5px">{title}</h2>', unsafe_allow_html=True)
    if description:
        st.caption(description)


# -----------------------------------------------------------------------------
# Sidebar & filters
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-mark">⚽</span>touchline<span>.</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">PENGATURAN DASHBOARD</div>', unsafe_allow_html=True)
    season = st.selectbox("Musim", SEASON_OPTIONS, index=0, format_func=lambda year: f"{year}/{year + 1}")

    try:
        league_rows = get_leagues(season, refresh=force_refresh)
        league_rows = [row for row in league_rows if row.get("sport", "Fußball") == "Fußball"]
        # Prioritize familiar competitions, then include the remaining API options.
        popular = [row for code in POPULAR_LEAGUES for row in league_rows if row.get("leagueShortcut", "").lower() == code]
        other = [row for row in league_rows if row not in popular]
        league_rows = popular + sorted(other, key=lambda row: row.get("leagueName", ""))
    except BackendUnavailable as exc:
        st.error(f"Tidak dapat mengambil daftar liga dari backend: {exc}")
        st.stop()

    # Keep one option per shortcut, as some APIs may expose duplicate records.
    unique_leagues = {}
    for row in league_rows:
        code = row.get("leagueShortcut")
        if code and code not in unique_leagues:
            unique_leagues[code] = row
    league_rows = list(unique_leagues.values())
    if not league_rows:
        st.error("API tidak mengembalikan daftar kompetisi untuk musim ini.")
        st.stop()
    league_codes = [row["leagueShortcut"] for row in league_rows]
    default_code = "pl" if "pl" in league_codes else ("bl1" if "bl1" in league_codes else league_codes[0])
    selected_code = st.selectbox(
        "Kompetisi",
        league_codes,
        index=league_codes.index(default_code),
        format_func=lambda code: next((row.get("leagueName", code) for row in league_rows if row.get("leagueShortcut") == code), code),
    )

    if st.button("↻  Muat ulang data", width="stretch"):
        st.cache_data.clear()
        st.session_state["force_refresh"] = True
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    page = st.radio("NAVIGASI", ["Ringkasan", "Pertandingan", "Klasemen", "Pencetak gol"], label_visibility="visible")
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        '<div class="sidebar-note">DATA SOURCE<br><strong>Streamlit UI → FastAPI → OpenLigaDB</strong><br>Cache data 15 menit · waktu ditampilkan WIB<br><br>Dashboard analisis sepak bola untuk eksplorasi data.</div>',
        unsafe_allow_html=True,
    )

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
    st.markdown('<div class="section-label">OVERVIEW · MUSIM INI</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Pertandingan selesai", f"{len(played_df):,}", f"dari {len(matches_df):,} jadwal")
    k2.metric("Total gol", f"{total_goals:,}", "gol tercipta")
    k3.metric("Rata-rata gol / laga", f"{avg_goals:.2f}", "kedua tim")
    k4.metric("Kemenangan kandang", f"{home_win_pct:.1f}%", f"{home_wins} kemenangan")

    chart_col, recent_col = st.columns([1.3, 1], gap="large")
    with chart_col:
        st.markdown('<div class="section-label">HASIL PERTANDINGAN</div>', unsafe_allow_html=True)
        if len(played_df):
            result_values = pd.DataFrame({"Hasil": ["Kandang menang", "Seri", "Tandang menang"], "Jumlah": [home_wins, draws, away_wins]})
            fig = px.pie(result_values, names="Hasil", values="Jumlah", hole=.72, color="Hasil", color_discrete_map={"Kandang menang": "#8cf28a", "Seri": "#64748b", "Tandang menang": "#38bdf8"})
            fig.update_traces(textposition="outside", textinfo="percent", marker=dict(line=dict(color="#0b1523", width=3)))
            fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-.13, x=0), annotations=[dict(text=f"{len(played_df)}<br><span style='font-size:10px;color:#8d9cb0'>LAGA</span>", x=.5, y=.5, showarrow=False, font=dict(size=21, color="#f3f6fb", family="Space Grotesk"))])
            st.plotly_chart(plot_theme(fig, 325), width="stretch", config={"displayModeBar": False})
        else:
            st.info("Belum ada pertandingan selesai untuk divisualisasikan.")

    with recent_col:
        st.markdown('<div class="section-label">JADWAL BERIKUTNYA</div>', unsafe_allow_html=True)
        if upcoming_df.empty:
            st.markdown('<div class="empty">Semua pertandingan musim ini telah selesai.</div>', unsafe_allow_html=True)
        else:
            next_matches = upcoming_df.sort_values("date").head(4)
            for _, row in next_matches.iterrows():
                render_match_card(row)

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.markdown('<div class="section-label">TREN GOL PER PEKAN</div>', unsafe_allow_html=True)
        if not played_df.empty:
            trend = played_df.groupby("round_id", dropna=True).agg(goals=("total_goals", "sum"), matches=("match_id", "count")).reset_index().sort_values("round_id")
            trend["week_label"] = trend["round_id"].apply(lambda x: f"P{x:g}" if pd.notna(x) else "-")
            fig = px.area(trend, x="week_label", y="goals", markers=True)
            fig.update_traces(line=dict(color="#8cf28a", width=2.5), fillcolor="rgba(140,242,138,.10)", marker=dict(size=5, color="#8cf28a"), hovertemplate="%{x}<br>%{y} gol<extra></extra>")
            fig.update_layout(xaxis_title="", yaxis_title="Gol", hovermode="x unified")
            st.plotly_chart(plot_theme(fig, 285), width="stretch", config={"displayModeBar": False})
        else:
            st.info("Grafik akan muncul setelah pertandingan selesai.")
    with right:
        st.markdown('<div class="section-label">TOP 5 KLASEMEN</div>', unsafe_allow_html=True)
        if not standings_df.empty:
            top = standings_df.sort_values(["points", "goal_diff"], ascending=[False, False]).head(5).copy()
            top["Tim"] = top.get("short_name", top.get("team", "Tim"))
            top = top.rename(columns={"points": "Poin", "played": "Main", "won": "M", "draw": "S", "lost": "K", "goal_diff": "SG"})
            display_cols = [col for col in ["Tim", "Main", "M", "S", "K", "SG", "Poin"] if col in top.columns]
            st.dataframe(top[display_cols], hide_index=True, width="stretch", height=252)
        else:
            st.info("Klasemen belum tersedia untuk kompetisi ini.")

    st.markdown('<div class="callout">Insight starter: bandingkan persentase kemenangan kandang dengan tandang, lalu cek apakah rata-rata gol ikut berubah sepanjang musim.</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Page: matches
# -----------------------------------------------------------------------------
elif page == "Pertandingan":
    section_title("MATCH CENTRE", "Jadwal & hasil", "Cari pertandingan berdasarkan tim, pekan, atau status.")
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
    st.caption(f"Menampilkan {len(filtered)} pertandingan · waktu Asia/Jakarta (WIB)")
    if filtered.empty:
        st.markdown('<div class="empty">Tidak ada pertandingan yang cocok dengan filter.</div>', unsafe_allow_html=True)
    else:
        for _, row in filtered.head(30).iterrows():
            render_match_card(row)
        if len(filtered) > 30:
            st.caption("Menampilkan 30 pertandingan pertama. Gunakan filter pekan atau tim untuk mempersempit hasil.")

# -----------------------------------------------------------------------------
# Page: standings
# -----------------------------------------------------------------------------
elif page == "Klasemen":
    section_title("TEAM PERFORMANCE", "Klasemen liga", "Bandingkan poin, produktivitas gol, dan selisih gol.")
    if standings_df.empty:
        st.markdown('<div class="empty">Data klasemen belum tersedia untuk kompetisi ini.</div>', unsafe_allow_html=True)
    else:
        table = standings_df.sort_values(["points", "goal_diff", "goals_for"], ascending=[False, False, False]).reset_index(drop=True).copy()
        table.insert(0, "#", range(1, len(table) + 1))
        table["Tim"] = table.get("short_name", table.get("team", "Tim"))
        table = table.rename(columns={"played": "Main", "won": "M", "draw": "S", "lost": "K", "goals_for": "GM", "goals_against": "GK", "goal_diff": "SG", "points": "Poin"})
        show = [c for c in ["#", "Tim", "Main", "M", "S", "K", "GM", "GK", "SG", "Poin"] if c in table.columns]
        st.dataframe(table[show], hide_index=True, width="stretch", height=610)
        st.markdown('<div class="section-label">GOL DICETAK · 10 TIM TERATAS</div>', unsafe_allow_html=True)
        goals_chart = table.sort_values("GM", ascending=True).tail(10)
        fig = px.bar(goals_chart, x="GM", y="Tim", orientation="h", text="GM", color="GM", color_continuous_scale=[[0, "#28634b"], [1, "#8cf28a"]])
        fig.update_traces(textposition="outside", marker_line_width=0, hovertemplate="%{y}<br>%{x} gol<extra></extra>")
        fig.update_layout(xaxis_title="Gol", yaxis_title="", coloraxis_showscale=False)
        st.plotly_chart(plot_theme(fig, 390), width="stretch", config={"displayModeBar": False})

# -----------------------------------------------------------------------------
# Page: top scorers
# -----------------------------------------------------------------------------
else:
    section_title("PLAYER SPOTLIGHT", "Pencetak gol", "Daftar pencetak gol tertinggi pada kompetisi dan musim yang dipilih.")
    if scorers_df.empty:
        st.markdown('<div class="empty">Data pencetak gol belum tersedia di API untuk kompetisi ini.</div>', unsafe_allow_html=True)
    else:
        scorer_name_col = "name"
        scorer_goals_col = "goals"
        scorers_df = scorers_df.sort_values(scorer_goals_col, ascending=True).tail(10).copy()
        st.markdown('<div class="section-label">TOP SCORER CHART</div>', unsafe_allow_html=True)
        fig = px.bar(scorers_df, x=scorer_goals_col, y=scorer_name_col, orientation="h", text=scorer_goals_col, color=scorer_goals_col, color_continuous_scale=[[0, "#28634b"], [1, "#8cf28a"]])
        fig.update_traces(textposition="outside", marker_line_width=0, hovertemplate="%{y}<br>%{x} gol<extra></extra>")
        fig.update_layout(xaxis_title="Gol", yaxis_title="", coloraxis_showscale=False)
        st.plotly_chart(plot_theme(fig, max(340, 35 * len(scorers_df))), width="stretch", config={"displayModeBar": False})
        table = scorers_df.sort_values(scorer_goals_col, ascending=False).reset_index(drop=True)
        table.insert(0, "#", range(1, len(table) + 1))
        table = table.rename(columns={scorer_name_col: "Pemain", scorer_goals_col: "Gol"})
        st.dataframe(table[["#", "Pemain", "Gol"]], hide_index=True, width="stretch")

# -----------------------------------------------------------------------------
# Footer / attribution
# -----------------------------------------------------------------------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    '<div class="sidebar-note">Sumber: <a href="https://www.openligadb.de/" target="_blank" style="color:#8cf28a">OpenLigaDB</a> · Data komunitas, disajikan untuk eksplorasi dan pembelajaran. Cakupan statistik berbeda per kompetisi.</div>',
    unsafe_allow_html=True,
)
