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


# --------------------------------------------------------------------------- #
# Score de riesgo por localidad — feature Ruta Más Segura (Issue #46)
# --------------------------------------------------------------------------- #
# Pesos por gravedad relativa del tipo de delito (del diseño técnico,
# `diseño_tecnico_ruta_segura.md` §PARTE 3, Paso 1). NO cambiar sin justificar
# y documentar: son defendibles ante el jurado (homicidio pesa 10× una bici).
PESOS_TIPO_DELITO = {
    "H":   10,   # Homicidios
    "DS":   8,   # Delitos Sexuales
    "LP":   7,   # Lesiones Personales
    "HP":   5,   # Hurto Personas
    "VI":   5,   # Violencia Intrafamiliar
    "HR":   4,   # Hurto Residencias
    "HC":   3,   # Hurto Comercio
    "HCE":  3,   # Hurto Celulares
    "HA":   3,   # Hurto Automotores
    "HM":   2,   # Hurto Motocicletas
    "HB":   1,   # Hurto Bicicletas
}


def calcular_scores_localidad(dataset_path: str) -> dict[str, float]:
    """Score de riesgo 0–10 por localidad para el routing de Ruta Más Segura.

    Lee el dataset analítico y devuelve un score de riesgo 0–10 por localidad,
    usando datos de 2024 (último año de entrenamiento). El score es la suma
    ponderada de `conteo_siedco` por tipo de delito (pesos de
    `PESOS_TIPO_DELITO`), normalizada al rango 0–10 con min-max. Solo usa filas
    `split == "train"`; nunca test.

    Devuelve: dict {cod_localidad: score} con exactamente 20 claves.
    Ejemplo: {"01": 3.2, "08": 8.7, "11": 7.4, ...}

    Nota: el score usa conteo absoluto (no por 100k habitantes).
    Localidades densamente pobladas como Suba/Kennedy pueden aparecer
    con score alto por volumen, no por tasa. Mejora futura: normalizar
    por población antes de aplicar pesos.
    """
    df = pd.read_parquet(dataset_path)
    df_2024 = df[(df["anio"] == 2024) & (df["split"] == "train")].copy()

    df_2024["conteo_ponderado"] = (
        df_2024["conteo_siedco"] * df_2024["tipo_delito"].map(PESOS_TIPO_DELITO).fillna(1)
    )

    scores_raw = df_2024.groupby("cod_localidad")["conteo_ponderado"].sum()
    rango = scores_raw.max() - scores_raw.min()
    if rango == 0:  # todos iguales (no debería ocurrir con 20 localidades reales)
        scores_norm = scores_raw * 0.0
    else:
        scores_norm = (scores_raw - scores_raw.min()) / rango * 10

    return scores_norm.round(2).to_dict()
