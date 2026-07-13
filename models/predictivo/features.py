"""
features.py — Feature engineering del modelo predictivo.

IMPORTANTE — anti-fuga de etiqueta:
  `riesgo_alto` se define como conteo_siedco > P75 del mismo tipo.
  Por tanto **NO** usamos `conteo_siedco` del mismo año como feature
  (sería aprender el umbral, no predecir riesgo).

Features:
  - Temporales: anio
  - Contexto: poblacion, ipm_nbi (Sumapaz imputado con mediana de train), tasa_nuse_100k
  - Rezagos históricos (solo pasado): lag_1/2/3 de conteo_siedco y media móvil 3 años
  - Categóricas: cod_localidad, tipo_delito (OneHot)

El preprocessor sklearn se ajusta SOLO con train.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Matriz de features documentada.
FEATURE_SPEC: list[dict[str, str]] = [
    {"nombre": "anio", "tipo": "numérica", "fuente": "SIEDCO (grano temporal)"},
    {"nombre": "poblacion", "tipo": "numérica", "fuente": "DANE / SDP"},
    {"nombre": "ipm_nbi", "tipo": "numérica", "fuente": "DANE IPM (Sumapaz: mediana train)"},
    {"nombre": "tasa_nuse_100k", "tipo": "numérica", "fuente": "NUSE / población × 100k"},
    {"nombre": "lag_1", "tipo": "numérica", "fuente": "conteo_siedco año-1 misma localidad-tipo"},
    {"nombre": "lag_2", "tipo": "numérica", "fuente": "conteo_siedco año-2"},
    {"nombre": "lag_3", "tipo": "numérica", "fuente": "conteo_siedco año-3"},
    {"nombre": "roll_mean_3", "tipo": "numérica", "fuente": "media de lags 1–3"},
    {"nombre": "cod_localidad", "tipo": "categórica", "fuente": "DIVIPOLA Bogotá"},
    {"nombre": "tipo_delito", "tipo": "categórica", "fuente": "taxonomía SIEDCO"},
]

NUMERIC_FEATURES = [
    "anio", "poblacion", "ipm_nbi", "tasa_nuse_100k",
    "lag_1", "lag_2", "lag_3", "roll_mean_3",
]
CATEGORICAL_FEATURES = ["cod_localidad", "tipo_delito"]
TARGET = "riesgo_alto"


def _lags_sin_fuga(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula lags por (localidad, tipo) ordenados por año — solo información pasada."""
    out = df.sort_values(["cod_localidad", "tipo_delito", "anio"]).copy()
    g = out.groupby(["cod_localidad", "tipo_delito"], sort=False)["conteo_siedco"]
    out["lag_1"] = g.shift(1)
    out["lag_2"] = g.shift(2)
    out["lag_3"] = g.shift(3)
    out["roll_mean_3"] = out[["lag_1", "lag_2", "lag_3"]].mean(axis=1)
    return out


def imputar_ipm_nbi(df: pd.DataFrame, mediana_train: float | None = None) -> tuple[pd.DataFrame, float]:
    """Imputa ipm_nbi de Sumapaz con la mediana de localidades con valor (decisión Int. 2).

    Si `mediana_train` se pasa, se reutiliza (para test/inferencia sin reaprender).
    """
    out = df.copy()
    if mediana_train is None:
        mediana_train = float(out["ipm_nbi"].median(skipna=True))
    out["ipm_nbi"] = out["ipm_nbi"].fillna(mediana_train)
    return out, mediana_train


def build_feature_frame(df: pd.DataFrame, mediana_ipm: float | None = None) -> tuple[pd.DataFrame, float]:
    """Añade lags + tasa NUSE + imputación IPM. No elimina filas."""
    out = _lags_sin_fuga(df)
    out, mediana_ipm = imputar_ipm_nbi(out, mediana_ipm)
    out["tasa_nuse_100k"] = out["conteo_nuse"] / out["poblacion"].clip(lower=1) * 100_000
    # Primeros años sin historial: lag NaN → 0 (sin delito observado previo).
    for col in ("lag_1", "lag_2", "lag_3", "roll_mean_3"):
        out[col] = out[col].fillna(0.0)
    return out, mediana_ipm


def make_preprocessor() -> ColumnTransformer:
    """ColumnTransformer + imputación residual + OneHot + escala numérica."""
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer(
        transformers=[
            ("num", numeric, NUMERIC_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def xy_from_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    y = df[TARGET].astype(int).to_numpy()
    return X, y


def feature_spec_markdown() -> str:
    lines = ["| nombre | tipo | fuente |", "|---|---|---|"]
    for row in FEATURE_SPEC:
        lines.append(f"| `{row['nombre']}` | {row['tipo']} | {row['fuente']} |")
    lines.append("")
    lines.append(
        "**Excluido a propósito:** `conteo_siedco` del mismo año — es la variable "
        "de la que se deriva `riesgo_alto` (fuga de etiqueta)."
    )
    return "\n".join(lines)


def pack_artifact_meta(mediana_ipm: float, feature_names: list[str] | None = None) -> dict[str, Any]:
    return {
        "mediana_ipm_train": mediana_ipm,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "feature_spec": FEATURE_SPEC,
        "feature_names_out": feature_names,
        "nota_anti_fuga": "No se usa conteo_siedco del mismo año como feature.",
    }
