"""
Modelado para Predicción Mundial 2026.

Expone:
  - FEATURE_COLS_MODEL : lista canónica de columnas que entran al modelo
  - LABEL_MAP / LABEL_MAP_INV : codificación del target (H=0, A=1, D=2)
  - make_pipeline(model_name) : devuelve un sklearn Pipeline listo para fit
  - evaluate(pipeline, X, y) : dict con log-loss, Brier, accuracy
  - feature_importance(pipeline, feature_names) : DataFrame ordenado
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OrdinalEncoder, LabelEncoder
from sklearn.metrics import log_loss, accuracy_score

# ---------------------------------------------------------------------------
# Feature columns (sin identifiers ni target)
# ---------------------------------------------------------------------------

CATEGORICAL_COLS = ["home_confederation", "away_confederation"]

NUMERIC_COLS = [
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

FEATURE_COLS_MODEL = NUMERIC_COLS + CATEGORICAL_COLS

# ---------------------------------------------------------------------------
# Target encoding
# ---------------------------------------------------------------------------

LABEL_MAP = {"H": 0, "A": 1, "D": 2}
LABEL_MAP_INV = {v: k for k, v in LABEL_MAP.items()}
CLASSES = ["H", "A", "D"]


def encode_target(y: pd.Series) -> np.ndarray:
    return y.map(LABEL_MAP).values


# ---------------------------------------------------------------------------
# Preprocessor
# ---------------------------------------------------------------------------

def _build_preprocessor() -> ColumnTransformer:
    """
    Imputation strategy:
    - Numeric: median (robust to outliers; elo/fifa/h2h nulos representan
      equipos desconocidos o primer enfrentamiento, la mediana es mejor proxy
      que 0 para rest_days y form; para elo_diff/fifa_rank_diff usamos 0
      explícitamente via fill_value=0 en columnas seleccionadas).
    - Categorical: constante 'Unknown' antes de OrdinalEncoder.

    Nota: elo_diff y fifa_rank_diff se imputan a 0 (= fuerza equivalente).
    El resto de numéricos usan la mediana.
    """
    zero_impute_cols = ["elo_diff", "fifa_rank_diff", "home_elo", "away_elo",
                        "home_fifa_rank", "away_fifa_rank"]
    median_cols = [c for c in NUMERIC_COLS if c not in zero_impute_cols]

    return ColumnTransformer(
        transformers=[
            ("zero_imp", SimpleImputer(strategy="constant", fill_value=0), zero_impute_cols),
            ("median_imp", SimpleImputer(strategy="median"), median_cols),
            ("cat", Pipeline([
                ("imp", SimpleImputer(strategy="constant", fill_value="Unknown")),
                ("enc", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
            ]), CATEGORICAL_COLS),
        ],
        remainder="drop",
    )


# ---------------------------------------------------------------------------
# Pipeline factory
# ---------------------------------------------------------------------------

def make_pipeline(model_name: str, calibrate: bool = False, **model_kwargs) -> Pipeline:
    """
    Crea un Pipeline completo: preprocesador + modelo.

    Args:
        model_name: 'logistic', 'random_forest' o 'xgboost'
        calibrate: si True, envuelve el modelo con CalibratedClassifierCV isotonic
        **model_kwargs: parámetros extra para el estimador

    Returns:
        sklearn Pipeline listo para .fit(X, y)
    """
    preprocessor = _build_preprocessor()

    if model_name == "logistic":
        clf = LogisticRegression(
            max_iter=1000,
            C=model_kwargs.get("C", 1.0),
            random_state=42,
        )
    elif model_name == "random_forest":
        clf = RandomForestClassifier(
            n_estimators=model_kwargs.get("n_estimators", 400),
            max_depth=model_kwargs.get("max_depth", 8),
            min_samples_leaf=model_kwargs.get("min_samples_leaf", 20),
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
    elif model_name == "gradient_boosting":
        clf = HistGradientBoostingClassifier(
            max_iter=model_kwargs.get("max_iter", 400),
            max_depth=model_kwargs.get("max_depth", 4),
            learning_rate=model_kwargs.get("learning_rate", 0.05),
            min_samples_leaf=model_kwargs.get("min_samples_leaf", 20),
            random_state=42,
        )
    else:
        raise ValueError(f"model_name desconocido: {model_name!r}. Opciones: 'logistic', 'random_forest', 'gradient_boosting'")

    if calibrate:
        clf = CalibratedClassifierCV(clf, method="isotonic", cv=5)

    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", clf),
    ])


# ---------------------------------------------------------------------------
# Evaluación
# ---------------------------------------------------------------------------

def evaluate(pipeline: Pipeline, X: pd.DataFrame, y_true_labels: np.ndarray) -> dict:
    """
    Evalúa un pipeline ya entrenado.

    Args:
        pipeline: Pipeline ajustado
        X: features (columnas = FEATURE_COLS_MODEL)
        y_true_labels: array de enteros (encode_target ya aplicado)

    Returns:
        dict con 'log_loss', 'brier', 'accuracy'
    """
    proba = pipeline.predict_proba(X)
    preds = np.argmax(proba, axis=1)

    ll = log_loss(y_true_labels, proba, labels=[0, 1, 2])
    acc = accuracy_score(y_true_labels, preds)

    # Brier multiclase: media de Brier por clase
    n = len(y_true_labels)
    brier = 0.0
    for k in range(3):
        y_k = (y_true_labels == k).astype(float)
        brier += np.mean((proba[:, k] - y_k) ** 2)
    brier /= 3.0

    return {"log_loss": round(ll, 4), "brier": round(brier, 4), "accuracy": round(acc, 4)}


# ---------------------------------------------------------------------------
# Feature importance
# ---------------------------------------------------------------------------

def feature_importance(
    pipeline: Pipeline,
    X: pd.DataFrame | None = None,
    y: np.ndarray | None = None,
    n_repeats: int = 10,
) -> pd.DataFrame:
    """
    Extrae importancia de features del pipeline.

    - RandomForest: feature_importances_ (MDI)
    - LogisticRegression: |coef| medio entre clases
    - HistGradientBoosting u otros: permutation importance (requiere X, y)

    Devuelve DataFrame con columnas ['feature', 'importance'], ordenado desc.
    """
    from sklearn.inspection import permutation_importance as _perm_imp

    zero_cols = ["elo_diff", "fifa_rank_diff", "home_elo", "away_elo",
                 "home_fifa_rank", "away_fifa_rank"]
    median_cols = [c for c in NUMERIC_COLS if c not in zero_cols]
    names = zero_cols + median_cols + CATEGORICAL_COLS

    clf = pipeline.named_steps["classifier"]
    if hasattr(clf, "estimator"):
        clf = clf.estimator

    if hasattr(clf, "feature_importances_"):
        importances = clf.feature_importances_
    elif hasattr(clf, "coef_"):
        importances = np.abs(clf.coef_).mean(axis=0)
    else:
        # Permutation importance — necesita X e y
        if X is None or y is None:
            raise ValueError(
                "Este modelo no tiene feature_importances_. "
                "Pasa X e y para usar permutation importance."
            )
        result = _perm_imp(pipeline, X, y, n_repeats=n_repeats,
                           random_state=42, scoring="neg_log_loss")
        importances = result.importances_mean

    return (
        pd.DataFrame({"feature": names, "importance": importances})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
