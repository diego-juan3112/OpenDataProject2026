"""
streamlit_app.py — Issue #32

Dashboard analitico de Alerta Ciudadana. Hoy: mapa base de Bogota + mock de
zonas-riesgo (via app/data_loader.py). La Issue #33 agrega las capas
completas (coropletico con leyenda, densidad NUSE, control de capas); la
Issue #34 reemplaza el mock por la API real GET /zonas-riesgo (#20).
"""
from __future__ import annotations

import sys
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config

from data_loader import cargar_zonas_riesgo

# Cubre las 20 localidades reales (incluida la rural Sumapaz al sur),
# verificado contra data/03_primary/zonas_bogota.geojson:
# lon [-74.4498, -73.9865], lat [3.7310, 4.8368]
LIMITES_BOGOTA = [[3.7310, -74.4498], [4.8368, -73.9865]]

COLOR_POR_NIVEL = {"bajo": "#2ecc71", "medio": "#f1c40f", "alto": "#e74c3c"}


def _estilo_zona(feature: dict) -> dict:
    nivel = feature["properties"]["nivel_riesgo"]
    return {
        "fillColor": COLOR_POR_NIVEL.get(nivel, "#95a5a6"),
        "color": "#555555",
        "weight": 1,
        "fillOpacity": 0.6,
    }


def main() -> None:
    st.set_page_config(page_title="Alerta Ciudadana", layout="wide")
    st.title("Alerta Ciudadana — Mapa de riesgo por zona")

    with st.sidebar:
        st.header("Controles")
        st.selectbox("Tipo de delito", options=list(config.SIEDCO_TIPOS.values()), index=2)
        st.select_slider("Año", options=list(range(2018, 2026)), value=2025)
        st.caption(
            "Datos de ejemplo (mock): el riesgo mostrado no proviene todavía "
            "del modelo predictivo real ni varía con estos controles — se "
            "conecta a la API real en la Issue #34."
        )

    zonas_riesgo = cargar_zonas_riesgo()

    mapa = folium.Map()
    mapa.fit_bounds(LIMITES_BOGOTA)
    folium.GeoJson(
        zonas_riesgo,
        name="Riesgo por zona (mock)",
        style_function=_estilo_zona,
        tooltip=folium.GeoJsonTooltip(
            fields=["localidad_nombre", "nombre_perfil", "nivel_riesgo"],
            aliases=["Localidad", "Perfil", "Nivel de riesgo"],
        ),
    ).add_to(mapa)

    st_folium(mapa, height=600)


if __name__ == "__main__":
    main()
