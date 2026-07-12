"""Tests para construir_reporte (Issue #36).

Usa una linea_base sintetica (no el fixture real de app/data/) -- mismo
patron que tests/test_flag_zscore.py (#29), funcion que este modulo
reutiliza tal cual.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from reporte_ciudadano import construir_reporte

LINEA_BASE_SINTETICA = [
    {"cod_localidad": "01", "tipo_delito": "A", "media": 100.0, "desviacion": 20.0},
    {"cod_localidad": "20", "tipo_delito": "HA", "media": 0.0, "desviacion": 0.0},
]


def test_construir_reporte_caso_comun_es_atipico_por_debajo():
    reporte = construir_reporte("01", "A", "vi algo raro", 4.7, -74.0, LINEA_BASE_SINTETICA)

    assert reporte["es_atipico"] is True
    assert reporte["z_score"] == pytest.approx(-4.95)
    assert reporte["descripcion"] == "vi algo raro"
    assert reporte["cod_localidad"] == "01"
    assert reporte["lat"] == 4.7
    assert reporte["lon"] == -74.0


def test_construir_reporte_caso_historial_nulo_es_atipico_senal_genuina():
    reporte = construir_reporte("20", "HA", "primera vez que pasa esto", 1.9, -74.2, LINEA_BASE_SINTETICA)

    assert reporte["es_atipico"] is True
    assert reporte["z_score"] is None


def test_construir_reporte_combo_inexistente_lanza_value_error():
    with pytest.raises(ValueError):
        construir_reporte("99", "ZZ", "x", 0.0, 0.0, LINEA_BASE_SINTETICA)
