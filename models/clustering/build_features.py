"""
build_features.py — Issue #26

Orquestador: features de perfil de zona (estandarizadas) + linea base
historica z-score, a partir de data/03_primary/dataset_analitico.parquet.
Escribe los dos entregables que desbloquean #27 (K-Means) y #36 (flag z-score).

Uso:
    python models/clustering/build_features.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
import config
import feature_engineering

OUT_DIR = Path(__file__).resolve().parent
FEATURES_PATH = OUT_DIR / "features_zona.parquet"
LINEA_BASE_PATH = OUT_DIR / "linea_base_zscore.parquet"


def run() -> None:
    print("== #26 Features de perfil de zona + linea base z-score ==")
    df = pd.read_parquet(config.DATASET_ANALITICO)

    features = feature_engineering.construir_features_zona(df)
    features.to_parquet(FEATURES_PATH)

    linea_base = feature_engineering.calcular_linea_base(df)
    linea_base.to_parquet(LINEA_BASE_PATH, index=False)

    _verificar(features, linea_base)


def _verificar(features: pd.DataFrame, linea_base: pd.DataFrame) -> None:
    print(f"  features_zona: {features.shape[0]} localidades x {features.shape[1]} columnas")
    assert features.shape == (20, 13), "forma inesperada de la matriz de features"
    print(f"  media por columna (desviacion max respecto a 0): {features.mean().abs().max():.2e}")
    print(f"  std por columna (debe ser 1.0): {features.std(ddof=0).round(3).to_dict()}")

    print(f"  linea_base: {linea_base.shape[0]} filas (esperado 220 = 20 localidades x 11 tipos)")
    assert linea_base.shape[0] == 220, "conteo de filas inesperado en la linea base"
    ceros = linea_base[linea_base["desviacion"] == 0]
    print(f"  filas con desviacion == 0 (revisar en #36 antes de dividir): {len(ceros)}")
    if len(ceros):
        print(ceros.to_string(index=False))

    print(f"\n  [ok] {FEATURES_PATH}")
    print(f"  [ok] {LINEA_BASE_PATH}")


if __name__ == "__main__":
    run()
