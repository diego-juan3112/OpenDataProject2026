"""Tests geofencing (#21) — point-in-polygon con geometria real o sintetica."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parent.parent
GEO = ROOT / "data" / "03_primary" / "zonas_bogota.geojson"


def riesgo_de_coordenada_py(lat: float, lon: float, geojson: dict) -> dict:
    """Referencia Python equivalente a riesgoDeCoordenada.js."""
    vacio = {
        "cod_localidad": None,
        "localidad_nombre": None,
        "nivel_riesgo": None,
        "fueraDeBogota": True,
    }
    if geojson is None or "features" not in geojson:
        return vacio
    pt = Point(lon, lat)
    for feat in geojson["features"]:
        geom = shape(feat["geometry"])
        if geom.contains(pt) or geom.intersects(pt):
            p = feat.get("properties") or {}
            return {
                "cod_localidad": p.get("cod_localidad"),
                "localidad_nombre": p.get("localidad_nombre"),
                "nivel_riesgo": p.get("nivel_riesgo"),
                "fueraDeBogota": False,
            }
    return vacio


def test_fuera_de_bogota_no_rompe():
    geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "cod_localidad": "01",
                    "localidad_nombre": "TEST",
                    "nivel_riesgo": "alto",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-74.1, 4.6], [-74.0, 4.6], [-74.0, 4.7], [-74.1, 4.7], [-74.1, 4.6]]
                    ],
                },
            }
        ],
    }
    # Oceano / fuera
    r = riesgo_de_coordenada_py(0.0, 0.0, geo)
    assert r["fueraDeBogota"] is True
    assert r["cod_localidad"] is None


def test_punto_dentro_poligono_sintetico():
    geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "cod_localidad": "01",
                    "localidad_nombre": "TEST",
                    "nivel_riesgo": "medio",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-74.1, 4.6], [-74.0, 4.6], [-74.0, 4.7], [-74.1, 4.7], [-74.1, 4.6]]
                    ],
                },
            }
        ],
    }
    r = riesgo_de_coordenada_py(4.65, -74.05, geo)
    assert r["fueraDeBogota"] is False
    assert r["cod_localidad"] == "01"
    assert r["nivel_riesgo"] == "medio"


@pytest.mark.skipif(not GEO.exists(), reason="zonas_bogota.geojson no disponible")
def test_punto_usaquen_geojson_real():
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    # Centroide aproximado de Usaquen no es trivial; usar representative_point
    from shapely.geometry import shape as shp

    feat01 = next(f for f in geo["features"] if f["properties"]["cod_localidad"] == "01")
    # Inyectar nivel mock
    feat01["properties"]["nivel_riesgo"] = "bajo"
    rp = shp(feat01["geometry"]).representative_point()
    r = riesgo_de_coordenada_py(rp.y, rp.x, {"type": "FeatureCollection", "features": [feat01]})
    assert r["fueraDeBogota"] is False
    assert r["cod_localidad"] == "01"
