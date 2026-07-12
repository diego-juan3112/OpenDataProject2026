"""Tests para flag_zscore, el flag de anomalia del reporte ciudadano (Issue #29).

Usa una tabla de linea_base sintetica (no el parquet real de #26): data/ y
models/clustering/linea_base_zscore.parquet no existen en CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flag_zscore import flag_zscore, UMBRAL_Z


def _linea_base_sintetica() -> pd.DataFrame:
    """2 combinaciones localidad-tipo: una con variacion historica normal,
    otra con desviacion 0 (mismo escenario real de Sumapaz en #26, donde el
    conteo historico fue 0 los 7 anios de train).
    """
    return pd.DataFrame([
        {"cod_localidad": "01", "tipo_delito": "A", "media": 100.0, "desviacion": 20.0},
        {"cod_localidad": "20", "tipo_delito": "HA", "media": 0.0, "desviacion": 0.0},
    ])


def test_flag_zscore_caso_normal_no_atipico():
    linea_base = _linea_base_sintetica()
    resultado = flag_zscore("01", "A", conteo=120.0, linea_base=linea_base)

    assert resultado["z_score"] == pytest.approx(1.0)
    assert resultado["es_atipico"] is False
    assert resultado["media"] == pytest.approx(100.0)
    assert resultado["desviacion"] == pytest.approx(20.0)


def test_flag_zscore_caso_normal_atipico():
    linea_base = _linea_base_sintetica()
    resultado = flag_zscore("01", "A", conteo=150.0, linea_base=linea_base)

    assert resultado["z_score"] == pytest.approx(2.5)
    assert resultado["es_atipico"] is True


def test_flag_zscore_umbral_es_dos():
    assert UMBRAL_Z == 2.0


def test_flag_zscore_desviacion_cero_conteo_igual_a_media_no_es_atipico():
    linea_base = _linea_base_sintetica()
    resultado = flag_zscore("20", "HA", conteo=0.0, linea_base=linea_base)

    assert resultado["z_score"] is None
    assert resultado["es_atipico"] is False
    assert resultado["media"] == pytest.approx(0.0)
    assert resultado["desviacion"] == pytest.approx(0.0)


def test_flag_zscore_desviacion_cero_conteo_distinto_es_atipico():
    linea_base = _linea_base_sintetica()
    resultado = flag_zscore("20", "HA", conteo=1.0, linea_base=linea_base)

    assert resultado["z_score"] is None
    assert resultado["es_atipico"] is True


def test_flag_zscore_combo_inexistente_lanza_value_error():
    linea_base = _linea_base_sintetica()

    with pytest.raises(ValueError):
        flag_zscore("99", "ZZ", conteo=10.0, linea_base=linea_base)
