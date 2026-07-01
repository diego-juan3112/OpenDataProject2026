"""
ingest_siedco.py — Issue #3

Ingesta de SIEDCO "Delito de Alto Impacto. Bogotá D.C." (fuente núcleo).

Naturaleza del dato (verificada 2026-06-30):
  - Polígono por localidad (EPSG:4686), 20 localidades de Bogotá.
  - Formato ANCHO: una columna por (tipo de delito × año), patrón CM<PREF><AA>CONT.
  - Conteos ANUALES (no hay mes ni franja horaria en el dato abierto).

Este script:
  1. Descarga y extrae el GeoJSON (idempotente).
  2. Lee con GeoPandas y valida CRS.
  3. DESPIVOTEA a formato largo: (cod_localidad, localidad, tipo_delito, anio, conteo).
  4. Filtra a la ventana 2018–2025 (config.ANIO_MIN..ANIO_MAX).
  5. Descarta filas que no sean una de las 20 localidades reales (reporta cuáles).
  6. Guarda data/interim/siedco_delitos.parquet.

Salida: data/interim/siedco_delitos.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import utils

OUT = config.INTERIM / "siedco_delitos.parquet"


def _col_for(prefijo: str, anio: int) -> str | None:
    """Nombre de columna ancha para (tipo, año), tolerando la truncación de HCE."""
    yy = f"{anio % 100:02d}"
    for cand in (f"CM{prefijo}{yy}CONT", f"CM{prefijo}{yy}CON"):
        if cand in _COLS_SET:
            return cand
    return None


_COLS_SET: set[str] = set()  # se llena en run()


def run(force: bool = False) -> pd.DataFrame:
    config.ensure_dirs()
    print("== #3 SIEDCO ==")

    zip_path = utils.download(
        config.SIEDCO_GEOJSON_URL, config.RAW_SIEDCO / "dai_geojson.zip", force=force
    )
    files = utils.unzip(zip_path, config.RAW_SIEDCO, force=force)
    geojson = next(f for f in files if f.suffix.lower() == ".geojson")

    gdf = gpd.read_file(geojson)
    assert gdf.crs is not None and gdf.crs.to_epsg() == 4686, f"CRS inesperado: {gdf.crs}"
    global _COLS_SET
    _COLS_SET = set(gdf.columns)

    # Normalizar identidad de localidad (Regla 1: cruzar por código, no por nombre).
    df = pd.DataFrame(gdf.drop(columns="geometry"))
    df[config.KEY_LOCALIDAD] = (
        df[config.SIEDCO_COL_CODLOCAL].astype(str).str.strip().str.zfill(2)
    )
    df["localidad_nombre"] = df[config.SIEDCO_COL_NOMLOCAL].astype(str).str.strip()

    # Detectar filas que NO son una de las 20 localidades (01..20).
    validos = {f"{i:02d}" for i in range(1, 21)}
    no_localidad = df.loc[~df[config.KEY_LOCALIDAD].isin(validos)]
    if len(no_localidad):
        print(
            f"  [nota] {len(no_localidad)} fila(s) no-localidad descartada(s): "
            + ", ".join(
                f"{r[config.KEY_LOCALIDAD]}='{r['localidad_nombre']}'"
                for _, r in no_localidad.iterrows()
            )
        )
    df = df.loc[df[config.KEY_LOCALIDAD].isin(validos)].copy()

    # Despivotear (tipo × año) -> largo.
    registros = []
    for prefijo, etiqueta in config.SIEDCO_TIPOS.items():
        for anio in range(config.ANIO_MIN, config.ANIO_MAX + 1):
            col = _col_for(prefijo, anio)
            if col is None:
                continue
            sub = df[[config.KEY_LOCALIDAD, "localidad_nombre", col]].copy()
            sub = sub.rename(columns={col: "conteo"})
            sub["tipo_delito"] = etiqueta
            sub["cod_delito"] = prefijo
            sub["anio"] = anio
            registros.append(sub)

    largo = pd.concat(registros, ignore_index=True)
    largo["conteo"] = largo["conteo"].fillna(0).astype("int64")
    largo = largo[
        [config.KEY_LOCALIDAD, "localidad_nombre", "anio", "cod_delito", "tipo_delito", "conteo"]
    ].sort_values([config.KEY_LOCALIDAD, "anio", "cod_delito"]).reset_index(drop=True)

    largo.to_parquet(OUT, index=False)

    # ---- Verificación en pantalla (primer run) ----
    print(f"  filas: {len(largo):,} | localidades: {largo[config.KEY_LOCALIDAD].nunique()} "
          f"| años: {sorted(largo['anio'].unique())} | tipos: {largo['tipo_delito'].nunique()}")
    print(f"  total incidentes 2018–2025: {largo['conteo'].sum():,}")
    print("  top 5 (localidad, tipo, año) por conteo:")
    top = largo.nlargest(5, "conteo")
    for _, r in top.iterrows():
        print(f"    {r[config.KEY_LOCALIDAD]} {r['localidad_nombre']:<16} "
              f"{r['tipo_delito']:<22} {r['anio']}  ->  {r['conteo']:,}")
    print(f"  [ok] guardado: {OUT}")
    return largo


if __name__ == "__main__":
    run(force="--force" in sys.argv)
