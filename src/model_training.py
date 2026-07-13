"""
model_training.py — Split temporal, baselines y entrenamiento del predictivo.

Validación espacio-temporal sin fuga: train = pasado, test = futuro.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

# Años de corte del protocolo anti-fuga
ANIO_TRAIN_MAX = 2024
ANIO_TEST = 2025
ANIO_VAL = 2024
ANIO_TUNE_TRAIN_MAX = 2023

RANDOM_STATE = 42


def temporal_split(
    df: pd.DataFrame,
    split_col: str = "split",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa train (pasado) y test (futuro) usando la columna `split`.
    """
    if split_col in df.columns:
        train = df[df[split_col] == "train"].copy()
        test = df[df[split_col] == "test"].copy()
    else:
        train = df[df["anio"] <= ANIO_TRAIN_MAX].copy()
        test = df[df["anio"] == ANIO_TEST].copy()

    if train.empty or test.empty:
        raise ValueError(
            "temporal_split produjo un conjunto vacío; "
            f"train={len(train)}, test={len(test)}"
        )
    if train["anio"].max() >= test["anio"].min():
        raise ValueError(
            "Fuga temporal detectada: max(train.anio) >= min(test.anio). "
            "No mezclar pasado y futuro."
        )
    return train, test


def temporal_tune_split(
    train_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Holdout temporal interno: fit ≤2023, validar 2024 (dentro de train)."""
    fit = train_df[train_df["anio"] <= ANIO_TUNE_TRAIN_MAX].copy()
    val = train_df[train_df["anio"] == ANIO_VAL].copy()
    if fit.empty or val.empty:
        raise ValueError(
            f"temporal_tune_split vacío: fit={len(fit)}, val={len(val)}"
        )
    return fit, val


def make_rf(
    n_estimators: int = 200,
    max_depth: int | None = 12,
    min_samples_leaf: int = 2,
    class_weight: str | dict | None = "balanced",
) -> RandomForestClassifier:
    """Random Forest con desbalance explícito (Issue #10 / #17)."""
    return RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        class_weight=class_weight,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def make_xgb(
    n_estimators: int = 200,
    max_depth: int = 4,
    learning_rate: float = 0.08,
    scale_pos_weight: float | None = None,
    y_train: np.ndarray | None = None,
):
    """XGBoost con scale_pos_weight equivalente a class_weight balanced."""
    from xgboost import XGBClassifier

    if scale_pos_weight is None:
        if y_train is None:
            scale_pos_weight = 1.0
        else:
            n_pos = max(int((y_train == 1).sum()), 1)
            n_neg = max(int((y_train == 0).sum()), 1)
            scale_pos_weight = n_neg / n_pos

    return XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        scale_pos_weight=scale_pos_weight,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def fit_pipeline(preprocessor: Any, estimator: Any, X: pd.DataFrame, y: np.ndarray) -> Pipeline:
    """Pipeline sklearn: preprocessor + estimador."""
    pipe = Pipeline([
        ("pre", preprocessor),
        ("clf", estimator),
    ])
    pipe.fit(X, y)
    return pipe
