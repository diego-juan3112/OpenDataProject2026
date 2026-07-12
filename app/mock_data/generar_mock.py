"""
generar_mock.py — Issue #32

Genera app/mock_data/zonas_riesgo_mock.geojson: un GeoJSON con la forma que
tendra GET /zonas-riesgo (#20, Integrante 2, aun no implementado), para que
el dashboard (#32) se pueda construir sin esperar a la API real.

Combina:
- Geometria + identidad REALES de data/03_primary/zonas_bogota.geojson (#5),
  simplificada (tolerancia 0.001 grados, ~100m) para que el fixture sea
  liviano y commiteable (el original pesa ~2.3 MB; simplificado, ~50 KB).
- Cluster + perfil REALES de models/clustering/zona_cluster.parquet (#27).
- Riesgo FALSO (nivel_riesgo, probabilidad_riesgo): el predictivo (#19,
  Integrante 2) no existe todavia. Se deriva del perfil de cluster REAL
  (alto impacto -> alto, hurto de bienes -> medio, bajo incidente -> bajo)
  mas un jitter deterministico (semilla fija = reproducible) para que no
  sea un unico valor repetido por perfil. NO es una prediccion real -- #34
  reemplaza esto por la respuesta real de GET /zonas-riesgo.
- Metadatos de consulta fijos (anio=2025, tipo_delito="HP"): la variacion
  por parametro es responsabilidad de #34, no de este scaffold.

Corrige tambien un bug de datos preexistente en el pipeline real (#5): la
localidad 15 llega con el nombre mal codificado ("ANTONIO NARI(replacement)O",
caracter de reemplazo Unicode irreversible -- verificado inspeccionando los
bytes crudos del geojson real). Se corrige SOLO en este fixture, documentado
aqui; el pipeline real de Integrante 1 sigue con el bug (fuera de alcance).

Uso:
    python app/mock_data/generar_mock.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
import config

OUT_PATH = Path(__file__).resolve().parent / "zonas_riesgo_mock.geojson"
ZONA_CLUSTER_PATH = config.ROOT / "models" / "clustering" / "zona_cluster.parquet"

TOLERANCIA_SIMPLIFICACION = 0.001  # ~100m, preserva la forma a escala de mapa web

CORRECCIONES_NOMBRE = {
    # Bug preexistente en zonas_bogota.geojson (#5): la localidad 15 llega con
    # caracter de reemplazo Unicode (U+FFFD), irreversible en el pipeline real.
    # Se corrige solo aqui -- no se toca src/ (fuera de alcance de #32).
    "15": "ANTONIO NARIÑO",
}

NIVEL_POR_PERFIL = {
    "Perfil de alto impacto generalizado": "alto",
    "Perfil hurto de bienes / ingreso alto": "medio",
    "Perfil de bajo incidente relativo": "bajo",
}
BASE_POR_NIVEL = {"alto": 0.8, "medio": 0.5, "bajo": 0.2}
SEMILLA_JITTER = 42
ANIO_MOCK = 2025
TIPO_DELITO_MOCK = "HP"  # Hurto Personas (ver src/config.py::SIEDCO_TIPOS)


def run() -> None:
    print("== #32 Generar mock de zonas-riesgo ==")
    gdf = gpd.read_file(config.ZONAS_GEOJSON)
    zona_cluster = pd.read_parquet(ZONA_CLUSTER_PATH)

    gdf = gdf.merge(zona_cluster[["cod_localidad", "cluster", "nombre_perfil"]],
                     on="cod_localidad", how="left")
    gdf = gdf.sort_values("cod_localidad").reset_index(drop=True)

    gdf["localidad_nombre"] = gdf.apply(
        lambda fila: CORRECCIONES_NOMBRE.get(fila["cod_localidad"], fila["localidad_nombre"]),
        axis=1,
    )
    gdf["geometry"] = gdf.geometry.simplify(TOLERANCIA_SIMPLIFICACION, preserve_topology=True)

    rng = random.Random(SEMILLA_JITTER)
    niveles, probabilidades = [], []
    for _, fila in gdf.iterrows():
        nivel = NIVEL_POR_PERFIL[fila["nombre_perfil"]]
        prob = round(BASE_POR_NIVEL[nivel] + rng.uniform(-0.1, 0.1), 3)
        niveles.append(nivel)
        probabilidades.append(prob)

    gdf["nivel_riesgo"] = niveles
    gdf["probabilidad_riesgo"] = probabilidades
    gdf["anio"] = ANIO_MOCK
    gdf["tipo_delito"] = TIPO_DELITO_MOCK

    gdf = gdf[["cod_localidad", "localidad_nombre", "cod_dane_mpio", "cluster",
               "nombre_perfil", "nivel_riesgo", "probabilidad_riesgo", "anio",
               "tipo_delito", "geometry"]]

    gdf.to_file(OUT_PATH, driver="GeoJSON")
    _verificar(gdf)


def _verificar(gdf: gpd.GeoDataFrame) -> None:
    assert len(gdf) == 20, "deben quedar exactamente 20 localidades"
    assert set(gdf["nivel_riesgo"]) <= {"bajo", "medio", "alto"}
    assert gdf.loc[gdf["cod_localidad"] == "15", "localidad_nombre"].iloc[0] == "ANTONIO NARIÑO"

    print(f"  {len(gdf)} localidades escritas en {OUT_PATH}")
    print(f"  distribucion nivel_riesgo:\n{gdf['nivel_riesgo'].value_counts().to_string()}")
    print(f"  tamano del archivo: {OUT_PATH.stat().st_size} bytes")
    print(f"\n  [ok] {OUT_PATH}")


if __name__ == "__main__":
    run()
