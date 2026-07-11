"""Tests para las features de perfil de zona y la linea base z-score (Issue #26).

Usan un DataFrame sintetico (no el parquet real): data/ no existe en CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from feature_engineering import (
    construir_features_zona,
    calcular_linea_base,
    conteo_total_por_zona,
)


def _df_sintetico(incluir_test: bool = False) -> pd.DataFrame:
    """DataFrame sintetico con el esquema de dataset_analitico.parquet:
    3 localidades x 2 tipos de delito x 7 anios de train (2018-2024),
    mas opcionalmente 1 fila de test (2025) para la prueba de fuga.
    """
    filas = []
    anios_train = range(2018, 2025)  # 7 anios

    conteos = {
        ("01", "A"): [10, 10, 10, 10, 10, 10, 10],  # constante -> desviacion 0
        ("01", "B"): [1, 2, 3, 4, 5, 6, 7],          # caso conocido: media 4, std ddof=1 ~2.1602
        ("02", "A"): [5, 15, 25, 5, 15, 25, 5],
        ("02", "B"): [20, 20, 20, 20, 20, 20, 20],
        ("03", "A"): [3, 6, 9, 3, 6, 9, 3],
        ("03", "B"): [50, 40, 30, 50, 40, 30, 50],
    }
    nuse_por_loc = {"01": 1000, "02": 2000, "03": 500}
    ipm_por_loc = {"01": 5.0, "02": 15.0, "03": np.nan}  # "03" simula a Sumapaz

    for (loc, tipo), valores in conteos.items():
        for anio, conteo in zip(anios_train, valores):
            filas.append({
                "cod_localidad": loc, "tipo_delito": tipo, "anio": anio,
                "conteo_siedco": conteo, "conteo_nuse": nuse_por_loc[loc],
                "poblacion": 100_000, "ipm_nbi": ipm_por_loc[loc], "split": "train",
            })

    if incluir_test:
        filas.append({
            "cod_localidad": "01", "tipo_delito": "A", "anio": 2025,
            "conteo_siedco": 999_999, "conteo_nuse": 1000,
            "poblacion": 100_000, "ipm_nbi": 5.0, "split": "test",
        })

    return pd.DataFrame(filas)


def test_features_zona_estandarizada_media_cero():
    df = _df_sintetico()
    features = construir_features_zona(df)

    assert features.shape == (3, 4)  # 3 localidades x (tasa_A, tasa_B, tasa_nuse, ipm_nbi)
    medias = features.mean()
    stds = features.std(ddof=0)
    assert medias.abs().max() < 1e-9
    assert (stds.round(6) == 1.0).all()


def test_ipm_nbi_sumapaz_se_imputa_con_mediana():
    df = _df_sintetico()
    features = construir_features_zona(df)
    # ipm_nbi crudo = [5.0, 15.0, NaN]; mediana de las 2 conocidas = 10.0.
    # Tras estandarizar, la localidad "03" (valor imputado == mediana) debe
    # quedar en 0 desviaciones estandar en la columna ipm_nbi.
    assert features.loc["03", "ipm_nbi"] == pytest.approx(0.0, abs=1e-9)


def test_linea_base_media_std_correctos():
    df = _df_sintetico()
    base = calcular_linea_base(df)

    fila = base[(base["cod_localidad"] == "01") & (base["tipo_delito"] == "B")].iloc[0]
    assert fila["media"] == pytest.approx(4.0)
    assert fila["desviacion"] == pytest.approx(2.160246899469287)

    fila_constante = base[(base["cod_localidad"] == "01") & (base["tipo_delito"] == "A")].iloc[0]
    assert fila_constante["media"] == pytest.approx(10.0)
    assert fila_constante["desviacion"] == pytest.approx(0.0)


def test_sin_fuga_solo_usa_train():
    df_sin_test = _df_sintetico(incluir_test=False)
    df_con_test = _df_sintetico(incluir_test=True)

    features_sin = construir_features_zona(df_sin_test)
    features_con = construir_features_zona(df_con_test)
    pd.testing.assert_frame_equal(features_sin, features_con)

    base_sin = calcular_linea_base(df_sin_test)
    base_con = calcular_linea_base(df_con_test)
    pd.testing.assert_frame_equal(base_sin, base_con)


def test_conteo_total_por_zona_suma_solo_train():
    df = _df_sintetico()
    conteo = conteo_total_por_zona(df)

    # "01": tipo A = 10*7=70, tipo B = 1+2+3+4+5+6+7=28 -> 98
    # "02": tipo A = 5+15+25+5+15+25+5=95, tipo B = 20*7=140 -> 235
    # "03": tipo A = 3+6+9+3+6+9+3=39, tipo B = 50+40+30+50+40+30+50=290 -> 329
    assert conteo.loc["01"] == 98
    assert conteo.loc["02"] == 235
    assert conteo.loc["03"] == 329
    assert conteo.name == "conteo_total"


def test_conteo_total_por_zona_sin_fuga():
    df_sin_test = _df_sintetico(incluir_test=False)
    df_con_test = _df_sintetico(incluir_test=True)

    conteo_sin = conteo_total_por_zona(df_sin_test)
    conteo_con = conteo_total_por_zona(df_con_test)
    pd.testing.assert_series_equal(conteo_sin, conteo_con)
