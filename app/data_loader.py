"""
data_loader.py — Issue #32

Carga el GeoJSON de zonas-riesgo. Hoy lee el fixture mock commiteado en
app/mock_data/zonas_riesgo_mock.geojson (generado por
app/mock_data/generar_mock.py, #32); la Issue #34 reemplaza el CUERPO de
cargar_zonas_riesgo() por una llamada HTTP real a GET /zonas-riesgo (#20),
sin cambiar su firma ni el resto de streamlit_app.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

MOCK_PATH = Path(__file__).resolve().parent / "mock_data" / "zonas_riesgo_mock.geojson"


@st.cache_data
def cargar_zonas_riesgo() -> dict:
    """Devuelve el GeoJSON de zonas-riesgo (mock, Issue #32).

    dict con forma de FeatureCollection: 20 features, cada una con geometry +
    properties (cod_localidad, localidad_nombre, cluster, nombre_perfil,
    nivel_riesgo, probabilidad_riesgo, anio, tipo_delito).
    """
    with open(MOCK_PATH, encoding="utf-8") as f:
        return json.load(f)
