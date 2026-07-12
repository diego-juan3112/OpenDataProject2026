"""
flag_zscore.py — Issue #29

Deteccion de anomalias para el reporte ciudadano simulado: compara un conteo
reciente reportado por un ciudadano contra la linea base historica de #26
(media/desviacion por cod_localidad-tipo_delito, calculada SOLO con train).
No hace I/O -- recibe la tabla de linea_base ya calculada como parametro,
para ser testeable con datos sinteticos (mismo patron que
src/feature_engineering.py y models/clustering/clustering.py). Consumida por
el formulario de reporte del dashboard (Issue #36, no implementado aqui).
"""
from __future__ import annotations

import pandas as pd

UMBRAL_Z = 2.0  # |z| > 2 ~ 95%, umbral estandar para un flag simple de anomalia


def flag_zscore(
    cod_localidad: str,
    tipo_delito: str,
    conteo: float,
    linea_base: pd.DataFrame,
) -> dict:
    """Compara conteo contra el historico de (cod_localidad, tipo_delito).

    linea_base debe tener las columnas cod_localidad, tipo_delito, media,
    desviacion (formato exacto de calcular_linea_base en
    src/feature_engineering.py, Issue #26 -- ya filtrado a train, sin fuga).

    Casos:
    - Normal (desviacion > 0): z_score = (conteo - media) / desviacion;
      es_atipico = abs(z_score) > UMBRAL_Z.
    - desviacion == 0 (historico perfectamente constante, p. ej. Sumapaz en
      datos reales): z_score = None (la formula no aplica, se evita
      ZeroDivisionError); es_atipico = conteo != media -- cualquier cambio
      es significativo si el historico nunca vario.

    Lanza ValueError si (cod_localidad, tipo_delito) no esta en linea_base,
    en vez de devolver un resultado por defecto enganoso.

    Devuelve {"es_atipico": bool, "z_score": float | None, "media": float,
    "desviacion": float}.
    """
    fila = linea_base[
        (linea_base["cod_localidad"] == cod_localidad)
        & (linea_base["tipo_delito"] == tipo_delito)
    ]
    if fila.empty:
        raise ValueError(
            f"No hay linea base para cod_localidad={cod_localidad!r}, "
            f"tipo_delito={tipo_delito!r}."
        )

    media = fila["media"].iloc[0]
    desviacion = fila["desviacion"].iloc[0]

    if desviacion == 0:
        return {
            "es_atipico": bool(conteo != media),
            "z_score": None,
            "media": media,
            "desviacion": desviacion,
        }

    z_score = (conteo - media) / desviacion
    return {
        "es_atipico": bool(abs(z_score) > UMBRAL_Z),
        "z_score": z_score,
        "media": media,
        "desviacion": desviacion,
    }
