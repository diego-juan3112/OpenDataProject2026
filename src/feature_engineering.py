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


def construir_features_zona(
    df: pd.DataFrame,
    split_col: str = "split",
    train_value: str = "train",
) -> pd.DataFrame:
    """Matriz localidad x features estandarizada para el clustering (Issue #26).

    Usa SOLO `split == train_value` (sin fuga): tasa anual promedio por 100.000
    habitantes por tipo de delito, tasa de llamadas NUSE por 100.000 hab., y
    contexto socioeconomico (`ipm_nbi`). Sumapaz (unica localidad con `ipm_nbi`
    nulo) se imputa con la mediana de las demas localidades -- imputacion
    documentada, no en silencio; ver `docs/data-dictionaries/features_clustering.md`.
    La decision final de como tratar a Sumapaz en el clustering (incluir con
    este valor imputado, excluir, o cluster propio) queda para la Issue #27.

    Devuelve la matriz ya estandarizada (z-score, ddof=0, media 0 / desviacion 1
    por columna), indexada por `cod_localidad`, lista para `KMeans.fit(...)`.
    """
    train = df[df[split_col] == train_value].copy()

    train["tasa_anual"] = train["conteo_siedco"] / train["poblacion"] * 100000
    tasa_tipo = train.pivot_table(index="cod_localidad", columns="tipo_delito",
                                   values="tasa_anual", aggfunc="mean")
    tasa_tipo.columns = [f"tasa_{c}" for c in tasa_tipo.columns]

    # conteo_nuse/poblacion vienen repetidos por tipo dentro de una misma
    # localidad-anio (es una senal de zona-anio, no de zona-tipo); se deduplica
    # antes de promediar para no contar el mismo anio 11 veces.
    nuse = (train.drop_duplicates(subset=["cod_localidad", "anio"])
                 .assign(tasa_nuse_anual=lambda d: d["conteo_nuse"] / d["poblacion"] * 100000)
                 .groupby("cod_localidad")["tasa_nuse_anual"].mean()
                 .rename("tasa_nuse"))

    ipm = (train.drop_duplicates(subset=["cod_localidad"])
                .set_index("cod_localidad")["ipm_nbi"])
    ipm = ipm.fillna(ipm.median())

    features = tasa_tipo.join(nuse).join(ipm.rename("ipm_nbi"))
    return (features - features.mean()) / features.std(ddof=0)


def calcular_linea_base(
    df: pd.DataFrame,
    split_col: str = "split",
    train_value: str = "train",
) -> pd.DataFrame:
    """Linea base historica (media/desviacion) por localidad-tipo (Issue #26).

    Usa SOLO `split == train_value` (sin fuga). Media y desviacion estandar
    muestral (`ddof=1`) de `conteo_siedco` sobre los anios de entrenamiento,
    por (`cod_localidad`, `tipo_delito`). Es el insumo directo de `flag_zscore`
    (Issue #36): dado un conteo reciente para una localidad-tipo, #36 calculara
    `z = (conteo_reciente - media) / desviacion`. Esta funcion NO calcula ese
    z-score, solo produce la linea base contra la que se comparara.

    Algunas combinaciones (p. ej. Sumapaz en tipos de conteo casi nulo) pueden
    tener `desviacion == 0` si los 7 conteos anuales son identicos -- no se
    corrige aqui; documentado para que #36 evite dividir por cero.
    """
    train = df[df[split_col] == train_value]
    return (train.groupby(["cod_localidad", "tipo_delito"])["conteo_siedco"]
                 .agg(media="mean", desviacion=lambda s: s.std(ddof=1))
                 .reset_index())


if __name__ == "__main__":
    import config

    _df = pd.read_parquet(config.DATASET_ANALITICO)
    _df, _u = add_target_riesgo_alto(_df)
    _tr = _df[_df["split"] == "train"]
    print("Umbrales P75 por tipo de delito (train):")
    print(_u.round(1).to_string())
    print("\nDistribución riesgo_alto (train):")
    print(_tr["riesgo_alto"].value_counts(normalize=True).round(3).to_string())
