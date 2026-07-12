"""Tests para ubicar_localidad (Issue #36).

A diferencia de la mayoria de tests puros del repo, este usa la geometria
REAL commiteada en app/data/geometria_localidades.geojson (de #33) -- es
seguro en CI porque, a diferencia de data/, esta versionada en git.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from localidad_lookup import ubicar_localidad

GEOMETRIA_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "geometria_localidades.geojson"


def _cargar_geometria_real() -> dict:
    with open(GEOMETRIA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_ubicar_localidad_punto_real_dentro_de_usaquen():
    geometria = _cargar_geometria_real()

    # Punto representativo real dentro del poligono de Usaquen (cod "01"),
    # verificado con shapely antes de escribir este test.
    cod = ubicar_localidad(4.745190674500066, -74.02788785657322, geometria)

    assert cod == "01"


def test_ubicar_localidad_fuera_de_bogota_devuelve_none():
    geometria = _cargar_geometria_real()

    cod = ubicar_localidad(0.0, 0.0, geometria)

    assert cod is None


def test_ubicar_localidad_otro_punto_real_dentro_de_bogota():
    geometria = _cargar_geometria_real()

    # Punto cerca del centro geografico de Bogota, cae dentro de
    # Teusaquillo (cod "13") -- verificado con shapely antes de escribir
    # este test.
    cod = ubicar_localidad(4.65, -74.1, geometria)

    assert cod == "13"
