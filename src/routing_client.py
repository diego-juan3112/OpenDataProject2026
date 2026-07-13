"""
routing_client.py — Cliente de OpenRouteService (feature Ruta Más Segura).

Issue #45: wrapper sobre el API REST de ORS (`get_routes`, `decodificar_ruta`).
Issue #47: spatial join ruta→localidades y score de la ruta
(`decodificar_ruta_gdf`, `localidades_de_ruta`, `score_ruta`). NO expone el
endpoint (eso es #48) ni recalcula scores por localidad (eso vive en #46).

Referencia de diseño: `diseño_tecnico_ruta_segura.md` §PARTE 2 y §PARTE 3.

Advertencia de coordenadas: ORS trabaja en orden **[lon, lat]**, no [lat, lon].
Invertirlas devuelve HTTP 400 o rutas fuera de Colombia.
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import polyline as polyline_lib
import requests
from shapely.geometry import LineString

# config.py vive en el mismo directorio; se añade src/ al path para que el
# import funcione tanto al importar como `src.routing_client` (desde la raíz)
# como al correr dentro de src/ (patrón usado en pipelines/pipeline_ml.py).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# Factor aproximado grados→metros en latitudes de Bogotá (1° ≈ 111.320 m).
_GRADOS_A_METROS = 111320
# Intervalo de muestreo de la ruta para el spatial join (~200 m).
_PASO_MUESTREO_M = 200


def get_routes(
    origen_lon: float,
    origen_lat: float,
    destino_lon: float,
    destino_lat: float,
    api_key: str,
    perfil: str = "driving-car",
    n_rutas: int = 2,
) -> dict:
    """Pide `n_rutas` rutas alternativas a ORS entre origen y destino.

    Llama a `POST {ORS_BASE_URL}/{perfil}/json`. El perfil va en la URL, no en el
    body. Devuelve el JSON completo de ORS (clave `routes`, cada una con
    `summary` y `geometry` en polyline codificada).

    Lanza `requests.HTTPError` si la respuesta no es 2xx.
    """
    url = f"{config.ORS_BASE_URL}/{perfil}/json"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "coordinates": [
            [origen_lon, origen_lat],    # ORS usa [lon, lat] — no al revés
            [destino_lon, destino_lat],
        ],
        "alternative_routes": {
            "target_count": n_rutas,     # cuántas rutas pedir (2 para el MVP)
            "weight_factor": 1.6,        # qué tan distintas deben ser (1.4–2.0)
        },
        "geometry": True,                # devolver la geometría de la ruta
        "instructions": False,           # no se necesita giro a giro en el MVP
    }
    response = requests.post(url, json=body, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def decodificar_ruta(encoded_geometry: str) -> list[tuple[float, float]]:
    """Decodifica la polyline codificada de ORS a lista de `(lon, lat)`.

    Se usa `geojson=True` para que `polyline` devuelva el orden [lon, lat]
    (el mismo que espera GeoJSON/Shapely), no [lat, lon].
    """
    return [tuple(p) for p in polyline_lib.decode(encoded_geometry, geojson=True)]


def decodificar_ruta_gdf(encoded_geometry: str) -> gpd.GeoDataFrame:
    """Versión GeoPandas de `decodificar_ruta()` para el spatial join (#47).

    Convierte la polyline de ORS en un GeoDataFrame de puntos muestreados cada
    ~200 m, listos para el spatial join. El muestreo reduce los miles de puntos
    de la polyline a un conjunto manejable sin perder cobertura geográfica, que
    es lo que mantiene el spatial join por debajo de los 500 ms del endpoint.
    """
    puntos = polyline_lib.decode(encoded_geometry, geojson=True)  # [[lon, lat], ...]
    if len(puntos) < 2:
        # Ruta degenerada: no hay línea que interpolar; se devuelven los puntos tal cual.
        return gpd.GeoDataFrame(geometry=gpd.points_from_xy(*zip(*puntos)) if puntos else [],
                                crs="EPSG:4326")

    linea = LineString(puntos)
    # `linea.length` está en grados; se pasa a metros para fijar el paso de ~200 m.
    largo_m = linea.length * _GRADOS_A_METROS
    n_pasos = max(int(largo_m // _PASO_MUESTREO_M), 1)
    # Fracciones normalizadas 0.0→1.0 (incluye inicio y fin) — evita el bug de
    # mezclar metros y grados que tiene el snippet de referencia del diseño.
    fracciones = [k / n_pasos for k in range(n_pasos + 1)]
    puntos_sample = [linea.interpolate(f, normalized=True) for f in fracciones]
    return gpd.GeoDataFrame(geometry=puntos_sample, crs="EPSG:4326")


def localidades_de_ruta(
    puntos_gdf: gpd.GeoDataFrame,
    zonas_gdf: gpd.GeoDataFrame,
) -> list[str]:
    """Spatial join: `cod_localidad` únicos que cruza la ruta, en orden.

    Para cada punto muestreado encuentra en qué localidad cae y devuelve la
    secuencia de `cod_localidad` en orden de aparición (sin duplicados),
    preservando la traza geográfica de la ruta. Los puntos fuera de Bogotá
    (sin localidad) se descartan.
    """
    cols = ["cod_localidad", "geometry"]
    joined = gpd.sjoin(puntos_gdf, zonas_gdf[cols], how="left", predicate="within")
    # Un punto en el borde puede matchear >1 polígono → un índice duplicado; se
    # conserva la primera coincidencia y se recupera el orden original.
    joined = joined[~joined.index.duplicated(keep="first")].reindex(puntos_gdf.index)

    # Fallback: los puntos que caen justo en el borde entre dos localidades
    # pueden no quedar `within` de ninguna; se reintentan con `intersects`.
    faltan = joined["cod_localidad"].isna()
    if faltan.any():
        pend = puntos_gdf.loc[faltan[faltan].index, ["geometry"]]
        fb = gpd.sjoin(pend, zonas_gdf[cols], how="left", predicate="intersects")
        fb = fb[~fb.index.duplicated(keep="first")]
        joined.loc[fb.index, "cod_localidad"] = fb["cod_localidad"]

    codigos = joined["cod_localidad"].dropna().tolist()
    # dict.fromkeys preserva el orden de primera aparición y elimina duplicados.
    return list(dict.fromkeys(codigos))


def score_ruta(localidades: list[str], scores_por_localidad: dict) -> dict:
    """Riesgo total de una ruta a partir de las localidades que atraviesa.

    El **nivel** se decide por el score MÁXIMO (no el promedio): si la ruta
    cruza aunque sea brevemente una zona de score alto, el nivel es ALTO —
    más conservador y honesto para una feature de seguridad.

    Devuelve `{score, score_max, nivel, localidades}`. Nunca lanza excepción:
    si `localidades` está vacía devuelve score 5.0 y nivel "DESCONOCIDO" para
    que el endpoint siempre pueda responder.
    """
    scores = [scores_por_localidad.get(loc, 5.0) for loc in localidades]
    if not scores:
        return {"score": 5.0, "score_max": 5.0, "nivel": "DESCONOCIDO", "localidades": []}

    score_promedio = sum(scores) / len(scores)
    score_max = max(scores)
    if score_max >= 7.5:
        nivel = "ALTO"
    elif score_max >= 4.5:
        nivel = "MEDIO"
    else:
        nivel = "BAJO"

    return {
        "score": round(score_promedio, 2),
        "score_max": round(score_max, 2),
        "nivel": nivel,
        "localidades": localidades,
    }
