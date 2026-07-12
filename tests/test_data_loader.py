"""Tests para data_loader.cargar_zonas_riesgo (Issue #32).

A diferencia de la mayoria de tests del repo (que usan datos sinteticos),
este lee el fixture mock REAL: app/mock_data/zonas_riesgo_mock.geojson SI
esta commiteado en git (a diferencia de data/), asi que es seguro leerlo en
CI -- es un archivo estatico versionado, no el pipeline real.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from data_loader import cargar_zonas_riesgo

PROPIEDADES_ESPERADAS = {
    "cod_localidad", "localidad_nombre", "cod_dane_mpio", "cluster",
    "nombre_perfil", "nivel_riesgo", "probabilidad_riesgo", "anio", "tipo_delito",
}


def test_cargar_zonas_riesgo_devuelve_20_localidades():
    geojson = cargar_zonas_riesgo()

    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 20


def test_cargar_zonas_riesgo_propiedades_completas():
    geojson = cargar_zonas_riesgo()

    for feature in geojson["features"]:
        assert PROPIEDADES_ESPERADAS.issubset(feature["properties"].keys())
        assert feature["properties"]["nivel_riesgo"] in {"bajo", "medio", "alto"}


def test_cargar_zonas_riesgo_distribucion_nivel_riesgo():
    geojson = cargar_zonas_riesgo()
    niveles = [f["properties"]["nivel_riesgo"] for f in geojson["features"]]

    assert niveles.count("bajo") == 12
    assert niveles.count("medio") == 6
    assert niveles.count("alto") == 2


def test_cargar_zonas_riesgo_corrige_mojibake_antonio_narino():
    geojson = cargar_zonas_riesgo()
    nombres = {f["properties"]["cod_localidad"]: f["properties"]["localidad_nombre"]
               for f in geojson["features"]}

    assert nombres["15"] == "ANTONIO NARIÑO"
