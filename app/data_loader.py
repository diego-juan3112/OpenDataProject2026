"""
data_loader.py — Issue #33 (reemplaza la funcion de mock de la Issue #32)

Carga los datos de las 3 capas del mapa desde app/data/ (generado por
app/data/generar_datasets_mapa.py, Issue #33 -- todos los valores son
reales, ver ese script y el spec de #33 para el detalle). Combina la
geometria (que no cambia) con los atributos del anio/tipo de delito
seleccionados, en tiempo de render.

cargar_zonas_riesgo(anio, tipo_delito) tiene la misma forma que tendra el
contrato real de GET /zonas-riesgo (#20, ver CLAUDE.md ss4) -- es la UNICA
funcion que la Issue #34 reemplaza por una llamada HTTP real, ahora
parametrizada de verdad (en #32 no tomaba parametros porque el mock era
estatico).

cargar_densidad_nuse(anio) es local siempre: NUSE no forma parte del
contrato de /zonas-riesgo (CLAUDE.md la describe como una capa propia del
dashboard, no del endpoint unico), asi que la Issue #34 no la toca.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"
GEOMETRIA_PATH = DATA_DIR / "geometria_localidades.geojson"
RIESGO_PATH = DATA_DIR / "riesgo_por_zona.json"
TIPOLOGIA_PATH = DATA_DIR / "tipologia_zonas.json"
NUSE_PATH = DATA_DIR / "nuse_por_zona.json"
LINEA_BASE_PATH = DATA_DIR / "linea_base_zscore.json"


@st.cache_data
def _cargar_geometria() -> dict:
    with open(GEOMETRIA_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def _cargar_riesgo() -> list[dict]:
    with open(RIESGO_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def _cargar_tipologia() -> list[dict]:
    with open(TIPOLOGIA_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def _cargar_nuse_crudo() -> list[dict]:
    with open(NUSE_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def cargar_zonas_riesgo(anio: int, tipo_delito: str) -> dict:
    """GeoJSON de las 20 localidades con riesgo real (#10) y tipologia real
    (#27) para el anio y tipo de delito elegidos.

    Cada feature agrega, ademas de la geometria: riesgo_alto (0/1),
    conteo_siedco, cluster y nombre_perfil. Lanza ValueError si no hay dato
    para la combinacion (anio, tipo_delito) pedida.
    """
    geojson = _cargar_geometria()
    riesgo_por_localidad = {
        fila["cod_localidad"]: fila
        for fila in _cargar_riesgo()
        if fila["anio"] == anio and fila["tipo_delito"] == tipo_delito
    }
    if not riesgo_por_localidad:
        raise ValueError(f"No hay datos de riesgo para anio={anio!r}, tipo_delito={tipo_delito!r}.")

    tipologia_por_localidad = {fila["cod_localidad"]: fila for fila in _cargar_tipologia()}

    for feature in geojson["features"]:
        cod = feature["properties"]["cod_localidad"]
        riesgo = riesgo_por_localidad[cod]
        tipologia = tipologia_por_localidad[cod]
        feature["properties"]["riesgo_alto"] = riesgo["riesgo_alto"]
        feature["properties"]["conteo_siedco"] = riesgo["conteo_siedco"]
        feature["properties"]["cluster"] = tipologia["cluster"]
        feature["properties"]["nombre_perfil"] = tipologia["nombre_perfil"]

    return geojson


@st.cache_data
def cargar_densidad_nuse(anio: int) -> dict:
    """GeoJSON de las 20 localidades con conteo_nuse real (agregado desde
    UPZ a nivel localidad, ver limitacion documentada en el spec de #33)
    para el anio elegido.

    Lanza ValueError si no hay dato para ese anio.
    """
    geojson = _cargar_geometria()
    nuse_por_localidad = {
        fila["cod_localidad"]: fila["conteo_nuse"]
        for fila in _cargar_nuse_crudo()
        if fila["anio"] == anio
    }
    if not nuse_por_localidad:
        raise ValueError(f"No hay datos de NUSE para anio={anio!r}.")

    for feature in geojson["features"]:
        cod = feature["properties"]["cod_localidad"]
        feature["properties"]["conteo_nuse"] = nuse_por_localidad[cod]

    return geojson


@st.cache_data
def cargar_linea_base() -> list[dict]:
    """Linea base historica real (#26): lista de dicts con cod_localidad,
    tipo_delito, media, desviacion. Consumida por
    app/reporte_ciudadano.py::construir_reporte (via flag_zscore, #29).
    """
    with open(LINEA_BASE_PATH, encoding="utf-8") as f:
        return json.load(f)
