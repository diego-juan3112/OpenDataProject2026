"""
generar_datasets_mapa.py — Issue #33 (riesgo/tipologia retirados en #34)

Genera los 3 archivos de datos reales que el dashboard sigue necesitando
localmente: geometria_localidades.geojson (capa NUSE, #33),
nuse_por_zona.json (capa NUSE, #33) y linea_base_zscore.json (reporte
ciudadano, #36). Riesgo y tipologia (antes generados aqui como
riesgo_por_zona.json / tipologia_zonas.json) se RETIRARON en la Issue #34:
ahora vienen de la API real GET /zonas-riesgo (#20), no de un fixture local
-- ver app/data_loader.py::cargar_zonas_riesgo(). conteo_nuse viene de
nuse_incidentes.parquet (#4), agregado a nivel localidad porque no existe
geometria real de UPZ en el pipeline (verificado: ni data/02_intermediate/
ni data/03_primary/ tienen limites de UPZ, solo de localidad).

Corrige el mismo bug de mojibake de "ANTONIO NARI(replacement)O" que el
mock de #32 ya corregia en zonas_bogota.geojson (bug real, preexistente,
documentado alli tambien; no se toca src/).

NUSE trae codigos de localidad invalidos ("99"=sin localizacion, "-0"=
basura, 0.94% de las filas) que se excluyen antes de agregar. Las
combinaciones (localidad, anio) sin ningun incidente NUSE se rellenan con
conteo_nuse=0 (cero estructural, mismo patron ya documentado en
pipeline_integration.py para el merge SIEDCO-NUSE) -- verificado: Sumapaz
(cod_localidad="20") no tiene ningun incidente NUSE en 2018.

Uso:
    python app/data/generar_datasets_mapa.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
import config
import feature_engineering

OUT_DIR = Path(__file__).resolve().parent
GEOMETRIA_PATH = OUT_DIR / "geometria_localidades.geojson"
NUSE_PATH = OUT_DIR / "nuse_por_zona.json"
LINEA_BASE_PATH = OUT_DIR / "linea_base_zscore.json"

NUSE_INCIDENTES_PATH = config.ROOT / "data" / "02_intermediate" / "nuse_incidentes.parquet"

TOLERANCIA_SIMPLIFICACION = 0.001  # ~100m, mismo criterio que #32

CORRECCIONES_NOMBRE = {
    # Bug preexistente en zonas_bogota.geojson (#5): la localidad 15 llega con
    # caracter de reemplazo Unicode (U+FFFD), irreversible en el pipeline real.
    # Se corrige solo aqui -- no se toca src/ (fuera de alcance de #33).
    "15": "ANTONIO NARIÑO",
}

CODIGOS_LOCALIDAD_VALIDOS = [f"{i:02d}" for i in range(1, 21)]


def run() -> None:
    print("== #33/#34/#36 Generar datasets reales del mapa ==")
    _generar_geometria()
    _generar_nuse()
    _generar_linea_base()
    print("\n  [ok] los 3 archivos de app/data/ estan listos")


def _generar_geometria() -> None:
    gdf = gpd.read_file(config.ZONAS_GEOJSON)
    gdf = gdf.sort_values("cod_localidad").reset_index(drop=True)
    gdf["localidad_nombre"] = gdf.apply(
        lambda fila: CORRECCIONES_NOMBRE.get(fila["cod_localidad"], fila["localidad_nombre"]),
        axis=1,
    )
    gdf["geometry"] = gdf.geometry.simplify(TOLERANCIA_SIMPLIFICACION, preserve_topology=True)
    gdf = gdf[["cod_localidad", "localidad_nombre", "cod_dane_mpio", "geometry"]]

    assert len(gdf) == 20, "deben quedar exactamente 20 localidades"
    if GEOMETRIA_PATH.exists():
        GEOMETRIA_PATH.unlink()
    gdf.to_file(GEOMETRIA_PATH, driver="GeoJSON")
    print(f"  geometria_localidades.geojson: {len(gdf)} localidades, {GEOMETRIA_PATH.stat().st_size} bytes")


def _generar_nuse() -> None:
    nuse = pd.read_parquet(NUSE_INCIDENTES_PATH)
    nuse = nuse[nuse["cod_localidad"].isin(CODIGOS_LOCALIDAD_VALIDOS)]
    agregado = nuse.groupby(["cod_localidad", "anio"])["cant_incidentes"].sum().reset_index()
    agregado.columns = ["cod_localidad", "anio", "conteo_nuse"]

    anios = range(config.ANIO_MIN, config.ANIO_MAX + 1)
    indice_completo = pd.MultiIndex.from_product(
        [CODIGOS_LOCALIDAD_VALIDOS, anios], names=["cod_localidad", "anio"]
    )
    agregado = (agregado.set_index(["cod_localidad", "anio"])
                        .reindex(indice_completo, fill_value=0)
                        .reset_index())
    agregado["anio"] = agregado["anio"].astype(int)
    agregado["conteo_nuse"] = agregado["conteo_nuse"].astype(int)
    registros = agregado.to_dict(orient="records")

    assert len(registros) == 160, "esperadas 20 localidades x 8 anios = 160 filas"
    ceros = [r for r in registros if r["conteo_nuse"] == 0]
    with open(NUSE_PATH, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False)
    print(f"  nuse_por_zona.json: {len(registros)} filas, "
          f"{len(ceros)} en cero estructural: {ceros}, {NUSE_PATH.stat().st_size} bytes")


def _generar_linea_base() -> None:
    df = pd.read_parquet(config.DATASET_ANALITICO)
    linea_base = feature_engineering.calcular_linea_base(df)
    linea_base["media"] = linea_base["media"].astype(float)
    linea_base["desviacion"] = linea_base["desviacion"].astype(float)
    registros = linea_base.to_dict(orient="records")

    assert len(registros) == 220, "esperadas 20 localidades x 11 tipos = 220 filas"
    with open(LINEA_BASE_PATH, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False)
    print(f"  linea_base_zscore.json: {len(registros)} filas, {LINEA_BASE_PATH.stat().st_size} bytes")


if __name__ == "__main__":
    run()
