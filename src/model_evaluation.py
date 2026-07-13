"""
model_evaluation.py — Métricas alineadas al objetivo (recall/F1 clase riesgo alto).

"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)


def metricas_riesgo(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    y_proba: np.ndarray | None = None,
    umbral: float = 0.5,
) -> dict[str, Any]:
    """Recall, F1 y precisión de la clase riesgo alto (pos_label=1)."""
    y_true = np.asarray(y_true).astype(int)
    if y_proba is not None and y_pred is None:
        y_pred = (np.asarray(y_proba) >= umbral).astype(int)
    y_pred = np.asarray(y_pred).astype(int)

    return {
        "recall_riesgo": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "precision_riesgo": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1_riesgo": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "matriz_confusion": confusion_matrix(y_true, y_pred).tolist(),
        "n": int(len(y_true)),
        "n_positivos": int((y_true == 1).sum()),
        "umbral": umbral,
    }


def tabla_comparativa(filas: list[dict[str, Any]]) -> pd.DataFrame:
    """Tabla baseline vs RF vs XGBoost (Issue #18)."""
    return pd.DataFrame(filas)[
        [c for c in ("modelo", "conjunto", "recall_riesgo", "precision_riesgo", "f1_riesgo", "n_positivos", "n")
         if any(c in f for f in filas) or c in filas[0]]
    ]


def reporte_texto(y_true, y_pred) -> str:
    return classification_report(
        y_true, y_pred, target_names=["riesgo_bajo", "riesgo_alto"], zero_division=0
    )


def mejor_umbral_f1(y_true, y_proba) -> tuple[float, float]:
    """Elige umbral que maximiza F1 de la clase positiva sobre un holdout temporal."""
    y_true = np.asarray(y_true).astype(int)
    y_proba = np.asarray(y_proba)
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    if len(thresholds) == 0:
        return 0.5, 0.0
    f1s = (2 * precision[:-1] * recall[:-1]) / np.clip(precision[:-1] + recall[:-1], 1e-12, None)
    idx = int(np.nanargmax(f1s))
    return float(thresholds[idx]), float(f1s[idx])
