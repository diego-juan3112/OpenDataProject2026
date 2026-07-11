"""Tests para la validacion interna del clustering (Issue #28).

Usan matrices/etiquetas sinteticas (no el parquet real): data/ y
models/clustering/*.parquet no existen en CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
from sklearn.cluster import KMeans

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "models" / "clustering"))

from clustering import silhouette_por_cluster


def _features_2_grupos_separados() -> pd.DataFrame:
    """8 zonas en 2 grupos muy separados (2 features): A1-A4 cerca de (0,0),
    B1-B4 cerca de (10,10). Separacion clara -> silhouette alto esperado.
    """
    filas = {
        "A1": {"x": 0.0, "y": 0.0},
        "A2": {"x": 0.1, "y": -0.1},
        "A3": {"x": -0.1, "y": 0.1},
        "A4": {"x": 0.05, "y": 0.05},
        "B1": {"x": 10.0, "y": 10.0},
        "B2": {"x": 10.1, "y": 9.9},
        "B3": {"x": 9.9, "y": 10.1},
        "B4": {"x": 10.05, "y": 10.05},
    }
    df = pd.DataFrame(filas).T
    df.index.name = "cod_localidad"
    return df


def test_silhouette_por_cluster_ambos_grupos_cohesivos():
    features = _features_2_grupos_separados()
    modelo = KMeans(n_clusters=2, n_init=10, random_state=42).fit(features.values)

    resumen = silhouette_por_cluster(features, modelo)

    assert list(resumen.columns) == ["cluster", "n", "silhouette_medio", "silhouette_min"]
    assert resumen["n"].tolist() == [4, 4]
    assert (resumen["silhouette_medio"] > 0.9).all()
    assert resumen["silhouette_medio"].iloc[0] == pytest.approx(0.9888, abs=0.001)
    assert resumen["silhouette_min"].iloc[0] == pytest.approx(0.9863, abs=0.001)
