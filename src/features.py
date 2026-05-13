"""
Feature engineering for Predicción Mundial 2026.

Each public function accepts the full matches DataFrame and returns it with
new columns appended. Always pass the FULL dataset (1872–2026) so that
rolling lookups covering pre-2010 history are correct; filter to the
training window only after calling build_features().
"""

from __future__ import annotations

from bisect import bisect_left

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Simple derived features (vectorised)
# ---------------------------------------------------------------------------


def add_elo_features(df: pd.DataFrame) -> pd.DataFrame:
    """Elo difference (positive = home team stronger, snapshot-based)."""
    df = df.copy()
    df["elo_diff"] = df["home_elo"] - df["away_elo"]
    return df


def add_fifa_rank_features(df: pd.DataFrame) -> pd.DataFrame:
    """FIFA rank difference (positive = home team is better ranked)."""
    df = df.copy()
    # Lower rank number = better team, so: away_rank - home_rank > 0 means home is better
    df["fifa_rank_diff"] = df["away_fifa_rank"] - df["home_fifa_rank"]
    return df


def add_confederation_features(df: pd.DataFrame) -> pd.DataFrame:
    """Flag when both teams belong to the same confederation."""
    df = df.copy()
    df["same_confederation"] = (
        df["home_confederation"] == df["away_confederation"]
    ).astype(int)
    return df


# ---------------------------------------------------------------------------
# Rolling form
# ---------------------------------------------------------------------------


def _build_team_match_history(df: pd.DataFrame) -> pd.DataFrame:
    """Flat (team, date, gf, ga, win, draw) from all matches with known results.

    result codes: 'H' = home win, 'A' = away win, 'D' = draw.
    """
    known = df[df["home_score"].notna()].copy()

    home = known[["date", "home_team", "home_score", "away_score", "result"]].copy()
    home.columns = ["date", "team", "gf", "ga", "result"]
    home["win"] = (home["result"] == "H").astype(int)
    home["draw"] = (home["result"] == "D").astype(int)

    away = known[["date", "away_team", "away_score", "home_score", "result"]].copy()
    away.columns = ["date", "team", "gf", "ga", "result"]
    away["win"] = (away["result"] == "A").astype(int)
    away["draw"] = (away["result"] == "D").astype(int)

    history = pd.concat([home, away], ignore_index=True)
    history["date"] = pd.to_datetime(history["date"])
    return history.sort_values(["team", "date"]).reset_index(drop=True)


def add_rolling_form(df: pd.DataFrame, windows: list[int] | None = None) -> pd.DataFrame:
    """
    Rolling form per team over the last N matches (shift-1, no leakage):
    mean goals scored/conceded and win/draw rate.
    Merged separately for home and away team.
    """
    if windows is None:
        windows = [5, 10]

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    history = _build_team_match_history(df)

    form_cols: list[str] = []
    for w in windows:
        for metric in ["gf", "ga", "win", "draw"]:
            col = f"{metric}_last{w}"
            history[col] = history.groupby("team")[metric].transform(
                lambda x, _w=w: x.shift(1).rolling(_w, min_periods=1).mean()
            )
            form_cols.append(col)

    # One row per (team, date); take last entry when same-day duplicates exist
    team_form = history.groupby(["team", "date"])[form_cols].last().reset_index()

    # Use merge_asof (nearest previous entry) so future matches (WC 2026) pick up the
    # team's most recent form even though they have no match on that exact date.
    orig_index = df.index
    df_sorted = df.sort_values("date")

    home_form = (
        team_form.rename(columns={"team": "home_team", **{c: f"home_{c}" for c in form_cols}})
        .sort_values("date")
    )
    away_form = (
        team_form.rename(columns={"team": "away_team", **{c: f"away_{c}" for c in form_cols}})
        .sort_values("date")
    )

    df_sorted = pd.merge_asof(
        df_sorted.sort_values(["date", "home_team"]),
        home_form,
        on="date", by="home_team", direction="backward",
    )
    df_sorted = pd.merge_asof(
        df_sorted.sort_values(["date", "away_team"]),
        away_form,
        on="date", by="away_team", direction="backward",
    )

    return df_sorted.loc[orig_index] if set(orig_index) == set(df_sorted.index) else df_sorted.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Head-to-head
# ---------------------------------------------------------------------------


