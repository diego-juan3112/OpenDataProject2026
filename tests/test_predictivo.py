"""Tests del predictivo (#14–#16) con DataFrames sintéticos — sin parquet real."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "models" / "predictivo"))

import baselines
import features as feat
import model_training as mtrain


def _df_sintetico() -> pd.DataFrame:
    filas = []
    for loc in ("01", "02"):
        for tipo in ("HP", "H"):
            for anio in range(2018, 2026):
                conteo = 10 * (anio - 2017) * (2 if loc == "01" else 1)
                filas.append({
                    "cod_localidad": loc,
                    "localidad_nombre": "A" if loc == "01" else "B",
                    "anio": anio,
                    "tipo_delito": tipo,
                    "tipo_delito_nombre": tipo,
                    "conteo_siedco": conteo,
                    "conteo_nuse": 100,
                    "poblacion": 100_000,
                    "ipm_nbi": np.nan if loc == "02" else 5.0,
                    "split": "train" if anio <= 2024 else "test",
                    "riesgo_alto": 1 if conteo > 40 else 0,
                })
    return pd.DataFrame(filas)


def test_temporal_split_sin_fuga():
    df = _df_sintetico()
    train, test = mtrain.temporal_split(df)
    assert train["anio"].max() < test["anio"].min()
    assert set(test["anio"]) == {2025}
    assert (train["split"] == "train").all()


def test_lags_no_usan_anio_actual():
    df = _df_sintetico()
    built, _ = feat.build_feature_frame(df)
    row_2018 = built[(built.anio == 2018) & (built.cod_localidad == "01") & (built.tipo_delito == "HP")].iloc[0]
    assert row_2018["lag_1"] == 0.0
    row_2019 = built[(built.anio == 2019) & (built.cod_localidad == "01") & (built.tipo_delito == "HP")].iloc[0]
    row_prev = df[(df.anio == 2018) & (df.cod_localidad == "01") & (df.tipo_delito == "HP")].iloc[0]
    assert row_2019["lag_1"] == pytest.approx(row_prev["conteo_siedco"])


def test_ipm_sumapaz_imputado():
    df = _df_sintetico()
    built, mediana = feat.build_feature_frame(df[df.split == "train"])
    assert built["ipm_nbi"].isna().sum() == 0
    assert mediana == pytest.approx(5.0)


def test_baseline_mayoria_todo_cero():
    y = np.array([0, 0, 1, 0, 1])
    pred = baselines.baseline_mayoria(y)
    assert pred.tolist() == [0, 0, 0, 0, 0]


def test_no_incluye_conteo_siedco_como_feature():
    assert "conteo_siedco" not in feat.NUMERIC_FEATURES
    assert "conteo_siedco" not in feat.CATEGORICAL_FEATURES
