"""
Motor de simulación Monte Carlo para el Mundial de Fútbol 2026.

Formato del torneo:
- 48 equipos en 12 grupos (A-L) de 4 equipos cada uno.
- Fase de grupos: round-robin; los 2 primeros de cada grupo + los 8 mejores
  terceros clasifican = 32 equipos a la fase eliminatoria.
- Eliminatorias: Ronda de 32 → Octavos → Cuartos → Semis → Final.

Bracket de la Ronda de 32 (aproximado, basado en pods de grupos):
  Los 12 grupos se dividen en 4 pods de 3; los partidos se intercalan para
  garantizar que dos equipos del mismo grupo no se crucen hasta los Cuartos.
  Las 4 plazas restantes las ocupan los 8 mejores terceros (seeded 1-8).
  Nota: el bracket oficial de la FIFA puede diferir en detalles específicos.

API pública:
    load_data()                       → groups_df, predictions_df, features_df, model
    build_team_stats(features_df, groups_df) → dict por equipo
    build_prob_cache(teams, team_stats, model) → dict (home,away) → (pH,pD,pA)
    simulate_tournament(...)          → dict equipo → ronda_alcanzada
    run_monte_carlo(n, seed)          → pd.DataFrame con probabilidades
    save_results(df, path)            → Path
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
_DATA_PROCESSED = _ROOT / "data" / "processed"
_DATA_RAW = _ROOT / "data" / "raw"
_MODELS_DIR = _ROOT / "src" / "models"
_REPORTS_DIR = _ROOT / "reports"

# ---------------------------------------------------------------------------
# Constantes del torneo
# ---------------------------------------------------------------------------
GROUPS = list("ABCDEFGHIJKL")

# Rondas en orden creciente de avance
ROUNDS = [
    "group_stage",    # eliminado en grupos
    "round_of_32",    # clasificó desde grupos, perdió en R32
    "round_of_16",    # ganó R32, perdió en R16
    "quarter_final",  # ganó R16, perdió en QF
    "semi_final",     # ganó QF, perdió en SF
    "final",          # ganó SF, perdió la Final
    "champion",       # ganó la Final
]

# Columnas de salida del DataFrame de resultados (se excluye "group_stage" → siempre 1.0)
OUTPUT_ROUNDS = ["qualify", "round_of_16", "quarter_final", "semi_final", "final", "champion"]

# Bracket oficial FIFA WC 2026 — Ronda de 32 (partidos 73-88)
# Slots fijos: '1A' = 1º grupo A, '2B' = 2º grupo B
# Slots dinámicos: '3rd_k' = k-ésimo mejor tercer clasificado (k=1..8)
#
# Estructura del árbol (cada par de R32 → un partido de R16 → QF → SF → Final):
#   Mitad izquierda → SF P101: QF P97 (R16 P89+P90)  +  QF P98 (R16 P93+P94)
#   Mitad derecha  → SF P102: QF P99 (R16 P91+P92)  +  QF P100 (R16 P95+P96)
# Garantía: 1º y 2º del mismo grupo siempre en mitades opuestas → solo se pueden
# ver en la FINAL.
R32_TEMPLATE = [
    # ── Mitad izquierda → SF P101 ──────────────────────────────────────────
    # QF P97: R16 P89 (W0 vs W1)  +  R16 P90 (W2 vs W3)
    ("1E",  "3rd_1"),   # 0  – P74
    ("1I",  "3rd_2"),   # 1  – P77
    ("2A",  "2B"),      # 2  – P73
    ("1F",  "2C"),      # 3  – P75
    # QF P98: R16 P93 (W4 vs W5)  +  R16 P94 (W6 vs W7)
    ("2K",  "2L"),      # 4  – P83
    ("1H",  "2J"),      # 5  – P84
    ("1D",  "3rd_3"),   # 6  – P81
    ("1G",  "3rd_4"),   # 7  – P82
    # ── Mitad derecha → SF P102 ────────────────────────────────────────────
    # QF P99: R16 P91 (W8 vs W9)  +  R16 P92 (W10 vs W11)
    ("1C",  "2F"),      # 8  – P76
    ("2E",  "2I"),      # 9  – P78
    ("1A",  "3rd_5"),   # 10 – P79
    ("1L",  "3rd_6"),   # 11 – P80
    # QF P100: R16 P95 (W12 vs W13)  +  R16 P96 (W14 vs W15)
    ("1J",  "2H"),      # 12 – P86
    ("2D",  "2G"),      # 13 – P88
    ("1B",  "3rd_7"),   # 14 – P85
    ("1K",  "3rd_8"),   # 15 – P87
]

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------


def load_data() -> tuple:
    """Carga grupos, predicciones, features y modelo."""
    groups_df = pd.read_csv(_DATA_RAW / "wc2026_groups.csv")
    predictions_df = pd.read_csv(_DATA_PROCESSED / "wc2026_group_stage_predictions.csv")
    features_df = pd.read_csv(_DATA_PROCESSED / "features_test.csv")
    model = joblib.load(_MODELS_DIR / "logistic_regression_final_2025.joblib")
    return groups_df, predictions_df, features_df, model


# ---------------------------------------------------------------------------
# Estadísticas por equipo
# ---------------------------------------------------------------------------


def build_team_stats(features_df: pd.DataFrame, groups_df: pd.DataFrame) -> dict:
    """Construye un lookup {equipo: dict_de_features} para predicciones en eliminatorias.

    Para cada equipo extrae ELO, ranking FIFA, forma reciente, apariciones en
    Mundiales y confederación a partir de features_test.csv.
    """
    conf_map = dict(zip(groups_df["team"], groups_df["confederation"]))
    stats: dict = {}

    for _, row in features_df.iterrows():
        for side, prefix in [("home_team", "home_"), ("away_team", "away_")]:
            team = row[side]
            if team in stats:
                continue
            stats[team] = {
                "elo": row.get(f"{prefix}elo", np.nan),
                "fifa_rank": row.get(f"{prefix}fifa_rank", np.nan),
                "confederation": conf_map.get(team, "Unknown"),
                "gf_last5": row.get(f"{prefix}gf_last5", np.nan),
                "ga_last5": row.get(f"{prefix}ga_last5", np.nan),
                "win_last5": row.get(f"{prefix}win_last5", np.nan),
                "draw_last5": row.get(f"{prefix}draw_last5", np.nan),
                "gf_last10": row.get(f"{prefix}gf_last10", np.nan),
                "ga_last10": row.get(f"{prefix}ga_last10", np.nan),
                "win_last10": row.get(f"{prefix}win_last10", np.nan),
                "draw_last10": row.get(f"{prefix}draw_last10", np.nan),
                "wc_appearances": row.get(f"{prefix}wc_appearances", 0),
            }

    return stats


# ---------------------------------------------------------------------------
# Predicción de probabilidades
# ---------------------------------------------------------------------------

# Columnas que espera el modelo (mismo orden que FEATURE_COLS_MODEL en models.py)
_NUMERIC_COLS = [
    "neutral", "is_friendly", "is_competitive", "is_world_cup", "same_confederation",
    "home_elo", "away_elo", "elo_diff",
    "home_fifa_rank", "away_fifa_rank", "fifa_rank_diff",
    "home_gf_last5", "home_ga_last5", "home_win_last5", "home_draw_last5",
    "away_gf_last5", "away_ga_last5", "away_win_last5", "away_draw_last5",
    "home_gf_last10", "home_ga_last10", "home_win_last10", "home_draw_last10",
    "away_gf_last10", "away_ga_last10", "away_win_last10", "away_draw_last10",
    "h2h_home_win_pct", "h2h_draw_pct", "h2h_away_win_pct",
    "home_rest_days", "away_rest_days",
    "home_wc_appearances", "away_wc_appearances",
]
_CATEGORICAL_COLS = ["home_confederation", "away_confederation"]
_FEATURE_COLS_MODEL = _NUMERIC_COLS + _CATEGORICAL_COLS


def _build_feature_row(
    home: str,
    away: str,
    team_stats: dict,
    neutral: bool = True,
    rest_days: float = 4.0,
) -> dict:
    """Construye un dict de features para un partido hipotético."""
    h = team_stats.get(home, {})
    a = team_stats.get(away, {})

    elo_h = h.get("elo", np.nan)
    elo_a = a.get("elo", np.nan)
    rank_h = h.get("fifa_rank", np.nan)
    rank_a = a.get("fifa_rank", np.nan)

    return {
        "neutral": int(neutral),
        "is_friendly": 0,
        "is_competitive": 1,
        "is_world_cup": 1,
        "same_confederation": int(
            h.get("confederation", "_H") == a.get("confederation", "_A")
        ),
        "home_elo": elo_h,
        "away_elo": elo_a,
        "elo_diff": (elo_h - elo_a) if pd.notna(elo_h) and pd.notna(elo_a) else np.nan,
        "home_fifa_rank": rank_h,
        "away_fifa_rank": rank_a,
        "fifa_rank_diff": (rank_a - rank_h) if pd.notna(rank_h) and pd.notna(rank_a) else np.nan,
        "home_gf_last5": h.get("gf_last5", np.nan),
        "home_ga_last5": h.get("ga_last5", np.nan),
        "home_win_last5": h.get("win_last5", np.nan),
        "home_draw_last5": h.get("draw_last5", np.nan),
        "away_gf_last5": a.get("gf_last5", np.nan),
        "away_ga_last5": a.get("ga_last5", np.nan),
        "away_win_last5": a.get("win_last5", np.nan),
        "away_draw_last5": a.get("draw_last5", np.nan),
        "home_gf_last10": h.get("gf_last10", np.nan),
        "home_ga_last10": h.get("ga_last10", np.nan),
        "home_win_last10": h.get("win_last10", np.nan),
        "home_draw_last10": h.get("draw_last10", np.nan),
        "away_gf_last10": a.get("gf_last10", np.nan),
        "away_ga_last10": a.get("ga_last10", np.nan),
        "away_win_last10": a.get("win_last10", np.nan),
        "away_draw_last10": a.get("draw_last10", np.nan),
        "h2h_home_win_pct": np.nan,
        "h2h_draw_pct": np.nan,
        "h2h_away_win_pct": np.nan,
        "home_rest_days": rest_days,
        "away_rest_days": rest_days,
        "home_wc_appearances": h.get("wc_appearances", 0),
        "away_wc_appearances": a.get("wc_appearances", 0),
        "home_confederation": h.get("confederation", "Unknown"),
        "away_confederation": a.get("confederation", "Unknown"),
    }


def build_prob_cache(
    teams: list[str],
    team_stats: dict,
    model,
    neutral: bool = True,
    rest_days: float = 4.0,
) -> dict[tuple[str, str], tuple[float, float, float]]:
    """Pre-computa probabilidades (pH, pD, pA) para todos los pares ordenados.

    Una sola llamada batch a model.predict_proba es mucho más eficiente que
    10.000 llamadas individuales durante el Monte Carlo.

    LABEL_MAP del modelo: H=0, A=1, D=2  → proba[:, 0]=pH, [:, 1]=pA, [:, 2]=pD
    """
    pairs = [(h, a) for h in teams for a in teams if h != a]
    rows = [_build_feature_row(h, a, team_stats, neutral, rest_days) for h, a in pairs]

    X = pd.DataFrame(rows)[_FEATURE_COLS_MODEL]
    proba = model.predict_proba(X)  # shape (N, 3)

    # classes_ = [0, 1, 2] → índices: 0→H, 1→A, 2→D
    classes = list(model.classes_)
    idx_h = classes.index(0)
    idx_a = classes.index(1)
    idx_d = classes.index(2)

    cache: dict = {}
    for (home, away), p in zip(pairs, proba):
        cache[(home, away)] = (float(p[idx_h]), float(p[idx_d]), float(p[idx_a]))

    return cache


# ---------------------------------------------------------------------------
# Simulación de partidos individuales
# ---------------------------------------------------------------------------


def _draw_outcome(prob_h: float, prob_d: float, prob_a: float, u: float) -> str:
    """Devuelve 'H', 'D' o 'A' según un número uniforme u ∈ [0,1)."""
    if u < prob_h:
        return "H"
    if u < prob_h + prob_d:
        return "D"
    return "A"


def _simulate_goals(
    outcome: str,
    elo_diff: float,
    rng: np.random.Generator,
) -> tuple[int, int]:
    """Simula marcador (goles_local, goles_visitante) coherente con outcome.

    Usa distribución Poisson con tasas ajustadas por diferencia de ELO.
    Los goles se usan únicamente para desempate en fase de grupos.
    """
    adj = float(elo_diff) / 400.0 * 0.6 if pd.notna(elo_diff) else 0.0
    lam_h = max(0.3, 1.15 + adj)
    lam_a = max(0.3, 1.15 - adj)

    for _ in range(50):
        gh = int(rng.poisson(lam_h))
        ga = int(rng.poisson(lam_a))
        if outcome == "H" and gh > ga:
            return gh, ga
        if outcome == "D" and gh == ga:
            return gh, ga
        if outcome == "A" and ga > gh:
            return gh, ga

    # Fallback si el rejection sampling no converge
    if outcome == "H":
        ga = max(0, int(rng.poisson(lam_a)))
        gh = ga + 1 + int(rng.poisson(0.3))
    elif outcome == "D":
        g = int(rng.poisson((lam_h + lam_a) / 2))
        gh = ga = g
    else:
        gh = max(0, int(rng.poisson(lam_h)))
        ga = gh + 1 + int(rng.poisson(0.3))

    return gh, ga


def _knockout_winner(
    home: str,
    away: str,
    prob_cache: dict,
    u: float,
) -> str:
    """Simula un partido eliminatorio (sin empates).

    P(local gana, incl. prórroga/penaltis) = prob_H + 0.5 * prob_D
    """
    prob_h, prob_d, _ = prob_cache.get((home, away), (1 / 3, 1 / 3, 1 / 3))
    return home if u < (prob_h + 0.5 * prob_d) else away


# ---------------------------------------------------------------------------
# Fase de grupos
# ---------------------------------------------------------------------------


def _simulate_group(
    group: str,
    teams: list[str],
    group_probs: dict,
    prob_cache: dict,
    team_stats: dict,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, dict]:
    """Simula los 6 partidos de un grupo.

    Devuelve (standings, match_outcomes) donde match_outcomes es un dict
    {(home, away): outcome} con outcome en {'H', 'D', 'A'}.
    standings tiene columnas [team, group, pts, gd, gf, group_pos].
    """
    record: dict = {t: {"pts": 0, "gd": 0, "gf": 0} for t in teams}
    match_outcomes: dict = {}

    for home, away in combinations(teams, 2):
        key = (home, away)
        if key in group_probs:
            prob_h, prob_d, prob_a = group_probs[key]
        else:
            prob_h, prob_d, prob_a = prob_cache.get(key, (1 / 3, 1 / 3, 1 / 3))

        outcome = _draw_outcome(prob_h, prob_d, prob_a, rng.random())
        match_outcomes[key] = outcome

        elo_h = team_stats.get(home, {}).get("elo", np.nan)
        elo_a = team_stats.get(away, {}).get("elo", np.nan)
        elo_diff = (elo_h - elo_a) if pd.notna(elo_h) and pd.notna(elo_a) else 0.0
        gh, ga = _simulate_goals(outcome, elo_diff, rng)

        record[home]["gf"] += gh
        record[away]["gf"] += ga
        record[home]["gd"] += gh - ga
        record[away]["gd"] += ga - gh

        if outcome == "H":
            record[home]["pts"] += 3
        elif outcome == "D":
            record[home]["pts"] += 1
            record[away]["pts"] += 1
        else:
            record[away]["pts"] += 3

    standings = (
        pd.DataFrame([{"team": t, "group": group, **record[t]} for t in teams])
        .sort_values(["pts", "gd", "gf"], ascending=False)
        .reset_index(drop=True)
    )
    standings["group_pos"] = standings.index + 1
    return standings, match_outcomes


def _best_thirds(all_thirds: list[dict]) -> list[str]:
    """Selecciona los 8 mejores terceros clasificados de los 12 grupos.

    Criterio: puntos → diferencia de goles → goles marcados.
    Devuelve lista ordenada de mejor (índice 0) a peor (índice 7).
    """
    df = (
        pd.DataFrame(all_thirds)
        .sort_values(["pts", "gd", "gf"], ascending=False)
        .reset_index(drop=True)
    )
    return df["team"].iloc[:8].tolist()


# ---------------------------------------------------------------------------
# Bracket y eliminatorias
# ---------------------------------------------------------------------------


def _resolve_r32_bracket(
    group_standings: dict,
    thirds: list[str],
) -> list[tuple[str, str]]:
    """Traduce R32_TEMPLATE a pares de equipos reales.

    Slots '1X' / '2X' → 1er/2º clasificado del grupo X.
    Slots '3rd_k' → k-ésimo mejor tercero clasificado.
    """
    def get(group: str, pos: int) -> str:
        st = group_standings[group]
        return st.loc[st["group_pos"] == pos, "team"].iloc[0]

    def resolve(slot: str) -> str:
        if slot.startswith("3rd_"):
            k = int(slot.split("_")[1]) - 1  # 0-indexed
            return thirds[k]
        pos = int(slot[0])
        grp = slot[1]
        return get(grp, pos)

    return [(resolve(h), resolve(a)) for h, a in R32_TEMPLATE]


def _run_knockout_rounds(
    r32_bracket: list[tuple[str, str]],
    prob_cache: dict,
    rng: np.random.Generator,
) -> dict[str, str]:
    """Ejecuta todas las rondas eliminatorias a partir del bracket R32.

    Devuelve dict {equipo: ronda_alcanzada} para los 32 participantes.
    Las rondas siguen el orden de ROUNDS (de "round_of_32" a "champion").
    """
    round_stages = ["round_of_16", "quarter_final", "semi_final", "final", "champion"]
    team_round: dict[str, str] = {}

    current_bracket = r32_bracket
    for next_round in round_stages:
        uniforms = rng.random(len(current_bracket))
        winners = [
            _knockout_winner(h, a, prob_cache, u)
            for (h, a), u in zip(current_bracket, uniforms)
        ]

        # Equipos eliminados en esta ronda → su ronda máxima es la anterior
        current_round_name = ROUNDS[ROUNDS.index(next_round) - 1]
        for (home, away), winner in zip(current_bracket, winners):
            loser = away if winner == home else home
            team_round[loser] = current_round_name

        if next_round == "champion":
            # El campeón
            team_round[winners[0]] = "champion"
            break

        # Próxima ronda: parejas de ganadores adyacentes
        current_bracket = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]

    return team_round


# ---------------------------------------------------------------------------
# Simulación de un torneo completo
# ---------------------------------------------------------------------------


def simulate_tournament(
    groups_df: pd.DataFrame,
    predictions_df: pd.DataFrame,
    team_stats: dict,
    prob_cache: dict,
    rng: np.random.Generator,
) -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    """Simula un torneo completo de principio a fin.

    Devuelve (team_round, group_match_outcomes):
      - team_round: {equipo: ronda_alcanzada} para los 48 participantes
      - group_match_outcomes: {(home, away): outcome} para los 72 partidos de grupos
    """
    team_round: dict[str, str] = {t: "group_stage" for t in groups_df["team"]}

    group_probs: dict = {}
    for _, row in predictions_df.iterrows():
        group_probs[(row["home_team"], row["away_team"])] = (
            float(row["prob_H"]),
            float(row["prob_D"]),
            float(row["prob_A"]),
        )

    # ─── Fase de grupos ───────────────────────────────────────────────────────
    group_standings: dict = {}
    all_thirds: list = []
    group_match_outcomes: dict = {}

    for grp in GROUPS:
        teams = groups_df.loc[groups_df["group"] == grp, "team"].tolist()
        standings, outcomes = _simulate_group(grp, teams, group_probs, prob_cache, team_stats, rng)
        group_standings[grp] = standings
        group_match_outcomes.update(outcomes)

        third_row = standings.loc[standings["group_pos"] == 3].iloc[0]
        all_thirds.append({
            "team": third_row["team"],
            "pts": third_row["pts"],
            "gd": third_row["gd"],
            "gf": third_row["gf"],
        })

    # Clasificados: top 2 por grupo + 8 mejores terceros
    thirds = _best_thirds(all_thirds)
    advancing: set = set()

    for grp in GROUPS:
        st = group_standings[grp]
        for pos in (1, 2):
            team = st.loc[st["group_pos"] == pos, "team"].iloc[0]
            advancing.add(team)
            team_round[team] = "round_of_32"

    for team in thirds:
        advancing.add(team)
        team_round[team] = "round_of_32"

    # ─── Eliminatorias ────────────────────────────────────────────────────────
    r32_bracket = _resolve_r32_bracket(group_standings, thirds)
    ko_results = _run_knockout_rounds(r32_bracket, prob_cache, rng)
    team_round.update(ko_results)

    return team_round, group_match_outcomes


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------


def run_monte_carlo(
    n_simulations: int = 10_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Ejecuta N simulaciones del torneo completo.

    Devuelve DataFrame con columnas:
        team, group, confederation,
        qualify, round_of_16, quarter_final, semi_final, final, champion

    Cada columna de ronda = probabilidad (0-1) de alcanzar o superar esa ronda.
    """
    groups_df, predictions_df, features_df, model = load_data()
    team_stats = build_team_stats(features_df, groups_df)

    teams = groups_df["team"].tolist()
    prob_cache = build_prob_cache(teams, team_stats, model)

    rng = np.random.default_rng(seed)

    # Acumuladores
    counts: dict = {t: {r: 0 for r in ROUNDS} for t in teams}
    match_counts: dict = {}  # {(home, away): {H: 0, D: 0, A: 0}}

    for _ in range(n_simulations):
        result, match_outcomes = simulate_tournament(
            groups_df, predictions_df, team_stats, prob_cache, rng
        )
        for team, best_round in result.items():
            best_idx = ROUNDS.index(best_round)
            for r in ROUNDS[: best_idx + 1]:
                counts[team][r] += 1
        for (home, away), outcome in match_outcomes.items():
            if (home, away) not in match_counts:
                match_counts[(home, away)] = {"H": 0, "D": 0, "A": 0}
            match_counts[(home, away)][outcome] += 1

    # Construir DataFrame de salida
    # qualify = P(team_round >= "round_of_32") = counts["round_of_32"] / N
    rows = []
    for team in teams:
        row: dict = {
            "team": team,
            "group": groups_df.loc[groups_df["team"] == team, "group"].iloc[0],
            "confederation": groups_df.loc[groups_df["team"] == team, "confederation"].iloc[0],
            "qualify": counts[team]["round_of_32"] / n_simulations,
            "round_of_16": counts[team]["round_of_16"] / n_simulations,
            "quarter_final": counts[team]["quarter_final"] / n_simulations,
            "semi_final": counts[team]["semi_final"] / n_simulations,
            "final": counts[team]["final"] / n_simulations,
            "champion": counts[team]["champion"] / n_simulations,
        }
        rows.append(row)

    df = (
        pd.DataFrame(rows)
        .sort_values("champion", ascending=False)
        .reset_index(drop=True)
    )

    # ── CSV de resultados por partido de grupos ──────────────────────────────
    team_to_group = dict(zip(groups_df["team"], groups_df["group"]))
    match_rows = []
    for (home, away), c in match_counts.items():
        total = c["H"] + c["D"] + c["A"]
        match_rows.append({
            "home_team": home,
            "away_team": away,
            "group": team_to_group.get(home, ""),
            "sim_prob_home_win": round(c["H"] / total, 4),
            "sim_prob_draw":     round(c["D"] / total, 4),
            "sim_prob_away_win": round(c["A"] / total, 4),
        })
    match_df = (
        pd.DataFrame(match_rows)
        .sort_values(["group", "home_team"])
        .reset_index(drop=True)
    )
    match_df.to_csv(_REPORTS_DIR / "group_match_results.csv", index=False)

    return df


# ---------------------------------------------------------------------------
# Exportar resultados
# ---------------------------------------------------------------------------


def save_results(df: pd.DataFrame, path: Optional[Path] = None) -> Path:
    """Guarda el DataFrame de resultados como CSV."""
    if path is None:
        path = _REPORTS_DIR / "simulation_results.csv"
    df.to_csv(path, index=False)
    return path