def add_head_to_head(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    H2H win/draw/loss rates (from the home team's perspective) over the
    last N meetings before each match date.  Uses bisect for fast lookup.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # result codes: 'H' = home win, 'A' = away win, 'D' = draw
    known = df[df["home_score"].notna()][
        ["date", "home_team", "away_team", "result"]
    ].copy()

    # Canonical pair key (alphabetically sorted) → histories keyed by pair
    known["_pair"] = [
        tuple(sorted([h, a]))
        for h, a in zip(known["home_team"], known["away_team"])
    ]

    pair_dates: dict = {}
    pair_home_teams: dict = {}
    pair_results: dict = {}

    for pair_key, grp in known.groupby("_pair"):
        grp_s = grp.sort_values("date")
        pair_dates[pair_key] = grp_s["date"].tolist()
        pair_home_teams[pair_key] = grp_s["home_team"].tolist()
        pair_results[pair_key] = grp_s["result"].tolist()

    h2h_home_win, h2h_draw, h2h_away_win = [], [], []

    for _, row in df.iterrows():
        pair_key = tuple(sorted([row["home_team"], row["away_team"]]))
        dates = pair_dates.get(pair_key, [])

        if not dates:
            h2h_home_win.append(np.nan)
            h2h_draw.append(np.nan)
            h2h_away_win.append(np.nan)
            continue

        # Index of first entry >= current date (exclusive upper bound)
        idx = bisect_left(dates, row["date"])
        start = max(0, idx - n)
        past_home_teams = pair_home_teams[pair_key][start:idx]
        past_results = pair_results[pair_key][start:idx]

        if not past_results:
            h2h_home_win.append(np.nan)
            h2h_draw.append(np.nan)
            h2h_away_win.append(np.nan)
            continue

        total = len(past_results)
        home_team = row["home_team"]
        home_wins = sum(
            1
            for ht, r in zip(past_home_teams, past_results)
            if (ht == home_team and r == "H")
            or (ht != home_team and r == "A")
        )
        draws = sum(1 for r in past_results if r == "D")

        h2h_home_win.append(home_wins / total)
        h2h_draw.append(draws / total)
        h2h_away_win.append((total - home_wins - draws) / total)

    df["h2h_home_win_pct"] = h2h_home_win
    df["h2h_draw_pct"] = h2h_draw
    df["h2h_away_win_pct"] = h2h_away_win
    return df


# ---------------------------------------------------------------------------
# Rest days
# ---------------------------------------------------------------------------


def add_rest_days(df: pd.DataFrame) -> pd.DataFrame:
    """Days since each team's previous match (NaN for first recorded match)."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    home_app = df[["date", "home_team"]].rename(columns={"home_team": "team"})
    away_app = df[["date", "away_team"]].rename(columns={"away_team": "team"})

    appearances = (
        pd.concat([home_app, away_app])
        .drop_duplicates()
        .sort_values(["team", "date"])
        .reset_index(drop=True)
    )
    appearances["prev_date"] = appearances.groupby("team")["date"].shift(1)
    appearances["rest_days"] = (appearances["date"] - appearances["prev_date"]).dt.days

    home_rest = appearances.rename(
        columns={"team": "home_team", "rest_days": "home_rest_days"}
    )[["home_team", "date", "home_rest_days"]]
    away_rest = appearances.rename(
        columns={"team": "away_team", "rest_days": "away_rest_days"}
    )[["away_team", "date", "away_rest_days"]]

    df = df.merge(home_rest, on=["home_team", "date"], how="left")
    df = df.merge(away_rest, on=["away_team", "date"], how="left")
    return df


# ---------------------------------------------------------------------------
# World Cup history
# ---------------------------------------------------------------------------


def add_wc_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Number of distinct World Cup editions each team participated in
    *before* the current match year (WC experience proxy).
    """
    df = df.copy()

    wc = df[df["is_world_cup"] & df["home_score"].notna()].copy()

    wc_home = wc[["year", "home_team"]].rename(columns={"home_team": "team"})
    wc_away = wc[["year", "away_team"]].rename(columns={"away_team": "team"})
    wc_teams = pd.concat([wc_home, wc_away]).drop_duplicates()

    team_wc_years: dict[str, list[int]] = (
        wc_teams.groupby("team")["year"].apply(sorted).to_dict()
    )

    def _count_before(team: str, year: int) -> int:
        years = team_wc_years.get(team, [])
        return int(bisect_left(years, year))

    df["home_wc_appearances"] = [
        _count_before(t, y) for t, y in zip(df["home_team"], df["year"])
    ]
    df["away_wc_appearances"] = [
        _count_before(t, y) for t, y in zip(df["away_team"], df["year"])
    ]
    return df


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

#: Columns kept in the final feature files
FEATURE_COLS = [
    # identifiers
    "date", "home_team", "away_team", "tournament", "year",
    # match context
    "neutral", "is_friendly", "is_competitive", "is_world_cup",
    "home_confederation", "away_confederation", "same_confederation",
    # strength (snapshot)
    "home_elo", "away_elo", "elo_diff",
    "home_fifa_rank", "away_fifa_rank", "fifa_rank_diff",
    # rolling form — last 5 matches
    "home_gf_last5", "home_ga_last5", "home_win_last5", "home_draw_last5",
    "away_gf_last5", "away_ga_last5", "away_win_last5", "away_draw_last5",
    # rolling form — last 10 matches
    "home_gf_last10", "home_ga_last10", "home_win_last10", "home_draw_last10",
    "away_gf_last10", "away_ga_last10", "away_win_last10", "away_draw_last10",
    # head-to-head
    "h2h_home_win_pct", "h2h_draw_pct", "h2h_away_win_pct",
    # rest
    "home_rest_days", "away_rest_days",
    # WC experience
    "home_wc_appearances", "away_wc_appearances",
    # target
    "result",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all feature engineering steps and return the full enriched dataset.

    Adds an ``is_future`` boolean flag (True for WC 2026 rows with no score)
    so callers can split into training and prediction sets without needing the
    original home_score column.
    """
    df = df.copy()
    df["is_future"] = df["home_score"].isna()
    df = add_elo_features(df)
    df = add_fifa_rank_features(df)
    df = add_confederation_features(df)
    df = add_rolling_form(df, windows=[5, 10])
    df = add_head_to_head(df, n=10)
    df = add_rest_days(df)
    df = add_wc_history(df)
    return df
