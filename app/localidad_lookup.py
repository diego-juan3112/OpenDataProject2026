"""
localidad_lookup.py — Issue #36

Determina a que localidad de Bogota pertenece un punto (lat, lon), via
point-in-polygon sobre la geometria real de las 20 localidades (#33). No
lee archivos -- recibe la geometria ya cargada como parametro, mismo patron
de funciones puras del resto del proyecto (models/clustering/clustering.py,
src/feature_engineering.py).
"""
from __future__ import annotations

from shapely.geometry import Point, shape


def ubicar_localidad(lat: float, lon: float, geometria: dict) -> str | None:
    """cod_localidad de la zona que contiene (lat, lon), o None si esta
    fuera de las 20 localidades de Bogota (Issue #36, criterio: rechaza
    coordenadas fuera de Bogota).

    geometria es el GeoJSON de app/data/geometria_localidades.geojson
    (FeatureCollection, EPSG:4326 -- shapely.Point espera (lon, lat), no
    (lat, lon)).
    """
    punto = Point(lon, lat)
    for feature in geometria["features"]:
        poligono = shape(feature["geometry"])
        if poligono.contains(punto):
            return feature["properties"]["cod_localidad"]
    return None
