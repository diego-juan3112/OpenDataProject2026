"""
pipeline_ml.py (antes build_dataset.py) — Issue #9  🎯

Script maestro del pipeline de datos. Corre de inicio a fin sin intervención
manual y produce los DOS entregables que desbloquean al resto del equipo (SYNC-1):

  data/03_primary/dataset_analitico.parquet   (cod_localidad × anio × tipo_delito)
  data/03_primary/zonas_bogota.geojson        (20 polígonos, EPSG:4326)

Orquesta: limpieza (Issue #7) → cruce por código (Issue #8) → marca de split
espacio-temporal → escritura de salidas + verificación.

Requisitos previos (ingesta, Issues #3–#6) — deben existir en data/02_intermediate/:
  siedco_delitos.parquet · nuse_incidentes.parquet · localidades.geojson ·
  dane_contexto.parquet. Si falta dane_contexto, se genera al vuelo (Issue #6).

Uso:
    python pipelines/pipeline_ml.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config
import data_cleaning
import feature_engineering
import pipeline_integration

# Columnas finales del dataset analítico (contrato con Integrantes 2 y 3).
# `riesgo_alto` es la variable objetivo del predictivo (Issue #10).
COLS_FINAL = [
    "cod_localidad", "localidad_nombre", "anio", "tipo_delito", "tipo_delito_nombre",
    "conteo_siedco", "conteo_nuse", "poblacion", "ipm_nbi", "split", "riesgo_alto",
]


def _requisitos() -> None:
    """Verifica los insumos de ingesta; genera dane_contexto si falta (Issue #6)."""
    faltan = [p.name for p in (
        config.INTERIM / "siedco_delitos.parquet",
        config.INTERIM / "nuse_incidentes.parquet",
        config.INTERIM / "localidades.geojson",
    ) if not p.exists()]
    if faltan:
        raise SystemExit(f"Faltan insumos de ingesta (correr Issues #3–#5): {faltan}")

    if not (config.INTERIM / "dane_contexto.parquet").exists():
        print("  [info] dane_contexto.parquet no existe → generando (Issue #6)…")
        import ingest_dane
        ingest_dane.run()


def _marcar_split(df: pd.DataFrame) -> pd.DataFrame:
    """Split espacio-temporal sin fuga: train ≤2024, test = 2025 (Restricción)."""
    df = df.copy()
    df["split"] = df["anio"].apply(lambda a: "train" if a <= 2024 else "test")
    return df


def run() -> pd.DataFrame:
    print("== #9 Dataset analítico final ==")
    config.ensure_dirs()
    _requisitos()

    # 1) Limpieza consolidada (regenera *_clean.parquet, idempotente).
    data_cleaning.run()

    # 2) Cruce por código + validación.
    pipeline_integration.run()

    # 3) Tabla analítica + split + variable objetivo (Issue #10).
    df = pipeline_integration.tabla_analitica().rename(columns={"ipm_pct": "ipm_nbi"})
    df = _marcar_split(df)
    df, _umbrales = feature_engineering.add_target_riesgo_alto(df)
    df = df[COLS_FINAL].sort_values(["cod_localidad", "anio", "tipo_delito"]).reset_index(drop=True)

    # 4) Escritura de salidas finales.
    df.to_parquet(config.DATASET_ANALITICO, index=False)

    zonas = pipeline_integration.tabla_zonas()
    config.ZONAS_GEOJSON.unlink(missing_ok=True)
    zonas.to_file(config.ZONAS_GEOJSON, driver="GeoJSON")

    _verificar(df, zonas)
    return df


def _verificar(df: pd.DataFrame, zonas) -> None:
    print("\n-- Verificación de salidas --")
    esperado = 20 * (config.ANIO_MAX - config.ANIO_MIN + 1) * len(config.SIEDCO_TIPOS)
    print(f"  dataset_analitico: {df.shape[0]} filas × {df.shape[1]} cols "
          f"(esperado {esperado} = 20 loc × {config.ANIO_MAX-config.ANIO_MIN+1} años × "
          f"{len(config.SIEDCO_TIPOS)} tipos)")
    assert df.shape[0] == esperado, "conteo de filas inesperado"
    print(f"  localidades: {df['cod_localidad'].nunique()} | "
          f"años: {df['anio'].min()}–{df['anio'].max()} | "
          f"tipos: {df['tipo_delito'].nunique()}")
    print(f"  split: {df['split'].value_counts().to_dict()}")
    print(f"  train años: {sorted(df.loc[df.split=='train','anio'].unique())}")
    print(f"  test  años: {sorted(df.loc[df.split=='test','anio'].unique())}")
    ipm_nulos = sorted(df.loc[df['ipm_nbi'].isna(), 'cod_localidad'].unique())
    print(f"  ipm_nbi nulo (Sumapaz sin EM, documentado): {ipm_nulos}")
    ra_tr = df.loc[df.split == 'train', 'riesgo_alto']
    print(f"  riesgo_alto (train) — objetivo #10: {ra_tr.value_counts().to_dict()} "
          f"({ra_tr.mean()*100:.1f}% clase 1)")
    print(f"  zonas_bogota.geojson: {len(zonas)} polígonos | CRS {zonas.crs}")
    assert len(zonas) == 20 and zonas.crs.to_epsg() == 4326
    print(f"\n  [ok] {config.DATASET_ANALITICO}")
    print(f"  [ok] {config.ZONAS_GEOJSON}")

    # Mensaje SYNC-1 para el equipo.
    print("\n" + "=" * 70)
    print("SYNC-1 · dataset listo para Integrantes 2 (predictivo/API) y 3 (clustering)")
    print("=" * 70)
    print(f"Ruta: {config.DATASET_ANALITICO}")
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print("\ndf.head():")
        print(df.head(8).to_string(index=False))
        print("\ndf.describe(numeric):")
        print(df[["anio", "conteo_siedco", "conteo_nuse", "poblacion", "ipm_nbi"]].describe().to_string())


if __name__ == "__main__":
    run()
