"""
ingest_divipola.py — Issue #5

Geometría oficial de las 20 localidades de Bogotá + códigos para el cruce.

Fuente: "Localidad. Bogotá D.C" (IDECA / Catastro), SHP en EPSG:4686.
  Campos relevantes: LocCodigo (2 díg.), LocNombre.

Este script:
  1. Descarga y extrae el shapefile (idempotente).
  2. Normaliza LocCodigo -> cod_localidad (2 díg., string).
  3. Añade cod_dane_mpio = 11001 (Bogotá) para dejar la puerta abierta a escalar
     a otros municipios por DIVIPOLA (Regla 1).
  4. Reproyecta a EPSG:4326 (WGS84) para consumo web (API/dashboard/móvil).
  5. Guarda geometría limpia en data/interim/localidades.geojson.

Salida: data/interim/localidades.geojson  (geometría base; el riesgo/cluster se
        adjunta en build_dataset.py una vez existan los modelos).
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import utils

OUT = config.INTERIM / "localidades.geojson"


def run(force: bool = False) -> gpd.GeoDataFrame:
    config.ensure_dirs()
    print("== #5 DIVIPOLA / Localidades ==")

    zip_path = utils.download(
        config.LOCALIDAD_SHP_URL, config.RAW_LOCALIDAD / "loca.zip", force=force
    )
    files = utils.unzip(zip_path, config.RAW_LOCALIDAD, force=force)
    shp = next(f for f in files if f.suffix.lower() == ".shp")

    gdf = gpd.read_file(shp)
    print(f"  columnas SHP: {list(gdf.columns)}")
    print(f"  CRS origen: {gdf.crs}")

    # Localizar la columna de código de forma robusta.
    code_col = next((c for c in gdf.columns if c.lower() == "loccodigo"), None)
    name_col = next((c for c in gdf.columns if c.lower() == "locnombre"), None)
    if code_col is None:
        raise RuntimeError(f"No encuentro columna de código de localidad en {list(gdf.columns)}")

    gdf[config.KEY_LOCALIDAD] = gdf[code_col].astype(str).str.strip().str.zfill(2)
    gdf["localidad_nombre"] = gdf[name_col].astype(str).str.strip() if name_col else None
    gdf["cod_dane_mpio"] = config.DANE_BOGOTA

    # Quedarnos solo con las 20 localidades reales.
    validos = {f"{i:02d}" for i in range(1, 21)}
    antes = len(gdf)
    gdf = gdf[gdf[config.KEY_LOCALIDAD].isin(validos)].copy()
    if len(gdf) != antes:
        print(f"  [nota] descartadas {antes - len(gdf)} geometría(s) fuera de 01..20")

    # Reproyectar a WGS84 para web.
    gdf = gdf.to_crs(config.CRS_WEB)

    gdf = gdf[[config.KEY_LOCALIDAD, "localidad_nombre", "cod_dane_mpio", "geometry"]]
    gdf = gdf.sort_values(config.KEY_LOCALIDAD).reset_index(drop=True)

    OUT.unlink(missing_ok=True)
    gdf.to_file(OUT, driver="GeoJSON")

    # ---- Verificación ----
    print(f"  localidades: {len(gdf)} | CRS salida: {gdf.crs}")
    b = gdf.total_bounds
    print(f"  bounding box (lon/lat): [{b[0]:.4f}, {b[1]:.4f}, {b[2]:.4f}, {b[3]:.4f}]")
    geom_ok = gdf.geometry.is_valid.all()
    print(f"  geometrías válidas: {geom_ok}")
    print("  " + ", ".join(f"{r[config.KEY_LOCALIDAD]}={r['localidad_nombre']}" for _, r in gdf.head(5).iterrows()) + " ...")
    print(f"  [ok] guardado: {OUT}")
    return gdf


if __name__ == "__main__":
    run(force="--force" in sys.argv)
