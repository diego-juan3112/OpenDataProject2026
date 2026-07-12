"""
reporte_ciudadano.py — Issue #36

Reporte ciudadano simulado: construye un reporte (localidad + tipo de
delito + descripcion + ubicacion) y lo evalua con flag_zscore() (#29,
src/flag_zscore.py, reutilizado tal cual, no reimplementado) contra la
linea base historica real (#26, app/data/linea_base_zscore.json).

Cada reporte se evalua de forma INDEPENDIENTE con conteo=1 (no un conteo
acumulado de la sesion): flag_zscore compara ese unico caso contra el
promedio HISTORICO ANUAL de esa localidad-tipo, asi que el resultado casi
siempre sale "por debajo del promedio" (z muy negativo) -- es la lectura
honesta, dado que 1 reporte nunca es comparable en escala a un promedio
anual. La excepcion real: localidades sin ningun historico para ese tipo
(desviacion=0), donde un solo reporte SI es una desviacion genuina (ver
docstring de flag_zscore para ese caso).

Sin base de datos: quien llama construir_reporte guarda el resultado en
st.session_state (ver la funcion de UI, agregada en un paso posterior de
este mismo modulo) -- se pierde al cerrar la sesion, decision de alcance ya
fijada en CLAUDE.md ss1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from flag_zscore import flag_zscore


def construir_reporte(
    cod_localidad: str,
    tipo_delito: str,
    descripcion: str,
    lat: float,
    lon: float,
    linea_base: list[dict],
) -> dict:
    """Construye un reporte evaluado contra la linea base real (#26).

    linea_base es la lista de dicts cod_localidad/tipo_delito/media/
    desviacion (formato de app/data/linea_base_zscore.json). Se evalua con
    conteo=1 (ver docstring del modulo). Lanza ValueError (de flag_zscore)
    si no hay linea base para (cod_localidad, tipo_delito).

    Devuelve un dict listo para st.session_state: los datos del reporte
    mas el resultado de flag_zscore (es_atipico, z_score, media,
    desviacion).
    """
    df_linea_base = pd.DataFrame(linea_base)
    resultado = flag_zscore(cod_localidad, tipo_delito, conteo=1, linea_base=df_linea_base)

    return {
        "cod_localidad": cod_localidad,
        "tipo_delito": tipo_delito,
        "descripcion": descripcion,
        "lat": lat,
        "lon": lon,
        **resultado,
    }


import streamlit as st

import config  # src/ ya esta en sys.path por el sys.path.insert de la Tarea 3, arriba en este mismo archivo

from localidad_lookup import ubicar_localidad

AVISO_PRIVACIDAD = (
    "Los datos de este reporte (ubicación, tipo de delito, descripción) se "
    "usan únicamente para esta demostración, viven solo en tu sesión del "
    "navegador (no se guardan en ninguna base de datos) y se borran al "
    "cerrar la pestaña. No se comparten con terceros. Al continuar, aceptas "
    "el tratamiento de estos datos conforme a la Ley 1581 de 2012 "
    "(protección de datos personales, Colombia)."
)


def _mensaje_resultado(reporte: dict) -> None:
    tipo_nombre = config.SIEDCO_TIPOS.get(reporte["tipo_delito"], reporte["tipo_delito"])
    if reporte["z_score"] is None:
        st.warning(
            f":material/report: Esta zona no tenía ningún caso histórico de "
            f"{tipo_nombre} en los datos de entrenamiento — tu "
            "reporte es una señal genuina de algo nuevo en esta localidad."
        )
        return

    st.info(
        f":material/info: Tu reporte es 1 caso puntual. El promedio "
        f"histórico anual para esta localidad y tipo de delito es de "
        f"{reporte['media']:.0f} casos (z={reporte['z_score']:.2f}) — es "
        "normal que un solo reporte quede muy por debajo de un promedio "
        "anual; esto no es una alerta de riesgo por sí solo."
    )


def render_formulario_reporte(zonas_riesgo: dict, linea_base: list[dict], ultimo_clic: dict | None) -> None:
    """Renderiza el formulario de reporte ciudadano (Issue #36).

    zonas_riesgo es el GeoJSON ya cargado por cargar_zonas_riesgo() (tiene
    la geometria real de las 20 localidades) -- se reutiliza aqui para
    ubicar_localidad(), sin cargar la geometria una segunda vez.

    ultimo_clic es el dict que devuelve st_folium() en 'last_clicked'
    ({"lat": .., "lng": ..}) de la corrida anterior del mapa, o None si
    todavia no se ha hecho clic (Issue #36, criterio: no rompe ante input
    faltante).

    Al enviar un reporte, esta funcion fuerza un st.rerun(): los marcadores
    del mapa se dibujan en streamlit_app.py ANTES de llamar a esta funcion
    (necesitan el session_state ya actualizado), asi que sin el rerun el
    marcador del reporte recien enviado no aparece hasta la siguiente
    interaccion del usuario. El resultado (_mensaje_resultado) se guarda en
    session_state para mostrarse justo despues del rerun.
    """
    st.session_state.setdefault("reportes", [])
    st.session_state.setdefault("consentimiento_reporte", False)
    st.session_state.setdefault("ultimo_resultado", None)

    st.subheader(":material/campaign: Reporte ciudadano (simulado)")

    if st.session_state["ultimo_resultado"] is not None:
        _mensaje_resultado(st.session_state["ultimo_resultado"])

    with st.expander("Aviso de privacidad", expanded=not st.session_state["consentimiento_reporte"]):
        st.write(AVISO_PRIVACIDAD)
        st.session_state["consentimiento_reporte"] = st.checkbox(
            "Acepto el tratamiento de mis datos para esta demostración",
            value=st.session_state["consentimiento_reporte"],
        )

    if not st.session_state["consentimiento_reporte"]:
        st.caption("Marca el checkbox de consentimiento para habilitar el formulario.")
        return

    if ultimo_clic is None:
        st.caption("Haz clic en el mapa para elegir la ubicación del reporte.")
        return

    lat, lon = ultimo_clic["lat"], ultimo_clic["lng"]
    cod_localidad = ubicar_localidad(lat, lon, zonas_riesgo)
    if cod_localidad is None:
        st.error("Esa ubicación está fuera de Bogotá. Haz clic dentro de una de las 20 localidades.")
        return

    with st.form("form_reporte_ciudadano", clear_on_submit=True):
        tipo_nombre = st.selectbox("Tipo de delito", options=list(config.SIEDCO_TIPOS.values()))
        descripcion = st.text_area("Descripción (requerida)")
        enviado = st.form_submit_button(":material/send: Enviar reporte")

    if enviado:
        if not descripcion.strip():
            st.error("La descripción es obligatoria.")
            return
        tipo_codigo = next(codigo for codigo, nombre in config.SIEDCO_TIPOS.items() if nombre == tipo_nombre)
        reporte = construir_reporte(cod_localidad, tipo_codigo, descripcion.strip(), lat, lon, linea_base)
        st.session_state["reportes"].append(reporte)
        st.session_state["ultimo_resultado"] = reporte
        st.rerun()
