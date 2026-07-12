"""Tests para data_loader (Issue #33): cargar_zonas_riesgo y
cargar_densidad_nuse.

A diferencia de la mayoria de tests del repo (que usan datos sinteticos),
estos leen los fixtures reales commiteados en app/data/ (generados por
app/data/generar_datasets_mapa.py, Issue #33) -- son seguros en CI porque,
a diferencia de data/, SI estan versionados en git.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from data_loader import cargar_zonas_riesgo, cargar_densidad_nuse


def test_cargar_zonas_riesgo_devuelve_20_localidades_con_riesgo_y_tipologia():
    geojson = cargar_zonas_riesgo(2025, "HP")

    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 20
    for feature in geojson["features"]:
        props = feature["properties"]
        assert props["riesgo_alto"] in (0, 1)
        assert isinstance(props["conteo_siedco"], int)
        assert props["nombre_perfil"] in {
            "Perfil de alto impacto generalizado",
            "Perfil hurto de bienes / ingreso alto",
            "Perfil de bajo incidente relativo",
        }


def test_cargar_zonas_riesgo_valores_reales_2025_hp():
    geojson = cargar_zonas_riesgo(2025, "HP")
    riesgo_por_localidad = {
        f["properties"]["cod_localidad"]: f["properties"]["riesgo_alto"]
        for f in geojson["features"]
    }

    # Kennedy (08), Engativa (10), Suba (11): las 3 unicas localidades en
    # riesgo alto para 2025/HP en el dato real (verificado corriendo el
    # generador contra dataset_analitico.parquet antes de escribir este test).
    assert riesgo_por_localidad["08"] == 1
    assert riesgo_por_localidad["10"] == 1
    assert riesgo_por_localidad["11"] == 1
    assert riesgo_por_localidad["01"] == 0
    assert sum(riesgo_por_localidad.values()) == 3


def test_cargar_zonas_riesgo_corrige_mojibake_antonio_narino():
    geojson = cargar_zonas_riesgo(2025, "HP")
    nombres = {f["properties"]["cod_localidad"]: f["properties"]["localidad_nombre"]
               for f in geojson["features"]}

    assert nombres["15"] == "ANTONIO NARIÑO"


def test_cargar_zonas_riesgo_combo_inexistente_lanza_value_error():
    with pytest.raises(ValueError):
        cargar_zonas_riesgo(2030, "HP")


def test_cargar_densidad_nuse_devuelve_20_localidades():
    geojson = cargar_densidad_nuse(2025)

    assert len(geojson["features"]) == 20
    for feature in geojson["features"]:
        assert isinstance(feature["properties"]["conteo_nuse"], int)
        assert feature["properties"]["conteo_nuse"] >= 0


def test_cargar_densidad_nuse_cero_estructural_sumapaz_2018():
    geojson = cargar_densidad_nuse(2018)
    conteo_sumapaz = next(
        f["properties"]["conteo_nuse"] for f in geojson["features"]
        if f["properties"]["cod_localidad"] == "20"
    )

    assert conteo_sumapaz == 0


def test_cargar_densidad_nuse_anio_inexistente_lanza_value_error():
    with pytest.raises(ValueError):
        cargar_densidad_nuse(2030)
