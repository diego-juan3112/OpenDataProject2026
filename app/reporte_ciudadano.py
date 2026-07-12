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
