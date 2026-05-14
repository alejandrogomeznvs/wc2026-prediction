import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from streamlit_sortables import sort_items

st.set_page_config(
    page_title="FIFA World Cup 2026 — Predictions",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Theme — dark navy + gold (World Cup 2026)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
html, body, [class*="css"] { background-color:#0a0e1a !important; color:#ffffff !important; }
[data-testid="stAppViewContainer"] { background:#0a0e1a; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { background:#0d1225; border-right:1px solid #1e2d5a; }
section[data-testid="stSidebar"] > div { background:#0d1225; }
[data-testid="block-container"] { padding-top:1.5rem; }

div[data-testid="metric-container"] {
    background:linear-gradient(135deg,#12192d,#1a2444);
    border:1px solid #FFD700; border-radius:12px; padding:16px 20px;
}
div[data-testid="metric-container"] label {
    color:#FFD700 !important; font-size:0.68rem;
    text-transform:uppercase; letter-spacing:0.1em; font-weight:700;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color:#ffffff !important; font-size:1.6rem; font-weight:800;
}
h1 { color:#FFD700 !important; font-weight:900; letter-spacing:-0.02em; }
h2,h3 { color:#ffffff !important; }
hr { border-color:#1e2d5a !important; }
[data-testid="stCaptionContainer"] p { color:#8892b0 !important; }
[data-testid="stSelectbox"]>div>div {
    background:#12192d !important; border:1px solid #1e2d5a !important; color:#fff !important;
}
[data-testid="stDataFrame"] { background:#12192d; border-radius:8px; }
[data-baseweb="select"] { background:#12192d !important; }

/* Bracket clickable buttons */
[data-testid="baseButton-primary"] {
    background-color:#FFD700 !important; color:#000 !important;
    border-color:#FFD700 !important; font-weight:700 !important;
    text-align:left !important;
}
[data-testid="baseButton-primary"]:hover { background-color:#e6c200 !important; }
[data-testid="baseButton-secondary"] {
    background-color:#12192d !important; color:#8892b0 !important;
    border:1px solid #1e2d5a !important; text-align:left !important;
}
[data-testid="baseButton-secondary"]:hover {
    background-color:#1a2444 !important; color:#fff !important;
    border-color:#FFD700 !important;
}

/* Sortables drag-and-drop */
.sortable-item {
    background:#12192d !important; color:#fff !important;
    border:1px solid #1e2d5a !important; border-radius:6px !important;
    padding:8px 12px !important; cursor:grab !important;
    font-size:0.82rem !important;
}
.sortable-item:hover { border-color:#FFD700 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE = Path(__file__).parent

ROUNDS = ["qualify","round_of_16","quarter_final","semi_final","final","champion"]
ROUND_LABELS = ["Clasifica","Octavos","Cuartos","Semis","Final","Campeon"]

CONF_COLORS = {
    "UEFA":"#003DA6","CONMEBOL":"#00a651","CONCACAF":"#e63946",
    "AFC":"#f4a261","CAF":"#e91e63","OFC":"#9c27b0",
}

FLAGS = {
    "Spain":"🇪🇸","Argentina":"🇦🇷","France":"🇫🇷","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Brazil":"🇧🇷","Germany":"🇩🇪","Netherlands":"🇳🇱","Portugal":"🇵🇹",
    "Belgium":"🇧🇪","Switzerland":"🇨🇭","Mexico":"🇲🇽","Colombia":"🇨🇴",
    "Japan":"🇯🇵","Uruguay":"🇺🇾","Croatia":"🇭🇷","Turkey":"🇹🇷",
    "Ecuador":"🇪🇨","Czech Republic":"🇨🇿","Morocco":"🇲🇦","Norway":"🇳🇴",
    "Austria":"🇦🇹","Senegal":"🇸🇳","Canada":"🇨🇦","South Korea":"🇰🇷",
    "Australia":"🇦🇺","Paraguay":"🇵🇾","Iran":"🇮🇷","United States":"🇺🇸",
    "Algeria":"🇩🇿","Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","Sweden":"🇸🇪","Panama":"🇵🇦",
    "Ivory Coast":"🇨🇮","Curaçao":"🇨🇼","Egypt":"🇪🇬","DR Congo":"🇨🇩",
    "Uzbekistan":"🇺🇿","Tunisia":"🇹🇳","South Africa":"🇿🇦","Jordan":"🇯🇴",
    "Bosnia and Herzegovina":"🇧🇦","New Zealand":"🇳🇿","Cape Verde":"🇨🇻",
    "Iraq":"🇮🇶","Ghana":"🇬🇭","Qatar":"🇶🇦","Haiti":"🇭🇹","Saudi Arabia":"🇸🇦",
}

ABBREV = {
    "Spain":"ESP","Argentina":"ARG","France":"FRA","England":"ENG",
    "Brazil":"BRA","Germany":"GER","Netherlands":"NED","Portugal":"POR",
    "Belgium":"BEL","Switzerland":"SUI","Mexico":"MEX","Colombia":"COL",
    "Japan":"JPN","Uruguay":"URU","Croatia":"CRO","Turkey":"TUR",
    "Ecuador":"ECU","Czech Republic":"CZE","Morocco":"MAR","Norway":"NOR",
    "Austria":"AUT","Senegal":"SEN","Canada":"CAN","South Korea":"KOR",
    "Australia":"AUS","Paraguay":"PAR","Iran":"IRN","United States":"USA",
    "Algeria":"ALG","Scotland":"SCO","Sweden":"SWE","Panama":"PAN",
    "Ivory Coast":"CIV","Curaçao":"CUW","Egypt":"EGY","DR Congo":"COD",
    "Uzbekistan":"UZB","Tunisia":"TUN","South Africa":"RSA","Jordan":"JOR",
    "Bosnia and Herzegovina":"BIH","New Zealand":"NZL","Cape Verde":"CPV",
    "Iraq":"IRQ","Ghana":"GHA","Qatar":"QAT","Haiti":"HAI","Saudi Arabia":"KSA",
}

ELO_NAME_MAP = {"Czechia":"Czech Republic","CuraÃ\x83Â§ao":"Curaçao"}

PRED_LABEL = {"H":"Gana local","A":"Gana visitante","D":"Empate"}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    sim = pd.read_csv(BASE / "reports/simulation_results.csv")
    groups_df = pd.read_csv(BASE / "data/raw/wc2026_groups.csv")
    elo_df = pd.read_csv(BASE / "data/raw/elo_ratings.csv", encoding="latin-1")
    elo_df["team"] = elo_df["team"].replace(ELO_NAME_MAP)

    sim = sim.merge(groups_df[["team","host_country","pot"]], on="team", how="left")
    sim = sim.merge(elo_df[["team","elo_rating"]], on="team", how="left")

    # Fechas del CSV original (home/away oficial según calendario FIFA)
    sched = pd.read_csv(
        BASE / "data/processed/wc2026_group_stage_predictions.csv", parse_dates=["date"]
    )
    sched["group"] = sched["home_team"].map(groups_df.set_index("team")["group"].to_dict())
    # Clave canónica independiente del orden home/away
    sched["pair"] = sched.apply(lambda r: tuple(sorted([r.home_team, r.away_team])), axis=1)

    # Probabilidades de simulación Monte Carlo por partido
    sim_m = pd.read_csv(BASE / "reports/group_match_results.csv")
    sim_m["pair"] = sim_m.apply(lambda r: tuple(sorted([r.home_team, r.away_team])), axis=1)

    # Merge: añadir fecha + orden oficial al CSV de simulación
    matches = sched[["date","home_team","away_team","group","pair"]].merge(
        sim_m[["pair","sim_prob_home_win","sim_prob_draw","sim_prob_away_win"]],
        on="pair", how="left"
    )
    # Las probs simuladas están en el orden (sim_home, sim_away) de combinations().
    # Las columnas del sched tienen su propio home/away. Necesito alinearlas:
    # Si el home_team del sched coincide con el home_team de sim_m → OK
    # Si no → invertir prob_home_win y prob_away_win
    sim_home_map = dict(zip(sim_m["pair"], sim_m["home_team"]))
    matches["sim_home"] = matches["pair"].map(sim_home_map)
    needs_flip = matches["home_team"] != matches["sim_home"]
    matches.loc[needs_flip, ["sim_prob_home_win","sim_prob_away_win"]] = (
        matches.loc[needs_flip, ["sim_prob_away_win","sim_prob_home_win"]].values
    )
    matches = matches.drop(columns=["pair","sim_home"])

    return sim, matches, groups_df


sim, matches, groups_df = load_data()

# ---------------------------------------------------------------------------
# Bracket visual helpers (page_bracket only)
# ---------------------------------------------------------------------------
def _bk_card(n1, n2, winner, is_final=False):
    """Match card: winner highlighted, loser ghosted with strikethrough."""
    t1, t2 = _td(n1), _td(n2)
    e1 = float(t1.get("elo_rating") or 1500)
    e2 = float(t2.get("elo_rating") or 1500)
    p = 1 / (1 + 10 ** (-((e1 - e2) / 400)))
    f1, f2 = FLAGS.get(t1["team"], ""), FLAGS.get(t2["team"], "")
    a1 = ABBREV.get(t1["team"], t1["team"][:3].upper())
    a2 = ABBREV.get(t2["team"], t2["team"][:3].upper())
    w1, w2 = t1["team"] == winner, t2["team"] == winner

    def row(flag, abbrev, prob, is_win):
        if is_win:
            return (
                f'<div style="display:flex;align-items:center;gap:5px;padding:7px 9px;'
                f'background:linear-gradient(90deg,#0c1d06,#152a08);border-left:3px solid #7ab83e;">'
                f'<span style="font-size:0.9rem;line-height:1;">{flag}</span>'
                f'<span style="color:#b5e675;font-weight:800;font-size:0.76rem;flex:1;">{abbrev}</span>'
                f'<span style="color:#7ab83e;font-size:0.6rem;font-weight:600;">{prob*100:.0f}%</span></div>'
            )
        return (
            f'<div style="display:flex;align-items:center;gap:5px;padding:7px 9px;'
            f'background:#0b1022;border-left:3px solid #1e2d5a;opacity:0.65;">'
            f'<span style="font-size:0.9rem;line-height:1;">{flag}</span>'
            f'<span style="color:#6b7280;font-weight:500;font-size:0.76rem;flex:1;'
            f'text-decoration:line-through;">{abbrev}</span>'
            f'<span style="color:#4b5563;font-size:0.6rem;">{prob*100:.0f}%</span></div>'
        )

    if is_final:
        wf, wa = (f1, a1) if w1 else (f2, a2)
        lf, la = (f2, a2) if w1 else (f1, a1)
        lp = (1 - p) if w1 else p
        return (
            f'<div style="border-radius:8px;overflow:hidden;margin-bottom:6px;'
            f'box-shadow:0 0 22px rgba(255,215,0,0.22),0 2px 8px rgba(0,0,0,0.6);'
            f'border:1px solid #b8860b;">'
            f'<div style="display:flex;align-items:center;gap:5px;padding:9px 10px;'
            f'background:linear-gradient(90deg,#1f1700,#2e2200);border-left:4px solid #FFD700;">'
            f'<span style="font-size:1.1rem;line-height:1;">{wf}</span>'
            f'<span style="color:#FFD700;font-weight:900;font-size:0.82rem;flex:1;">{wa}</span>'
            f'<span style="background:#FFD700;color:#000;font-size:0.48rem;font-weight:900;'
            f'padding:2px 5px;border-radius:3px;">CAMPEÓN</span></div>'
            f'<div style="display:flex;align-items:center;gap:5px;padding:7px 10px;'
            f'background:#0b1022;border-left:4px solid #1e2d5a;opacity:0.6;">'
            f'<span style="font-size:0.9rem;line-height:1;">{lf}</span>'
            f'<span style="color:#6b7280;font-weight:500;font-size:0.76rem;flex:1;'
            f'text-decoration:line-through;">{la}</span>'
            f'<span style="color:#4b5563;font-size:0.6rem;">{lp*100:.0f}%</span></div></div>'
        )
    return (
        f'<div style="border-radius:6px;overflow:hidden;margin-bottom:6px;'
        f'box-shadow:0 1px 5px rgba(0,0,0,0.5);border:1px solid #1a2535;">'
        + row(f1, a1, p, w1)
        + row(f2, a2, 1 - p, w2)
        + '</div>'
    )


def _bk_connector(y_outer, y_inner, total_h, color="#2d4a8a", flip=False, w=12):
    """Bracket connector lines pairing adjacent rounds."""
    h2 = w // 2
    lines = ""
    for i, yi in enumerate(y_inner):
        y1, y2 = y_outer[i * 2], y_outer[i * 2 + 1]
        if not flip:
            lines += (
                f'<div style="position:absolute;top:{y1}px;left:0;width:{h2}px;height:2px;background:{color};opacity:0.5;"></div>'
                f'<div style="position:absolute;top:{y1}px;left:{h2}px;width:2px;height:{y2-y1}px;background:{color};opacity:0.5;"></div>'
                f'<div style="position:absolute;top:{y2}px;left:0;width:{h2}px;height:2px;background:{color};opacity:0.5;"></div>'
                f'<div style="position:absolute;top:{yi}px;left:{h2}px;width:{h2}px;height:2px;background:{color};opacity:0.5;"></div>'
            )
        else:
            lines += (
                f'<div style="position:absolute;top:{y1}px;right:0;width:{h2}px;height:2px;background:{color};opacity:0.5;"></div>'
                f'<div style="position:absolute;top:{y1}px;right:{h2}px;width:2px;height:{y2-y1}px;background:{color};opacity:0.5;"></div>'
                f'<div style="position:absolute;top:{y2}px;right:0;width:{h2}px;height:2px;background:{color};opacity:0.5;"></div>'
                f'<div style="position:absolute;top:{yi}px;right:{h2}px;width:{h2}px;height:2px;background:{color};opacity:0.5;"></div>'
            )
    return f'<div style="position:relative;width:{w}px;flex-shrink:0;height:{total_h}px;">{lines}</div>'


def _bk_sf_line(y_sf, total_h, color="#b828d0", w=12):
    """Straight horizontal connector between SF and Final."""
    line = f'<div style="position:absolute;top:{y_sf}px;left:0;width:{w}px;height:2px;background:{color};opacity:0.5;"></div>'
    return f'<div style="position:relative;width:{w}px;flex-shrink:0;height:{total_h}px;">{line}</div>'


# ---------------------------------------------------------------------------
# Simulator — R32 bracket template (mirrors simulation.py)
# ---------------------------------------------------------------------------
R32_TEMPLATE_DASH = [
    # ── LADO IZQUIERDO → SF P101 → Final ──────────────────────────────────────
    # QF P97: R16 P89 (W0 vs W1)  +  R16 P90 (W2 vs W3)
    ("1E",  "3rd_1"),   # 0  – P74  Boston          → R16 P89
    ("1I",  "3rd_2"),   # 1  – P77  Nueva York       → R16 P89
    ("2A",  "2B"),      # 2  – P73  Los Ángeles      → R16 P90
    ("1F",  "2C"),      # 3  – P75  Monterrey        → R16 P90
    # QF P98: R16 P93 (W4 vs W5)  +  R16 P94 (W6 vs W7)
    ("2K",  "2L"),      # 4  – P83  Toronto          → R16 P93
    ("1H",  "2J"),      # 5  – P84  Los Ángeles      → R16 P93
    ("1D",  "3rd_3"),   # 6  – P81  Bahía de SF      → R16 P94
    ("1G",  "3rd_4"),   # 7  – P82  Seattle          → R16 P94
    # ── LADO DERECHO → SF P102 → Final ───────────────────────────────────────
    # QF P99: R16 P91 (W8 vs W9)  +  R16 P92 (W10 vs W11)
    ("1C",  "2F"),      # 8  – P76  Houston          → R16 P91
    ("2E",  "2I"),      # 9  – P78  Dallas           → R16 P91
    ("1A",  "3rd_5"),   # 10 – P79  Ciudad de México → R16 P92
    ("1L",  "3rd_6"),   # 11 – P80  Atlanta          → R16 P92
    # QF P100: R16 P95 (W12 vs W13)  +  R16 P96 (W14 vs W15)
    ("1J",  "2H"),      # 12 – P86  Miami            → R16 P95
    ("2D",  "2G"),      # 13 – P88  Dallas           → R16 P95
    ("1B",  "3rd_7"),   # 14 – P85  Vancouver        → R16 P96
    ("1K",  "3rd_8"),   # 15 – P87  Kansas City      → R16 P96
]


def elo_prob_teams(t1, t2, sim_df):
    """P(t1 wins) using Elo ratings from sim_df."""
    r1 = sim_df[sim_df["team"] == t1]
    r2 = sim_df[sim_df["team"] == t2]
    e1 = float(r1["elo_rating"].iloc[0]) if not r1.empty and pd.notna(r1["elo_rating"].iloc[0]) else 1500.0
    e2 = float(r2["elo_rating"].iloc[0]) if not r2.empty and pd.notna(r2["elo_rating"].iloc[0]) else 1500.0
    return 1 / (1 + 10 ** (-(e1 - e2) / 400))


def _init_sim_state():
    """Initialize group_picks (top 3 per group from model) in session_state."""
    if "group_picks" not in st.session_state:
        all_groups = sorted(groups_df["group"].unique())
        picks = {}
        for grp in all_groups:
            grp_df = sim[sim["group"] == grp].sort_values("qualify", ascending=False)
            teams = grp_df["team"].tolist()
            picks[grp] = {
                "1st": teams[0] if len(teams) > 0 else "",
                "2nd": teams[1] if len(teams) > 1 else "",
                "3rd": teams[2] if len(teams) > 2 else "",
            }
        st.session_state.group_picks = picks


def _build_r32(group_picks):
    """Build 16-match R32 bracket from group_picks dict."""
    slot_map = {}
    selected = set()
    third_candidates = []
    for grp, p in group_picks.items():
        t1 = p.get("1st", "")
        t2 = p.get("2nd", "")
        t3 = p.get("3rd", "")
        if t1:
            slot_map[f"1{grp}"] = t1
            selected.add(t1)
        if t2:
            slot_map[f"2{grp}"] = t2
            selected.add(t2)
        if t3:
            third_candidates.append(t3)
    tc_df = sim[sim["team"].isin(third_candidates)].sort_values("qualify", ascending=False)
    for i, t in enumerate(tc_df["team"].tolist()[:8], 1):
        slot_map[f"3rd_{i}"] = t
    return [(slot_map.get(h, "TBD"), slot_map.get(a, "TBD")) for h, a in R32_TEMPLATE_DASH]


def _td(name):
    """Get team dict from sim dataframe for HTML helpers."""
    row = sim[sim["team"] == name]
    if not row.empty:
        return row.iloc[0].to_dict()
    return {"team": name, "elo_rating": 1500.0, "champion": 0.0, "group": "?"}


def _resolve_bracket(r32, ns=""):
    """Compute full bracket from session_state (Elo fallback). ns= key namespace prefix."""
    def gw(t1, t2, pfx, i):
        k = f"win_{ns}{pfx}_{i}"
        v = st.session_state.get(k)
        if v not in (t1, t2):
            return t1 if elo_prob_teams(t1, t2, sim) >= 0.5 else t2
        return v

    r32_w = [gw(t1, t2, "r32", i) for i, (t1, t2) in enumerate(r32)]
    r16 = [(r32_w[i * 2], r32_w[i * 2 + 1]) for i in range(8)]
    r16_w = [gw(t1, t2, "r16", i) for i, (t1, t2) in enumerate(r16)]
    qf = [(r16_w[i * 2], r16_w[i * 2 + 1]) for i in range(4)]
    qf_w = [gw(t1, t2, "qf", i) for i, (t1, t2) in enumerate(qf)]
    sf = [(qf_w[i * 2], qf_w[i * 2 + 1]) for i in range(2)]
    sf_w = [gw(t1, t2, "sf", i) for i, (t1, t2) in enumerate(sf)]
    fin = (sf_w[0], sf_w[1])
    champ = gw(*fin, "final", 0)
    runner = fin[1] if champ == fin[0] else fin[0]
    return {
        "r32": r32, "r32_w": r32_w,
        "r16": r16, "r16_w": r16_w,
        "qf": qf, "qf_w": qf_w,
        "sf": sf, "sf_w": sf_w,
        "final": fin, "champion": champ, "runner_up": runner,
    }


def _compute_static_bracket():
    """Full bracket from model predictions only, no session state."""
    all_groups = sorted(groups_df["group"].unique())
    picks = {}
    for grp in all_groups:
        grp_df = sim[sim["group"] == grp].sort_values("qualify", ascending=False)
        teams = grp_df["team"].tolist()
        picks[grp] = {
            "1st": teams[0] if teams else "",
            "2nd": teams[1] if len(teams) > 1 else "",
            "3rd": teams[2] if len(teams) > 2 else "",
        }
    r32 = _build_r32(picks)
    def ew(t1, t2):
        return t1 if elo_prob_teams(t1, t2, sim) >= 0.5 else t2
    r32_w = [ew(t1, t2) for t1, t2 in r32]
    r16 = [(r32_w[i * 2], r32_w[i * 2 + 1]) for i in range(8)]
    r16_w = [ew(t1, t2) for t1, t2 in r16]
    qf = [(r16_w[i * 2], r16_w[i * 2 + 1]) for i in range(4)]
    qf_w = [ew(t1, t2) for t1, t2 in qf]
    sf = [(qf_w[i * 2], qf_w[i * 2 + 1]) for i in range(2)]
    sf_w = [ew(t1, t2) for t1, t2 in sf]
    fin = (sf_w[0], sf_w[1])
    champ = ew(*fin)
    runner = fin[1] if champ == fin[0] else fin[0]
    return {"r32": r32, "r32_w": r32_w, "r16": r16, "r16_w": r16_w,
            "qf": qf, "qf_w": qf_w, "sf": sf, "sf_w": sf_w,
            "final": fin, "champion": champ, "runner_up": runner}


def _bk_col(label, name_pairs, winner_names, pad_top, inter_gap, min_w, label_color, is_final=False):
    """Bracket round column with colored label and styled match cards."""
    body = ""
    for i, ((n1, n2), w) in enumerate(zip(name_pairs, winner_names)):
        if i > 0 and inter_gap > 0:
            body += f'<div style="height:{inter_gap}px"></div>'
        body += _bk_card(n1, n2, w, is_final=is_final)
    return (
        f'<div style="display:flex;flex-direction:column;min-width:{min_w}px;flex-shrink:0;padding-top:{pad_top}px;">'
        f'<div style="color:{label_color};font-size:0.52rem;font-weight:800;letter-spacing:0.12em;'
        f'text-align:center;margin-bottom:8px;text-transform:uppercase;white-space:nowrap;'
        f'border-bottom:1px solid {label_color}44;padding-bottom:4px;">{label}</div>'
        f'{body}</div>'
    )


def _downstream_win_keys(match_key):
    """Keys that must be cleared when match_key's winner changes."""
    for rnd in ("r32", "r16", "qf", "sf"):
        if rnd in match_key:
            ns = match_key[: match_key.index(rnd)]  # "" or "bk_"
            tail = match_key[match_key.index(rnd):]  # "r32_0" etc.
            break
    else:
        return []
    try:
        idx = int(tail.split("_")[1])
    except (IndexError, ValueError):
        idx = 0
    p = f"win_{ns}"
    if rnd == "r32":
        r16i = idx // 2
        return [f"{p}r16_{r16i}", f"{p}qf_{r16i//2}", f"{p}sf_{r16i//4}", f"{p}final_0"]
    if rnd == "r16":
        qfi = idx // 2
        return [f"{p}qf_{qfi}", f"{p}sf_{qfi//2}", f"{p}final_0"]
    if rnd == "qf":
        return [f"{p}sf_{idx//2}", f"{p}final_0"]
    return [f"{p}final_0"]  # sf


def _interactive_btn_card(col, t1, t2, match_key):
    """Match card with two clickable buttons (gold = winner). Returns winner."""
    p = elo_prob_teams(t1, t2, sim)
    win_key = f"win_{match_key}"
    if win_key not in st.session_state or st.session_state[win_key] not in (t1, t2):
        st.session_state[win_key] = t1 if p >= 0.5 else t2
    winner = st.session_state[win_key]
    f1, f2 = FLAGS.get(t1, ""), FLAGS.get(t2, "")

    col.markdown(
        f'<div style="background:#0d1225;border:1px solid #1e2d5a;border-radius:8px 8px 0 0;'
        f'padding:5px 10px 3px;">'
        f'<div style="background:#1e2d5a;border-radius:2px;height:4px;">'
        f'<div style="background:#FFD700;width:{p*100:.0f}%;height:4px;border-radius:2px;"></div></div>'
        f'<div style="display:flex;justify-content:space-between;font-size:0.6rem;margin-top:2px;">'
        f'<span style="color:#FFD700;">{p*100:.0f}%</span>'
        f'<span style="color:#8892b0;">{(1-p)*100:.0f}%</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    _dn = _downstream_win_keys(match_key)
    if col.button(
        f"{f1} {ABBREV.get(t1, t1[:3].upper())}", key=f"btn_{match_key}_t1",
        use_container_width=True,
        type="primary" if winner == t1 else "secondary",
    ):
        st.session_state[win_key] = t1
        for k in _dn:
            st.session_state.pop(k, None)
        st.rerun()
    if col.button(
        f"{f2} {ABBREV.get(t2, t2[:3].upper())}", key=f"btn_{match_key}_t2",
        use_container_width=True,
        type="primary" if winner == t2 else "secondary",
    ):
        st.session_state[win_key] = t2
        for k in _dn:
            st.session_state.pop(k, None)
        st.rerun()
    return st.session_state[win_key]



# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.markdown(
    '<p style="color:#FFD700;font-weight:900;font-size:1.1rem;'
    'letter-spacing:0.05em;margin-bottom:4px;">FIFA WORLD CUP</p>'
    '<p style="color:#8892b0;font-size:0.75rem;margin-top:0;">2026 · Predictions</p>',
    unsafe_allow_html=True,
)
st.sidebar.divider()

page = st.sidebar.radio(
    "nav",
    ["Grupos", "Bracket", "Probabilidades", "Resumen",
     "Simulador", "Sobre el proyecto"],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.markdown(
    '<p style="color:#8892b0;font-size:0.7rem;line-height:1.6;">'
    "10.000 simulaciones Monte Carlo<br>"
    "Modelo: Regresión Logística<br>"
    "Accuracy: 61.6% · Log-loss: 0.845</p>",
    unsafe_allow_html=True,
)


# ===========================================================================
# PAGE 1 — GRUPOS
# ===========================================================================
def page_grupos():
    st.markdown(
        '<h1 style="margin-bottom:4px;">Fase de Grupos</h1>'
        '<p style="color:#8892b0;font-size:0.85rem;margin-top:0;">'
        "Clasificación predicha por probabilidad de avanzar a octavos (10.000 simulaciones)</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    all_groups = sorted(sim["group"].unique())
    # 4 columns, 3 rows
    for row_i in range(3):
        cols = st.columns(4, gap="medium")
        for col_i, col in enumerate(cols):
            grp_idx = row_i * 4 + col_i
            if grp_idx >= len(all_groups):
                break
            grp = all_groups[grp_idx]
            grp_df = sim[sim["group"] == grp].sort_values("qualify", ascending=False).reset_index(drop=True)

            # Build group card HTML
            rows_html = ""
            for rank, (_, t) in enumerate(grp_df.iterrows(), 1):
                flag = FLAGS.get(t["team"], "")
                qualify_pct = f"{t['qualify']*100:.1f}%"
                conf = t["confederation"]
                conf_color = CONF_COLORS.get(conf, "#888")

                if rank <= 2:
                    bg = "linear-gradient(90deg,#0d2b1a,#12192d)"
                    border_left = "3px solid #00a651"
                    rank_color = "#00a651"
                else:
                    bg = "#0d1225"
                    border_left = "3px solid #1e2d5a"
                    rank_color = "#4a5568"

                host_badge = ""
                if t.get("host_country") == "Yes":
                    host_badge = '<span style="background:#C8102E;color:#fff;font-size:0.55rem;padding:1px 4px;border-radius:3px;margin-left:4px;">SEDE</span>'

                rows_html += (
                    f'<div style="background:{bg};border-left:{border_left};'
                    f'padding:8px 10px;margin-bottom:3px;border-radius:0 6px 6px 0;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<div style="display:flex;align-items:center;gap:6px;min-width:0;flex:1;">'
                    f'<span style="color:{rank_color};font-weight:700;font-size:0.75rem;flex-shrink:0;width:14px;">{rank}</span>'
                    f'<span style="font-size:1rem;flex-shrink:0;">{flag}</span>'
                    f'<div style="min-width:0;overflow:hidden;">'
                    f'<span style="color:#fff;font-size:0.78rem;font-weight:600;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;">{t["team"]}</span>'
                    f'{host_badge}'
                    f'<span style="color:{conf_color};font-size:0.6rem;">{conf}</span>'
                    f'</div></div>'
                    f'<div style="text-align:right;flex-shrink:0;margin-left:6px;">'
                    f'<div style="color:#FFD700;font-weight:700;font-size:0.82rem;">{qualify_pct}</div>'
                    f'<div style="color:#8892b0;font-size:0.62rem;">clasif.</div>'
                    f'</div></div></div>'
                )

            card_html = (
                f'<div style="background:#12192d;border:1px solid #1e2d5a;'
                f'border-radius:10px;overflow:hidden;margin-bottom:12px;">'
                f'<div style="background:linear-gradient(90deg,#1a2444,#0d1225);'
                f'padding:10px 14px;display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="color:#FFD700;font-weight:900;font-size:1rem;'
                f'letter-spacing:0.05em;">GRUPO {grp}</span>'
                f'<span style="color:#8892b0;font-size:0.65rem;">'
                f'{len(grp_df)} equipos</span></div>'
                f'<div style="padding:8px;">{rows_html}</div>'
                f'<div style="padding:6px 12px 8px;border-top:1px solid #1e2d5a;">'
                f'<span style="color:#4a5568;font-size:0.62rem;">Verde = clasificado predicho</span>'
                f'</div></div>'
            )
            col.markdown(card_html, unsafe_allow_html=True)


# ===========================================================================
# PAGE 2 — BRACKET
# ===========================================================================
def page_bracket():
    st.markdown(
        '<h1 style="margin-bottom:4px;">Cuadro de la Fase Final</h1>'
        '<p style="color:#8892b0;font-size:0.85rem;margin-top:0;">'
        "Predicción del cuadro completo desde la Ronda de 32 — modelo Elo. "
        "El ganador de cada cruce es el favorito según las probabilidades.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    bk = _compute_static_bracket()
    champ_d = _td(bk["champion"])
    runner_d = _td(bk["runner_up"])

    # Champion spotlight
    st.markdown(
        f'<div style="display:flex;gap:16px;margin-bottom:20px;">'
        f'<div style="background:linear-gradient(135deg,#b8860b,#FFD700,#b8860b);'
        f'border-radius:14px;padding:18px 24px;text-align:center;flex:1;">'
        f'<div style="font-size:2.2rem;">{FLAGS.get(champ_d["team"],"")}</div>'
        f'<div style="color:#000;font-size:0.58rem;font-weight:800;letter-spacing:0.15em;'
        f'margin:4px 0;">CAMPEON PREDICHO</div>'
        f'<div style="color:#000;font-weight:900;font-size:1.3rem;">{champ_d["team"]}</div>'
        f'<div style="color:#333;font-size:0.8rem;margin-top:2px;">'
        f'{champ_d.get("champion",0)*100:.1f}% de probabilidad</div>'
        f'</div>'
        f'<div style="background:linear-gradient(135deg,#1a2444,#2a3a5c);'
        f'border:1px solid #4a5568;border-radius:14px;padding:18px 24px;text-align:center;flex:1;">'
        f'<div style="font-size:2.2rem;">{FLAGS.get(runner_d["team"],"")}</div>'
        f'<div style="color:#8892b0;font-size:0.58rem;font-weight:800;letter-spacing:0.15em;'
        f'margin:4px 0;">FINALISTA PREDICHO</div>'
        f'<div style="color:#fff;font-weight:900;font-size:1.3rem;">{runner_d["team"]}</div>'
        f'<div style="color:#8892b0;font-size:0.8rem;margin-top:2px;">'
        f'{runner_d.get("champion",0)*100:.1f}% de probabilidad</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Two-sided bracket with connector lines ─────────────────────────────
    S = 82  # card unit height (px)

    # Absolute y-centers of match cards in each round
    yR32 = [i * S + S // 2 for i in range(8)]                        # [41,123,…,615]
    yR16 = [S // 2 + i * (S + S) + S // 2 for i in range(4)]         # [82,246,410,574]
    yQF  = [3 * S // 2 + i * (S + 3 * S) + S // 2 for i in range(2)] # [164,492]
    ySF  = 7 * S // 2 + S // 2                                        # 328

    # Column heights (pad + cards + gaps)
    hR32 = 8 * S                           # 656
    hR16 = S // 2 + 4 * S + 3 * S         # 615
    hQF  = 3 * S // 2 + 2 * S + 3 * S     # 533
    hSF  = 7 * S // 2 + S                  # 369

    # Round label colours: cool blue → purple → gold as rounds converge
    CL = {"r32": "#4a6888", "r16": "#3a5ab0", "qf": "#5540b0", "sf": "#9030c0", "fin": "#FFD700"}
    # Connector colours: matching progression
    CC = {1: "#2d4068", 2: "#3a3898", 3: "#7030a8", 4: "#b828d0"}

    MW = 140  # column min-width

    r32l = _bk_col("RONDA 32",  bk["r32"][:8],  bk["r32_w"][:8],  0,       0,    MW, CL["r32"])
    c1l  = _bk_connector(yR32, yR16, hR32, CC[1])
    r16l = _bk_col("OCTAVOS",   bk["r16"][:4],  bk["r16_w"][:4],  S//2,    S,    MW, CL["r16"])
    c2l  = _bk_connector(yR16, yQF,  hR16, CC[2])
    qfl  = _bk_col("CUARTOS",   bk["qf"][:2],   bk["qf_w"][:2],   3*S//2,  3*S,  MW, CL["qf"])
    c3l  = _bk_connector(yQF,  [ySF], hQF,  CC[3])
    sfl  = _bk_col("SEMIS",     bk["sf"][:1],   bk["sf_w"][:1],   7*S//2,  0,    MW, CL["sf"])
    c4l  = _bk_sf_line(ySF, hSF, CC[4])
    fin  = _bk_col("★ FINAL ★", [bk["final"]], [bk["champion"]],  7*S//2,  0,    MW, CL["fin"], is_final=True)
    c4r  = _bk_sf_line(ySF, hSF, CC[4])
    sfr  = _bk_col("SEMIS",     bk["sf"][1:],   bk["sf_w"][1:],   7*S//2,  0,    MW, CL["sf"])
    c3r  = _bk_connector(yQF,  [ySF], hQF,  CC[3], flip=True)
    qfr  = _bk_col("CUARTOS",   bk["qf"][2:],   bk["qf_w"][2:],   3*S//2,  3*S,  MW, CL["qf"])
    c2r  = _bk_connector(yR16, yQF,  hR16, CC[2], flip=True)
    r16r = _bk_col("OCTAVOS",   bk["r16"][4:],  bk["r16_w"][4:],  S//2,    S,    MW, CL["r16"])
    c1r  = _bk_connector(yR32, yR16, hR32, CC[1], flip=True)
    r32r = _bk_col("RONDA 32",  bk["r32"][8:],  bk["r32_w"][8:],  0,       0,    MW, CL["r32"])

    min_w = 9 * MW + 8 * 12 + 40  # 9 cols + 8 connectors (12px each) + padding
    st.markdown(
        '<div style="background:#080c18;border:1px solid #1a2640;border-radius:14px;'
        f'padding:20px 16px;overflow-x:auto;zoom:0.94;">'
        f'<div style="display:flex;align-items:flex-start;gap:0;min-width:{min_w}px;">'
        + r32l + c1l + r16l + c2l + qfl + c3l + sfl + c4l
        + fin
        + c4r + sfr + c3r + qfr + c2r + r16r + c1r + r32r
        + '</div></div>',
        unsafe_allow_html=True,
    )


# ===========================================================================
# PAGE 3 — PROBABILIDADES
# ===========================================================================
def page_probabilidades():
    st.markdown(
        '<h1 style="margin-bottom:4px;">Probabilidades por Partido</h1>'
        '<p style="color:#8892b0;font-size:0.85rem;margin-top:0;">'
        "Probabilidades empíricas extraídas de 10.000 simulaciones Monte Carlo — "
        "reflejan el nivel real de los rivales en cada grupo</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    groups_list = sorted(matches["group"].dropna().unique())
    sel_group = st.selectbox("Selecciona un grupo", groups_list)

    grp_matches = matches[matches["group"] == sel_group].sort_values("date")
    grp_teams = groups_df[groups_df["group"] == sel_group]["team"].tolist()

    # Team cards
    tc = st.columns(4, gap="small")
    for i, team in enumerate(grp_teams):
        row = sim[sim["team"] == team]
        if row.empty:
            continue
        r = row.iloc[0]
        flag = FLAGS.get(team, "")
        tc[i].markdown(
            f'<div style="background:#12192d;border:1px solid #1e2d5a;border-radius:10px;'
            f'padding:12px;text-align:center;">'
            f'<div style="font-size:1.8rem;">{flag}</div>'
            f'<div style="color:#fff;font-weight:700;font-size:0.85rem;margin:4px 0;">{team}</div>'
            f'<div style="color:#FFD700;font-size:1rem;font-weight:800;">{r["champion"]*100:.1f}%</div>'
            f'<div style="color:#8892b0;font-size:0.65rem;">prob. campeon</div>'
            f'<div style="color:#00a651;font-size:0.75rem;margin-top:4px;">'
            f'Clasif.: {r["qualify"]*100:.0f}%</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Match stacked bars — probabilidades de la simulación Monte Carlo
    labels = [f"{m['home_team']} vs {m['away_team']}" for _, m in grp_matches.iterrows()]
    home_p = [m["sim_prob_home_win"] * 100 for _, m in grp_matches.iterrows()]
    draw_p = [m["sim_prob_draw"]     * 100 for _, m in grp_matches.iterrows()]
    away_p = [m["sim_prob_away_win"] * 100 for _, m in grp_matches.iterrows()]
    dates  = [m["date"].strftime("%d %b") for _, m in grp_matches.iterrows()]
    preds  = [
        m["home_team"] if m["sim_prob_home_win"] > m["sim_prob_away_win"] and m["sim_prob_home_win"] > m["sim_prob_draw"]
        else (m["away_team"] if m["sim_prob_away_win"] > m["sim_prob_home_win"] and m["sim_prob_away_win"] > m["sim_prob_draw"]
        else "Empate")
        for _, m in grp_matches.iterrows()
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Local", x=home_p, y=labels, orientation="h",
        marker_color="#003DA6",
        text=[f"{v:.0f}%" for v in home_p], textposition="inside", insidetextanchor="middle",
        hovertemplate="Local: %{x:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Empate", x=draw_p, y=labels, orientation="h",
        marker_color="#4a5568",
        text=[f"{v:.0f}%" for v in draw_p], textposition="inside", insidetextanchor="middle",
        hovertemplate="Empate: %{x:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Visitante", x=away_p, y=labels, orientation="h",
        marker_color="#C8102E",
        text=[f"{v:.0f}%" for v in away_p], textposition="inside", insidetextanchor="middle",
        hovertemplate="Visitante: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        barmode="stack",
        height=360,
        margin=dict(l=0, r=0, t=10, b=10),
        plot_bgcolor="#0d1225", paper_bgcolor="#0d1225",
        font=dict(color="#ffffff"),
        xaxis=dict(range=[0, 100], visible=False, gridcolor="#1e2d5a"),
        yaxis=dict(autorange="reversed", gridcolor="#1e2d5a"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(color="#ffffff"),
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Table
    detail = pd.DataFrame({
        "Fecha": dates,
        "Local": [m["home_team"] for _, m in grp_matches.iterrows()],
        "Visitante": [m["away_team"] for _, m in grp_matches.iterrows()],
        "Prob. local %": [f"{v:.1f}" for v in home_p],
        "Prob. empate %": [f"{v:.1f}" for v in draw_p],
        "Prob. visitante %": [f"{v:.1f}" for v in away_p],
        "Prediccion": preds,
    })
    st.dataframe(detail, use_container_width=True, hide_index=True)


# ===========================================================================
# PAGE 4 — RESUMEN EJECUTIVO
# ===========================================================================
def page_resumen():
    st.markdown(
        '<h1 style="margin-bottom:4px;">Resumen</h1>'
        '<p style="color:#8892b0;font-size:0.85rem;margin-top:0;">'
        "Visión global del Mundial 2026 — 48 equipos, 10.000 simulaciones Monte Carlo</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # KPIs
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Equipos", "48")
    k2.metric("Partidos grupo", "72")
    k3.metric("Simulaciones", "10.000")
    k4.metric("Accuracy modelo", "61.6%")
    k5.metric("Gran favorito", "España")

    st.divider()

    col_bar, col_donut = st.columns([3, 2], gap="large")

    with col_bar:
        st.markdown("### Top 12 favoritos al titulo")
        top12 = sim.nlargest(12, "champion").copy()
        top12["pct"] = top12["champion"] * 100
        top12["color"] = top12["confederation"].map(CONF_COLORS).fillna("#888")
        top12["label"] = top12.apply(
            lambda r: f'{FLAGS.get(r["team"],"")} {r["team"]}', axis=1
        )

        fig_bar = go.Figure(go.Bar(
            x=top12["pct"],
            y=top12["label"],
            orientation="h",
            marker=dict(
                color=top12["color"].tolist(),
                line=dict(color="#FFD700", width=0.5),
            ),
            text=[f"{v:.1f}%" for v in top12["pct"]],
            textposition="outside",
            textfont=dict(color="#ffffff", size=11),
            hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
        ))
        fig_bar.update_layout(
            yaxis=dict(categoryorder="total ascending", gridcolor="#1e2d5a", color="#ffffff"),
            xaxis=dict(range=[0, 26], visible=False, gridcolor="#1e2d5a"),
            height=420,
            margin=dict(l=0, r=70, t=10, b=10),
            plot_bgcolor="#0d1225", paper_bgcolor="#0d1225",
            font=dict(color="#ffffff"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_donut:
        st.markdown("### Por confederacion")
        conf_agg = (
            sim.groupby("confederation")["champion"].sum().reset_index()
            .sort_values("champion", ascending=False)
        )
        conf_agg["pct"] = conf_agg["champion"] * 100

        fig_pie = go.Figure(go.Pie(
            labels=conf_agg["confederation"],
            values=conf_agg["pct"].round(1),
            hole=0.55,
            marker=dict(
                colors=[CONF_COLORS.get(c, "#888") for c in conf_agg["confederation"]],
                line=dict(color="#0a0e1a", width=2),
            ),
            textinfo="label+percent",
            textfont=dict(color="#ffffff", size=11),
            hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
        ))
        fig_pie.update_layout(
            height=420,
            margin=dict(l=0, r=0, t=10, b=10),
            showlegend=False,
            paper_bgcolor="#0d1225",
            font=dict(color="#ffffff"),
            annotations=[dict(
                text='<b style="font-size:14px">Prob.<br>Campeon</b>',
                x=0.5, y=0.5, showarrow=False,
                font=dict(color="#FFD700", size=13),
            )],
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()
    st.markdown("### Ranking completo — 48 selecciones")

    table = sim[["team","group","confederation","elo_rating"] + ROUNDS].copy()
    table = table.sort_values("champion", ascending=False).reset_index(drop=True)
    display = pd.DataFrame()
    display["#"] = range(1, len(table)+1)
    display["Equipo"] = table["team"].apply(lambda t: f'{FLAGS.get(t,"")} {t}')
    display["Grupo"] = table["group"]
    display["Confed."] = table["confederation"]
    display["Elo"] = table["elo_rating"].fillna(0).astype(int)
    for col, lbl in zip(ROUNDS, ROUND_LABELS):
        display[lbl] = (table[col] * 100).round(1).astype(str) + "%"

    st.dataframe(display, use_container_width=True, hide_index=True, height=520)


_SG_SORT_CSS = """
.sortable-component { background: transparent; }
.sortable-container {
    background: #0d1225;
    border: 1px solid #1e2d5a;
    border-radius: 10px;
    overflow: hidden;
    counter-reset: rank;
}
.sortable-container-header {
    background: linear-gradient(90deg, #1a2444, #0d1225);
    color: #FFD700;
    font-weight: 900;
    font-size: 14px;
    letter-spacing: 0.08em;
    padding: 10px 14px;
    border-bottom: 2px solid #FFD700;
}
.sortable-container-body { background: #0d1225; padding: 5px 6px 6px; }
.sortable-item {
    background: linear-gradient(90deg, #0a1e11, #0d1225);
    color: #ffffff;
    border-left: 4px solid #00a651;
    border-radius: 5px;
    padding: 9px 11px;
    margin: 2px 0;
    font-size: 13px;
    font-weight: 600;
    cursor: grab;
    counter-increment: rank;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: filter 0.1s;
}
.sortable-item::before {
    content: counter(rank) "° ";
    color: #FFD700;
    font-weight: 900;
    font-size: 11px;
    margin-right: 4px;
}
.sortable-item:nth-child(3) {
    background: #0d1225;
    border-left-color: #e6a817;
    color: #ccd6f6;
    margin-top: 5px;
    border-top: 1px dashed #2a3550;
}
.sortable-item:nth-child(4) {
    background: #0a0e1a;
    border-left-color: #4a5568;
    color: #8892b0;
}
.sortable-item:hover { filter: brightness(1.35); }
.sortable-item.dragging {
    background: #FFD700;
    color: #000000;
    border-left-color: #b8860b;
    box-shadow: 0 4px 18px rgba(255,215,0,0.45);
    font-weight: 700;
    opacity: 0.96;
}
.sortable-item.dragging::before { content: none; counter-increment: none; }
"""


# ===========================================================================
# PAGE 5 — SIMULADOR (grupos + eliminatoria en tabs)
# ===========================================================================
def page_simulador():
    st.markdown("""
    <style>
    [data-testid="baseButton-primary"] {
        background-color:#FFD700 !important; color:#000 !important;
        border:1px solid #b8860b !important; font-weight:700 !important;
        text-align:left !important; border-radius:5px !important;
        padding:6px 10px !important; height:auto !important; font-size:0.78rem !important;
    }
    [data-testid="baseButton-secondary"] {
        background-color:#0d1225 !important; color:#8892b0 !important;
        border:1px solid #1e2d5a !important; font-weight:500 !important;
        text-align:left !important; border-radius:5px !important;
        padding:6px 10px !important; height:auto !important; font-size:0.78rem !important;
    }
    [data-testid="baseButton-primary"]:hover { filter:brightness(1.12) !important; }
    [data-testid="baseButton-secondary"]:hover {
        background-color:#12192d !important; color:#ccd6f6 !important;
        border-color:#2d3e6a !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<h1 style="margin-bottom:4px;">Simulador</h1>'
        '<p style="color:#8892b0;font-size:0.85rem;margin-top:0;">'
        "Ajusta la clasificación de grupos y simula el cuadro eliminatorio en tiempo real</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    _init_sim_state()

    # ── Detect group_picks changes and flush bracket win keys ─────────────────
    _gp_sig = "|".join(
        f"{g}:{p.get('1st','')},{p.get('2nd','')}"
        for g, p in sorted(st.session_state.group_picks.items())
    )
    if st.session_state.get("_gp_sig") != _gp_sig:
        for _k in [k for k in st.session_state
                   if k.startswith("win_") and not k.startswith("win_bk_")]:
            del st.session_state[_k]
        st.session_state["_gp_sig"] = _gp_sig

    tab_g, tab_e = st.tabs(["🏟️  Fase de Grupos", "⚔️  Eliminatoria"])

    # ── TAB 1: GRUPOS ────────────────────────────────────────────────────────
    with tab_g:
        st.markdown(
            '<p style="color:#8892b0;font-size:0.82rem;padding:8px 0 6px;">'
            "Arrastra para reordenar · verde = clasifica directo · "
            "naranja = posible mejor 3.º</p>",
            unsafe_allow_html=True,
        )

        all_groups = sorted(groups_df["group"].unique())
        qualify_map = dict(zip(sim["team"], sim["qualify"]))

        for row_i in range(3):
            gcols = st.columns(4, gap="medium")
            for col_i, gcol in enumerate(gcols):
                grp_idx = row_i * 4 + col_i
                if grp_idx >= len(all_groups):
                    break
                grp = all_groups[grp_idx]
                grp_teams = (
                    sim[sim["group"] == grp]
                    .sort_values("qualify", ascending=False)["team"]
                    .tolist()
                )
                cur1 = st.session_state.group_picks[grp].get("1st", grp_teams[0])
                cur2 = st.session_state.group_picks[grp].get("2nd", grp_teams[1])
                cur3 = st.session_state.group_picks[grp].get("3rd", grp_teams[2])
                seen, ordered = set(), []
                for t in [cur1, cur2, cur3] + grp_teams:
                    if t in grp_teams and t not in seen:
                        ordered.append(t)
                        seen.add(t)

                items, item_to_team = [], {}
                for team in ordered:
                    flag = FLAGS.get(team, "")
                    q = f"{qualify_map.get(team, 0)*100:.0f}%"
                    disp = f"{flag} {team}  {q}"
                    items.append(disp)
                    item_to_team[disp] = team

                with gcol:
                    result = sort_items(
                        items,
                        header=f"GRUPO {grp}",
                        direction="vertical",
                        custom_style=_SG_SORT_CSS,
                        key=f"sort_{grp}",
                    )

                if result != items:
                    new_order = [
                        item_to_team.get(it, grp_teams[i])
                        for i, it in enumerate(result)
                    ]
                    if len(new_order) >= 3:
                        st.session_state.group_picks[grp]["1st"] = new_order[0]
                        st.session_state.group_picks[grp]["2nd"] = new_order[1]
                        st.session_state.group_picks[grp]["3rd"] = new_order[2]
                        st.rerun()

        st.markdown(
            '<p style="color:#4a5568;font-size:0.75rem;padding-top:10px;">'
            "Los 8 mejores terceros clasifican automáticamente · "
            "Cambia a ⚔️ Eliminatoria para ver el cuadro actualizado</p>",
            unsafe_allow_html=True,
        )

    # ── TAB 2: ELIMINATORIA ──────────────────────────────────────────────────
    with tab_e:
        r32 = _build_r32(st.session_state.group_picks)
        bk = _resolve_bracket(r32)

        champ, runner = bk["champion"], bk["runner_up"]
        champ_d, runner_d = _td(champ), _td(runner)

        # ── Clasificados de grupos (badge grid) ──────────────────────────────
        gp = st.session_state.group_picks
        all_g = sorted(gp.keys())
        badge_rows = [all_g[:6], all_g[6:]]

        st.markdown(
            '<div style="color:#FFD700;font-weight:900;font-size:0.65rem;'
            'letter-spacing:0.12em;padding:10px 0 6px;">'
            'CLASIFICADOS DE GRUPOS → RONDA DE 32</div>',
            unsafe_allow_html=True,
        )
        for br in badge_rows:
            badge_cols = st.columns(len(br), gap="small")
            for bcol, g in zip(badge_cols, br):
                t1n = gp[g].get("1st", "")
                t2n = gp[g].get("2nd", "")
                f1, f2 = FLAGS.get(t1n, ""), FLAGS.get(t2n, "")
                bcol.markdown(
                    f'<div style="background:#12192d;border:1px solid #1e2d5a;'
                    f'border-radius:8px;padding:7px 8px;text-align:center;">'
                    f'<div style="color:#FFD700;font-size:0.6rem;font-weight:900;'
                    f'letter-spacing:0.08em;margin-bottom:5px;">GRP {g}</div>'
                    f'<div style="display:flex;align-items:center;gap:4px;'
                    f'margin-bottom:3px;justify-content:flex-start;">'
                    f'<span style="background:#00a651;color:#fff;font-size:0.48rem;'
                    f'font-weight:900;padding:1px 4px;border-radius:3px;flex-shrink:0;">1°</span>'
                    f'<span style="font-size:0.8rem;">{f1}</span>'
                    f'<span style="color:#fff;font-size:0.65rem;font-weight:600;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{t1n}</span>'
                    f'</div>'
                    f'<div style="display:flex;align-items:center;gap:4px;'
                    f'justify-content:flex-start;">'
                    f'<span style="background:#e6a817;color:#000;font-size:0.48rem;'
                    f'font-weight:900;padding:1px 4px;border-radius:3px;flex-shrink:0;">2°</span>'
                    f'<span style="font-size:0.8rem;">{f2}</span>'
                    f'<span style="color:#ccd6f6;font-size:0.65rem;font-weight:600;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{t2n}</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

        st.divider()

        # ── 2-sided interactive bracket (R32 outer, Final center) ────────────
        st.markdown(
            '<div style="color:#FFD700;font-weight:900;font-size:0.65rem;'
            'letter-spacing:0.12em;padding:2px 0 10px;">'
            'CUADRO ELIMINATORIO · haz clic para elegir quién pasa</div>',
            unsafe_allow_html=True,
        )

        C = 112
        br_cols = st.columns([2.8, 2.4, 2.0, 1.6, 2.0, 1.6, 2.0, 2.4, 2.8], gap="small")
        c_r32l, c_r16l, c_qfl, c_sfl, c_fin, c_sfr, c_qfr, c_r16r, c_r32r = br_cols

        _HDR = ('<div style="color:#8892b0;font-size:0.55rem;font-weight:800;'
                'letter-spacing:0.1em;text-align:center;border-bottom:1px solid #1e2d5a;'
                'padding-bottom:4px;margin-bottom:6px;text-transform:uppercase;white-space:nowrap;">')
        for _col, _lbl in [
            (c_r32l, "RONDA 32"), (c_r16l, "OCTAVOS"), (c_qfl, "CUARTOS"),
            (c_sfl, "SEMIS"), (c_fin, "★ FINAL ★"), (c_sfr, "SEMIS"),
            (c_qfr, "CUARTOS"), (c_r16r, "OCTAVOS"), (c_r32r, "RONDA 32"),
        ]:
            _col.markdown(f'{_HDR}{_lbl}</div>', unsafe_allow_html=True)

        # R32 left (matches 0-7)
        for i in range(8):
            _interactive_btn_card(c_r32l, *r32[i], f"r32_{i}")

        # R16 left (matches 0-3)
        c_r16l.markdown(f'<div style="height:{C//2}px"></div>', unsafe_allow_html=True)
        for i in range(4):
            _interactive_btn_card(c_r16l, *bk["r16"][i], f"r16_{i}")
            if i < 3:
                c_r16l.markdown(f'<div style="height:{C}px"></div>', unsafe_allow_html=True)

        # QF left (matches 0-1)
        c_qfl.markdown(f'<div style="height:{int(C*1.5)}px"></div>', unsafe_allow_html=True)
        _interactive_btn_card(c_qfl, *bk["qf"][0], "qf_0")
        c_qfl.markdown(f'<div style="height:{C*3}px"></div>', unsafe_allow_html=True)
        _interactive_btn_card(c_qfl, *bk["qf"][1], "qf_1")

        # SF left (match 0)
        c_sfl.markdown(f'<div style="height:{int(C*3.5)}px"></div>', unsafe_allow_html=True)
        _interactive_btn_card(c_sfl, *bk["sf"][0], "sf_0")

        # Final (center)
        c_fin.markdown(f'<div style="height:{int(C*3.5)}px"></div>', unsafe_allow_html=True)
        _interactive_btn_card(c_fin, *bk["final"], "final_0")

        # SF right (match 1)
        c_sfr.markdown(f'<div style="height:{int(C*3.5)}px"></div>', unsafe_allow_html=True)
        _interactive_btn_card(c_sfr, *bk["sf"][1], "sf_1")

        # QF right (matches 2-3)
        c_qfr.markdown(f'<div style="height:{int(C*1.5)}px"></div>', unsafe_allow_html=True)
        _interactive_btn_card(c_qfr, *bk["qf"][2], "qf_2")
        c_qfr.markdown(f'<div style="height:{C*3}px"></div>', unsafe_allow_html=True)
        _interactive_btn_card(c_qfr, *bk["qf"][3], "qf_3")

        # R16 right (matches 4-7)
        c_r16r.markdown(f'<div style="height:{C//2}px"></div>', unsafe_allow_html=True)
        for i in range(4, 8):
            _interactive_btn_card(c_r16r, *bk["r16"][i], f"r16_{i}")
            if i < 7:
                c_r16r.markdown(f'<div style="height:{C}px"></div>', unsafe_allow_html=True)

        # R32 right (matches 8-15)
        for i in range(8, 16):
            _interactive_btn_card(c_r32r, *r32[i], f"r32_{i}")

        st.divider()

        # ── Champion spotlight ────────────────────────────────────────────────
        st.markdown(
            f'<div style="display:flex;gap:14px;margin:4px 0 14px;">'
            f'<div style="background:linear-gradient(135deg,#b8860b,#FFD700,#b8860b);'
            f'border-radius:12px;padding:14px 22px;text-align:center;flex:1;">'
            f'<div style="font-size:1.8rem;">{FLAGS.get(champ,"")}</div>'
            f'<div style="color:#000;font-size:0.52rem;font-weight:900;letter-spacing:0.16em;'
            f'margin:3px 0;">🏆 CAMPEÓN</div>'
            f'<div style="color:#000;font-weight:900;font-size:1.1rem;">{champ}</div>'
            f'<div style="color:#333;font-size:0.7rem;">'
            f'{champ_d.get("champion",0)*100:.1f}% según modelo</div>'
            f'</div>'
            f'<div style="background:linear-gradient(135deg,#1a2444,#2a3a5c);'
            f'border:1px solid #4a5568;border-radius:12px;padding:14px 22px;'
            f'text-align:center;flex:1;">'
            f'<div style="font-size:1.8rem;">{FLAGS.get(runner,"")}</div>'
            f'<div style="color:#8892b0;font-size:0.52rem;font-weight:900;letter-spacing:0.16em;'
            f'margin:3px 0;">🥈 FINALISTA</div>'
            f'<div style="color:#fff;font-weight:900;font-size:1.1rem;">{runner}</div>'
            f'<div style="color:#8892b0;font-size:0.7rem;">'
            f'{runner_d.get("champion",0)*100:.1f}% según modelo</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        rcol, _ = st.columns([1, 4])
        if rcol.button("↺  Resetear bracket", key="sim_reset"):
            for k in list(st.session_state.keys()):
                if k.startswith("win_"):
                    del st.session_state[k]
            st.rerun()


# ===========================================================================
# PAGE 8 — SOBRE EL PROYECTO
# ===========================================================================
def page_sobre_proyecto():
    st.markdown(
        '<h1 style="margin-bottom:4px;">Sobre el Proyecto</h1>'
        '<p style="color:#8892b0;font-size:0.85rem;margin-top:0;">'
        "Cómo funciona el modelo y qué hay detrás de las predicciones</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Partidos historicos", "49.328")
    m2.metric("Periodo analizado", "1872–2026")
    m3.metric("Accuracy modelo", "61.6%")
    m4.metric("Simulaciones", "10.000")

    st.divider()

    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        st.markdown(
            '<div style="background:#12192d;border:1px solid #1e2d5a;border-radius:10px;padding:20px;">'
            '<div style="color:#FFD700;font-weight:900;font-size:0.7rem;letter-spacing:0.12em;'
            'text-transform:uppercase;margin-bottom:12px;">Datos</div>'
            '<ul style="color:#ccd6f6;font-size:0.82rem;line-height:1.8;padding-left:16px;margin:0;">'
            '<li><b>49.328 partidos</b> internacionales (1872–2026)</li>'
            '<li>Ratings <b>Elo</b> actualizados a mayo 2026</li>'
            '<li>Ranking <b>FIFA</b> historico desde 2020</li>'
            '<li>Calendario oficial del Mundial 2026 (48 equipos, 12 grupos)</li>'
            '</ul></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div style="background:#12192d;border:1px solid #1e2d5a;border-radius:10px;padding:20px;">'
            '<div style="color:#FFD700;font-weight:900;font-size:0.7rem;letter-spacing:0.12em;'
            'text-transform:uppercase;margin-bottom:12px;">Modelo ML</div>'
            '<ul style="color:#ccd6f6;font-size:0.82rem;line-height:1.8;padding-left:16px;margin:0;">'
            '<li><b>Regresión Logística</b> multiclase (victoria / empate / derrota)</li>'
            '<li><b>41 variables</b>: diferencia Elo, ranking FIFA, forma reciente '
            '(últimos 5/10 partidos), head-to-head, experiencia en Mundiales</li>'
            '<li>Validación <b>temporal</b>: entrenado hasta 2018, validado 2019–2022, '
            'test 2023–2025</li>'
            '<li>Log-loss <b>0.845</b> · Brier <b>0.166</b></li>'
            '</ul></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div style="background:#12192d;border:1px solid #1e2d5a;border-radius:10px;padding:20px;">'
            '<div style="color:#FFD700;font-weight:900;font-size:0.7rem;letter-spacing:0.12em;'
            'text-transform:uppercase;margin-bottom:12px;">Simulación Monte Carlo</div>'
            '<ul style="color:#ccd6f6;font-size:0.82rem;line-height:1.8;padding-left:16px;margin:0;">'
            '<li><b>10.000 simulaciones</b> completas del torneo</li>'
            '<li>Cada simulación sortea los 72 partidos de grupos y toda la fase eliminatoria</li>'
            '<li>Las probabilidades reflejan el <b>nivel real del grupo</b>, '
            'no solo el partido aislado</li>'
            '<li>Probabilidades en el bracket: fórmula <b>Elo</b> para cada cruce específico</li>'
            '</ul></div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("### Principales predicciones")

    top5 = sim.nlargest(5, "champion").reset_index(drop=True)
    for _, row in top5.iterrows():
        flag = FLAGS.get(row["team"], "")
        champ_pct = row["champion"] * 100
        qualify_pct = row["qualify"] * 100
        elo_val = int(row["elo_rating"]) if pd.notna(row.get("elo_rating")) else "—"
        st.markdown(
            f'<div style="background:#12192d;border-left:4px solid #FFD700;'
            f'border-radius:0 8px 8px 0;padding:12px 18px;margin-bottom:8px;'
            f'display:flex;justify-content:space-between;align-items:center;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<span style="font-size:1.4rem;">{flag}</span>'
            f'<div>'
            f'<div style="color:#fff;font-weight:700;font-size:0.9rem;">{row["team"]}</div>'
            f'<div style="color:#8892b0;font-size:0.65rem;">'
            f'{row["confederation"]} · Elo {elo_val}</div>'
            f'</div></div>'
            f'<div style="text-align:right;">'
            f'<div style="color:#FFD700;font-weight:800;font-size:1rem;">{champ_pct:.1f}% campeon</div>'
            f'<div style="color:#00a651;font-size:0.72rem;">{qualify_pct:.0f}% clasifica</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("### Limitaciones del modelo")
    st.markdown(
        '<div style="background:#12192d;border:1px solid #1e2d5a;border-radius:10px;padding:20px;">'
        '<ul style="color:#ccd6f6;font-size:0.82rem;line-height:1.9;padding-left:18px;margin:0;">'
        '<li>El modelo predice en base a <b>rendimiento historico</b> — no considera lesiones, '
        'sanciones ni condicion fisica actual de los jugadores.</li>'
        '<li>El formato de <b>48 equipos</b> es nuevo en 2026; el modelo nunca ha entrenado '
        'con datos de ese formato exacto.</li>'
        '<li>El ranking FIFA mas reciente disponible es de <b>septiembre 2025</b> '
        '(no hay datos publicados post-clasificacion).</li>'
        '<li>XGBoost fue descartado por incompatibilidades en macOS; '
        'la <b>Regresión Logística</b> resultó ser el modelo con mejor rendimiento en validación.</li>'
        '</ul></div>',
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("### Stack técnico")
    tools = [
        ("Python 3.11", "#3776AB"),
        ("scikit-learn", "#F89939"),
        ("pandas · numpy", "#e86b1a"),
        ("Streamlit", "#FF4B4B"),
        ("Plotly", "#3D9970"),
    ]
    t_cols = st.columns(5)
    for col, (name, color) in zip(t_cols, tools):
        col.markdown(
            f'<div style="background:{color}22;border:1px solid {color}88;'
            f'border-radius:8px;padding:14px;text-align:center;">'
            f'<div style="color:{color};font-weight:700;font-size:0.78rem;">{name}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if page == "Grupos":
    page_grupos()
elif page == "Bracket":
    page_bracket()
elif page == "Probabilidades":
    page_probabilidades()
elif page == "Resumen":
    page_resumen()
elif page == "Simulador":
    page_simulador()
else:
    page_sobre_proyecto()
