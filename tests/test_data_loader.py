"""Tests para data_loader (Issue #34): cargar_zonas_riesgo ahora llama a la
API real via requests, en vez de leer fixtures locales (retirados en esta
issue). cargar_densidad_nuse sigue local (NUSE no esta en el contrato de la
API) -- sus tests, de la Issue #33, no cambian.

Se mockea requests.get (frontera de red) -- unica excepcion al patron de
"datos reales o sinteticos, nunca mocks" de este repo: una unit test no
debe depender de que la API este corriendo. La prueba end-to-end real (API
+ dashboard corriendo juntos) se hace aparte, ver la Tarea 3 de este plan.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from data_loader import API_BASE_URL, cargar_densidad_nuse, cargar_zonas_riesgo

GEOJSON_EJEMPLO = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "cod_localidad": "01",
                "localidad_nombre": "USAQUEN",
                "nivel_riesgo": "medio",
                "probabilidad_riesgo": 0.4354,
                "riesgo_predicho": 0,
                "cluster": 0,
                "nombre_perfil": "Perfil de bajo incidente relativo",
                "anio": 2025,
                "tipo_delito": "HP",
            },
            "geometry": {"type": "Polygon", "coordinates": []},
        }
    ],
}


def test_cargar_zonas_riesgo_llama_a_la_api_con_los_parametros_correctos():
    cargar_zonas_riesgo.clear()
    with patch("data_loader.requests.get") as mock_get:
        mock_get.return_value = Mock(json=lambda: GEOJSON_EJEMPLO)
        mock_get.return_value.raise_for_status = lambda: None

        resultado = cargar_zonas_riesgo(2025, "HP")

    mock_get.assert_called_once_with(
        f"{API_BASE_URL}/zonas-riesgo",
        params={"anio": 2025, "tipo": "HP"},
        timeout=10,
    )
    assert resultado == GEOJSON_EJEMPLO


def test_cargar_zonas_riesgo_api_caida_lanza_runtime_error_claro():
    cargar_zonas_riesgo.clear()
    with patch("data_loader.requests.get", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(RuntimeError, match=API_BASE_URL):
            cargar_zonas_riesgo(2024, "H")


def test_cargar_zonas_riesgo_error_http_lanza_runtime_error():
    cargar_zonas_riesgo.clear()
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("422 tipo invalido")
    with patch("data_loader.requests.get", return_value=mock_response):
        with pytest.raises(RuntimeError):
            cargar_zonas_riesgo(2030, "ZZ")


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
