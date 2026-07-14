"""
data_loader.py — Issue #34 (reemplaza el fixture local de riesgo/tipologia
de la Issue #33 por la API real)

cargar_zonas_riesgo() llama a la API real GET /zonas-riesgo (#20, de
Integrante 2) -- ya no lee fixtures locales de riesgo/tipologia (esos
quedaron obsoletos y se retiraron en esta issue, ver
app/data/generar_datasets_mapa.py). cargar_densidad_nuse() y
cargar_linea_base() SIGUEN leyendo fixtures locales: NUSE no forma parte
del contrato de la API (CLAUDE.md ss4) y la linea base del reporte
ciudadano (#36) tampoco.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"
GEOMETRIA_PATH = DATA_DIR / "geometria_localidades.geojson"
NUSE_PATH = DATA_DIR / "nuse_por_zona.json"
LINEA_BASE_PATH = DATA_DIR / "linea_base_zscore.json"

API_BASE_URL = os.environ.get("ALERTA_API_URL", "http://localhost:8000")


@st.cache_data
def _cargar_geometria() -> dict:
    with open(GEOMETRIA_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def _cargar_nuse_crudo() -> list[dict]:
    with open(NUSE_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=300)
def cargar_zonas_riesgo(anio: int, tipo_delito: str) -> dict:
    """GeoJSON de las 20 localidades con riesgo REAL (modelo predictivo,
    #19) y tipologia REAL (#27), pedido a la API real GET /zonas-riesgo
    (#20). Cacheado 5 minutos (ttl=300): no se re-pide en cada interaccion
    del sidebar, pero tampoco queda pegado indefinidamente si la API se
    reinicia con un modelo nuevo.

    Lanza RuntimeError con un mensaje claro si la API no responde (caida,
    timeout, error HTTP) -- streamlit_app.py lo atrapa y muestra con
    st.error en vez de dejar que tumbe la app.
    """
    try:
        respuesta = requests.get(
            f"{API_BASE_URL}/zonas-riesgo",
            params={"anio": anio, "tipo": tipo_delito},
            timeout=10,
        )
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"No se pudo conectar a la API en {API_BASE_URL}/zonas-riesgo "
            f"(anio={anio}, tipo={tipo_delito}). ¿Está corriendo "
            f"`uvicorn api.main:app`? Detalle: {exc}"
        ) from exc


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
