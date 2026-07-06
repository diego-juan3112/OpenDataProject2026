"""
feature_engineering.py — Creación de variables y codificación.

Por ahora expone la construcción de la **variable objetivo** del predictivo
(Issue #10): `riesgo_alto`, etiquetada por percentil dentro de cada tipo de
delito. Los lags temporales, tasas por 100k y codificaciones adicionales que
consumen Integrante 2 (predictivo) e Integrante 3 (clustering) se construyen
sobre esta base a partir de `data/03_primary/dataset_analitico.parquet`.
"""

from __future__ import annotations

import pandas as pd

# Percentil por defecto para el umbral de "riesgo alto" (Issue #10, acordado
# con Integrante 2). P75 dentro de cada tipo de delito → ~25% de clase positiva.
PERCENTIL_RIESGO_ALTO = 0.75


def umbrales_riesgo(
    df: pd.DataFrame,
    percentil: float = PERCENTIL_RIESGO_ALTO,
    split_col: str = "split",
    train_value: str = "train",
) -> pd.Series:
    """Umbral de conteo por tipo de delito, calculado SOLO con filas de train.

    El umbral se aprende del histórico de entrenamiento (años ≤2024) para no
    filtrar información de test. Devuelve una serie indexada por `tipo_delito`.
    """
    train = df[df[split_col] == train_value]
    return train.groupby("tipo_delito")["conteo_siedco"].quantile(percentil)


def add_target_riesgo_alto(
    df: pd.DataFrame,
    percentil: float = PERCENTIL_RIESGO_ALTO,
    split_col: str = "split",
    train_value: str = "train",
) -> tuple[pd.DataFrame, pd.Series]:
    """Añade la columna binaria `riesgo_alto` (0/1) al dataset analítico.

    Una fila (localidad × año × tipo_delito) es `riesgo_alto = 1` si su
    `conteo_siedco` **supera** (estrictamente) el percentil `percentil` del
    **mismo tipo de delito** en el histórico de entrenamiento. Los umbrales se
    aprenden solo de train y se aplican también a las filas test (para la
    evaluación de Integrante 2, Issue #17) sin fuga de información: test nunca
    interviene en el cálculo del umbral.

    Devuelve (df con la columna añadida, serie de umbrales por tipo de delito).
    """
    umbrales = umbrales_riesgo(df, percentil, split_col, train_value)
    df = df.copy()
    df["riesgo_alto"] = (
        df["conteo_siedco"] > df["tipo_delito"].map(umbrales)
    ).astype(int)
    return df, umbrales


if __name__ == "__main__":
    import config

    _df = pd.read_parquet(config.DATASET_ANALITICO)
    _df, _u = add_target_riesgo_alto(_df)
    _tr = _df[_df["split"] == "train"]
    print("Umbrales P75 por tipo de delito (train):")
    print(_u.round(1).to_string())
    print("\nDistribución riesgo_alto (train):")
    print(_tr["riesgo_alto"].value_counts(normalize=True).round(3).to_string())
