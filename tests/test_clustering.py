"""Tests para el clustering K-Means de perfiles de zona (Issue #27).

Usan una matriz de features sintetica (no el parquet real): data/ y
models/clustering/features_zona.parquet no existen en CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "models" / "clustering"))

from clustering import evaluar_k, entrenar_kmeans_final, nombrar_clusters, construir_zona_cluster

COLS_VIOLENTO = ["tasa_H", "tasa_DS", "tasa_VI", "tasa_LP"]
COLS_PATRIMONIAL = ["tasa_HA", "tasa_HB", "tasa_HC", "tasa_HCE", "tasa_HM", "tasa_HR", "tasa_HP"]
COLS_TIPO_DELITO = ["tasa_DS", "tasa_H", "tasa_HA", "tasa_HB", "tasa_HC", "tasa_HCE",
                     "tasa_HM", "tasa_HP", "tasa_HR", "tasa_LP", "tasa_VI"]
TODAS_COLS = COLS_TIPO_DELITO + ["tasa_nuse", "ipm_nbi"]


def _features_sinteticas() -> pd.DataFrame:
    """6 zonas sinteticas en 3 pares claramente separables (ya estandarizadas):
    Z1/Z2 = alto impacto en todo; Z3/Z4 = alto solo en patrimonial (bajo en
    violento, ipm bajo); Z5/Z6 = bajo en todo.
    """
    filas = {
        "Z1": {c: 2.0 for c in TODAS_COLS},
        "Z2": {c: 2.1 for c in TODAS_COLS},
        "Z3": {**{c: 1.5 for c in COLS_PATRIMONIAL}, **{c: -0.5 for c in COLS_VIOLENTO},
               "tasa_nuse": 0.5, "ipm_nbi": -1.0},
        "Z4": {**{c: 1.6 for c in COLS_PATRIMONIAL}, **{c: -0.4 for c in COLS_VIOLENTO},
               "tasa_nuse": 0.4, "ipm_nbi": -0.9},
        "Z5": {c: -0.8 for c in TODAS_COLS},
        "Z6": {c: -0.7 for c in TODAS_COLS},
    }
    synth = pd.DataFrame(filas).T
    synth.index.name = "cod_localidad"
    return synth[TODAS_COLS]


def test_evaluar_k_detecta_la_separacion_clara_en_k3():
    features = _features_sinteticas()
    tabla = evaluar_k(features, range(2, 5))

    assert list(tabla["k"]) == [2, 3, 4]
    fila_k3 = tabla[tabla["k"] == 3].iloc[0]
    assert fila_k3["silhouette"] == pytest.approx(0.9416, abs=0.01)
    assert fila_k3["silhouette"] == tabla["silhouette"].max()


def test_entrenar_kmeans_final_agrupa_los_3_pares_correctamente():
    features = _features_sinteticas()
    modelo = entrenar_kmeans_final(features, k=3)
    etiquetas = dict(zip(features.index, modelo.predict(features.values)))

    assert etiquetas["Z1"] == etiquetas["Z2"]
    assert etiquetas["Z3"] == etiquetas["Z4"]
    assert etiquetas["Z5"] == etiquetas["Z6"]
    assert len({etiquetas["Z1"], etiquetas["Z3"], etiquetas["Z5"]}) == 3


def test_nombrar_clusters_asigna_los_3_perfiles_esperados():
    features = _features_sinteticas()
    modelo = entrenar_kmeans_final(features, k=3)
    nombres = nombrar_clusters(features, modelo)
    etiquetas = dict(zip(features.index, modelo.predict(features.values)))

    assert nombres[etiquetas["Z1"]] == "Perfil de alto impacto generalizado"
    assert nombres[etiquetas["Z3"]] == "Perfil hurto de bienes / ingreso alto"
    assert nombres[etiquetas["Z5"]] == "Perfil de bajo incidente relativo"


def test_construir_zona_cluster_forma_y_columnas():
    features = _features_sinteticas()
    modelo = entrenar_kmeans_final(features, k=3)
    nombres = nombrar_clusters(features, modelo)
    zona_cluster = construir_zona_cluster(features, modelo, nombres)

    assert list(zona_cluster.columns) == ["cod_localidad", "cluster", "nombre_perfil"]
    assert zona_cluster.shape == (6, 3)
    fila_z1 = zona_cluster[zona_cluster["cod_localidad"] == "Z1"].iloc[0]
    assert fila_z1["nombre_perfil"] == "Perfil de alto impacto generalizado"
