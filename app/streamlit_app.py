"""
streamlit_app.py — Issue #34 (conecta el coropletico de riesgo a la API real)

Dashboard analitico de Alerta Ciudadana. 3 capas, togglables: coropletico
de riesgo (modelo predictivo REAL via GET /zonas-riesgo, #20, #34, siempre
visible), densidad NUSE (agregada a nivel localidad -- no existe geometria
real de UPZ, ver app/README.md) y tipologia de zonas (K-Means real, #27),
estas dos ultimas activables con checkboxes del sidebar (no con el
LayerControl nativo de Leaflet, para mantener un solo lugar de controles
consistente con el resto de la app). cargar_densidad_nuse() se queda local
para siempre (NUSE no forma parte del contrato de esa API).
"""
from __future__ import annotations

import sys
from pathlib import Path

import branca.colormap as cm
import folium
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config

from data_loader import API_BASE_URL, cargar_zonas_riesgo, cargar_densidad_nuse, cargar_linea_base
from reporte_ciudadano import render_formulario_reporte

# Cubre las 20 localidades reales (incluida la rural Sumapaz al sur),
# verificado contra data/03_primary/zonas_bogota.geojson:
# lon [-74.4498, -73.9865], lat [3.7310, 4.8368]
LIMITES_BOGOTA = [[3.7310, -74.4498], [4.8368, -73.9865]]

COLOR_RIESGO = {"bajo": "#2ecc71", "medio": "#f1c40f", "alto": "#e74c3c"}
COLOR_TIPOLOGIA = {
    "Perfil de alto impacto generalizado": "#c0392b",
    "Perfil hurto de bienes / ingreso alto": "#f39c12",
    "Perfil de bajo incidente relativo": "#27ae60",
}
ICONO_POR_ATIPICO = {True: ("triangle-exclamation", "red"), False: ("circle-check", "green")}


def _estilo_riesgo(feature: dict) -> dict:
    nivel = feature["properties"]["nivel_riesgo"]
    return {"fillColor": COLOR_RIESGO.get(nivel, "#95a5a6"), "color": "#555555", "weight": 1, "fillOpacity": 0.6}


def _estilo_tipologia(feature: dict) -> dict:
    perfil = feature["properties"]["nombre_perfil"]
    return {"fillColor": COLOR_TIPOLOGIA.get(perfil, "#95a5a6"), "color": "#555555", "weight": 1, "fillOpacity": 0.6}


def main() -> None:
    st.set_page_config(page_title="Alerta Ciudadana", layout="wide")
    st.title("Alerta Ciudadana — Mapa de riesgo por zona")

    st.session_state.setdefault("reportes", [])

    with st.sidebar:
        st.header("Controles")
        tipo_nombre = st.selectbox("Tipo de delito", options=list(config.SIEDCO_TIPOS.values()), index=2)
        tipo_codigo = next(codigo for codigo, nombre in config.SIEDCO_TIPOS.items() if nombre == tipo_nombre)
        anio = st.select_slider(
            "Año", options=list(range(config.ANIO_MIN, config.ANIO_MAX + 1)), value=config.ANIO_MAX
        )
        st.caption(
            f"El coroplético de riesgo viene del modelo predictivo real, "
            f"vía la API en {API_BASE_URL}."
        )
        st.divider()
        mostrar_nuse = st.checkbox("Mostrar densidad NUSE", value=False)
        mostrar_tipologia = st.checkbox("Mostrar tipología de zonas", value=False)

    try:
        zonas_riesgo = cargar_zonas_riesgo(anio, tipo_codigo)
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    mapa = folium.Map()
    mapa.fit_bounds(LIMITES_BOGOTA)

    folium.GeoJson(
        zonas_riesgo,
        style_function=_estilo_riesgo,
        tooltip=folium.GeoJsonTooltip(
            fields=["localidad_nombre", "tipo_delito_nombre", "nivel_riesgo", "probabilidad_riesgo"],
            aliases=["Localidad", "Tipo de delito", "Nivel de riesgo", "Probabilidad"],
        ),
    ).add_to(mapa)

    if mostrar_nuse:
        densidad_nuse = cargar_densidad_nuse(anio)
        conteos_nuse = [f["properties"]["conteo_nuse"] for f in densidad_nuse["features"]]
        colormap = cm.LinearColormap(
            colors=["#fff5cc", "#e67e22", "#7b241c"], vmin=min(conteos_nuse), vmax=max(conteos_nuse)
        )
        colormap.caption = "Llamadas al 123 (agregado por localidad)"
        folium.GeoJson(
            densidad_nuse,
            style_function=lambda feature: {
                "fillColor": colormap(feature["properties"]["conteo_nuse"]),
                "color": "#555555",
                "weight": 1,
                "fillOpacity": 0.7,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["localidad_nombre", "conteo_nuse"],
                aliases=["Localidad", "Llamadas al 123"],
            ),
        ).add_to(mapa)
        colormap.add_to(mapa)

    if mostrar_tipologia:
        folium.GeoJson(
            zonas_riesgo,
            style_function=_estilo_tipologia,
            tooltip=folium.GeoJsonTooltip(
                fields=["localidad_nombre", "nombre_perfil"],
                aliases=["Localidad", "Perfil"],
            ),
        ).add_to(mapa)

    for reporte in st.session_state["reportes"]:
        icono_nombre, color = ICONO_POR_ATIPICO[reporte["es_atipico"]]
        folium.Marker(
            location=[reporte["lat"], reporte["lon"]],
            popup=folium.Popup(
                f"<b>{config.SIEDCO_TIPOS.get(reporte['tipo_delito'], reporte['tipo_delito'])}</b>"
                f"<br>{reporte['descripcion']}",
                max_width=250,
            ),
            icon=folium.Icon(color=color, icon=icono_nombre, prefix="fa"),
        ).add_to(mapa)

    map_data = st_folium(mapa, height=600)

    linea_base = cargar_linea_base()
    render_formulario_reporte(zonas_riesgo, linea_base, (map_data or {}).get("last_clicked"))


if __name__ == "__main__":
    main()
