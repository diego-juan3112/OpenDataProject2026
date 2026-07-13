"""
predict.py — Inferencia del modelo predictivo.

Contrato de entrada (por fila o DataFrame):
  cod_localidad, anio, tipo_delito, conteo_nuse, poblacion, ipm_nbi
  + historial opcional en un DataFrame más amplio para calcular lags
    (si solo se pasa un año, los lags quedan en 0 salvo que se provea
    el dataset analítico completo).

Contrato de salida:
  probabilidad de riesgo alto, predicho (0/1) según umbral del artefacto.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import features as feat

MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"


def load_model(path: Path = MODEL_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"No está {path}. Ejecuta primero: python models/predictivo/train.py"
        )
    return joblib.load(path)


def _prepare(df: pd.DataFrame, mediana_ipm: float) -> pd.DataFrame:
    prepared, _ = feat.build_feature_frame(df, mediana_ipm=mediana_ipm)
    return prepared


def predict(
    df: pd.DataFrame,
    artifact: dict[str, Any] | None = None,
    model_path: Path = MODEL_PATH,
) -> pd.DataFrame:
    """Devuelve df con columnas probabilidad_riesgo y riesgo_predicho."""
    artifact = artifact or load_model(model_path)
    pipe = artifact["pipeline"]
    umbral = float(artifact.get("umbral", 0.5))
    mediana = float(artifact["meta"]["mediana_ipm_train"])

    prepared = _prepare(df, mediana)
    X = prepared[feat.NUMERIC_FEATURES + feat.CATEGORICAL_FEATURES]
    proba = pipe.predict_proba(X)[:, 1]
    pred = (proba >= umbral).astype(int)

    out = prepared[
        ["cod_localidad", "anio", "tipo_delito"]
        + (["localidad_nombre"] if "localidad_nombre" in prepared.columns else [])
        + (["tipo_delito_nombre"] if "tipo_delito_nombre" in prepared.columns else [])
    ].copy()
    out["probabilidad_riesgo"] = proba
    out["riesgo_predicho"] = pred
    out["umbral"] = umbral
    return out


def predict_zona_anio_tipo(
    cod_localidad: str,
    anio: int,
    tipo_delito: str,
    dataset: pd.DataFrame | None = None,
    artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inferencia de una celda (localidad × año × tipo) usando el dataset para lags."""
    dataset = dataset if dataset is not None else pd.read_parquet(config.DATASET_ANALITICO)
    # Asegurar que la fila consultada existe; si no, error claro.
    mask = (
        (dataset["cod_localidad"] == str(cod_localidad).zfill(2))
        & (dataset["anio"] == int(anio))
        & (dataset["tipo_delito"] == tipo_delito)
    )
    if not mask.any():
        raise KeyError(
            f"No hay fila para localidad={cod_localidad}, anio={anio}, tipo={tipo_delito}"
        )
    result = predict(dataset, artifact=artifact)
    row = result.loc[mask].iloc[0]
    return {
        "cod_localidad": row["cod_localidad"],
        "anio": int(row["anio"]),
        "tipo_delito": row["tipo_delito"],
        "probabilidad_riesgo": float(row["probabilidad_riesgo"]),
        "riesgo_predicho": int(row["riesgo_predicho"]),
        "umbral": float(row["umbral"]),
        "nivel_riesgo": "alto" if int(row["riesgo_predicho"]) == 1 else "bajo",
    }


if __name__ == "__main__":
    art = load_model()
    df = pd.read_parquet(config.DATASET_ANALITICO)
    ejemplo = predict_zona_anio_tipo("01", 2025, "HP", dataset=df, artifact=art)
    print("Ejemplo inferencia Usaquén / 2025 / Hurto Personas:")
    print(ejemplo)
    # Smoke test: todas las filas test
    test = df[df["split"] == "test"]
    out = predict(df, artifact=art)
    out_test = out.loc[test.index]
    print(f"\nPredicciones test: {len(out_test)} filas, "
          f"% riesgo alto predicho={out_test['riesgo_predicho'].mean():.1%}")
