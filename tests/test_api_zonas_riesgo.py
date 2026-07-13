"""Smoke tests de la API con TestClient.

Se saltan automaticamente si faltan model.joblib / clusters / parquet
(CI no versiona data/ ni *.joblib).
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "predictivo" / "model.joblib"
CLUSTERS = ROOT / "models" / "clustering" / "clusters.joblib"
ZONA = ROOT / "models" / "clustering" / "zona_cluster.parquet"
DATASET = ROOT / "data" / "03_primary" / "dataset_analitico.parquet"
GEO = ROOT / "data" / "03_primary" / "zonas_bogota.geojson"

pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in (MODEL, CLUSTERS, ZONA, DATASET, GEO)),
    reason="Artefactos locales de modelo/datos no disponibles",
)


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["n_zonas"] == 20
    assert 2025 in body["anios"]


def test_zonas_riesgo_default(client):
    r = client.get("/zonas-riesgo", params={"anio": 2025, "tipo": "HP"})
    assert r.status_code == 200
    geo = r.json()
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) == 20
    props = geo["features"][0]["properties"]
    for key in (
        "cod_localidad", "localidad_nombre", "cod_dane_mpio",
        "cluster", "nombre_perfil", "nivel_riesgo", "probabilidad_riesgo",
        "anio", "tipo_delito",
    ):
        assert key in props
    assert props["nivel_riesgo"] in {"bajo", "medio", "alto"}
    assert props["anio"] == 2025
    assert props["tipo_delito"] == "HP"


def test_zonas_riesgo_slug_tipo(client):
    r = client.get("/zonas-riesgo", params={"anio": 2025, "tipo": "hurto_personas"})
    assert r.status_code == 200
    assert r.json()["features"][0]["properties"]["tipo_delito"] == "HP"


def test_zonas_riesgo_tipo_invalido(client):
    r = client.get("/zonas-riesgo", params={"anio": 2025, "tipo": "no_existe"})
    assert r.status_code == 422


def test_zonas_riesgo_anio_invalido(client):
    r = client.get("/zonas-riesgo", params={"anio": 1999, "tipo": "HP"})
    assert r.status_code == 422
