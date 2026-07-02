"""
ingest_nuse.py — Issue #4

Ingesta de NUSE "Incidentes Tramitados en el C4 - Línea 123. Bogotá D.C."

Naturaleza del dato (verificada 2026-06-30):
  - CSV AGREGADO (NO nivel-incidente, NO lat/lon). ~112 MB, latin-1, sep=';'.
  - Grano: localidad × UPZ × año × mes × tipo_incidente, con CANT_INCIDENTES.
  - Cubre ene-2015 .. may-2026. Aquí se recorta a 2018–2025 para alinear con
    la ventana del dataset analítico (SIEDCO). La cobertura completa queda en
    data/raw/ por si se necesita para la capa de densidad histórica.
  - Rol en el proyecto: señal complementaria (volumen de llamadas de emergencia)
    y capa de densidad por UPZ. NO comparte taxonomía con los delitos SIEDCO.

Salidas:
  data/interim/nuse_incidentes.parquet  -> grano nativo (localidad×UPZ×año×mes×tipo)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import utils

OUT = config.INTERIM / "nuse_incidentes.parquet"

_COLS = [
    "ID", "ANIO", "MES", "TIPO_INCIDENTE", "TIPO_DETALLE",
    "COD_LOCALIDAD", "LOCALIDAD", "COD_UPZ", "UPZ", "CANT_INCIDENTES",
]


def run(force: bool = False) -> pd.DataFrame:
    config.ensure_dirs()
    print("== #4 NUSE ==")

    csv_path = utils.download(
        config.NUSE_CSV_URL, config.RAW_NUSE / "nuse_c4_linea123.csv", force=force
    )
    # Diccionario oficial de campos (pequeño) — se guarda para el data-dictionary.
    utils.download(
        config.NUSE_DICC_CAMPOS_URL, config.RAW_NUSE / "definicioncampos.csv", force=force
    )

    df = pd.read_csv(
        csv_path,
        sep=config.SEP_SDSCJ,
        encoding=config.ENCODING_SDSCJ,
        dtype=str,
        usecols=_COLS,
    )
    n_bruto = len(df)

    # Tipos numéricos y llaves normalizadas (Regla 1: código, no texto).
    df["anio"] = pd.to_numeric(df["ANIO"], errors="coerce").astype("Int64")
    df["mes"] = pd.to_numeric(df["MES"], errors="coerce").astype("Int64")
    df["cant_incidentes"] = pd.to_numeric(df["CANT_INCIDENTES"], errors="coerce").fillna(0).astype("int64")
    df[config.KEY_LOCALIDAD] = df["COD_LOCALIDAD"].astype(str).str.strip().str.zfill(2)
    df["cod_upz"] = df["COD_UPZ"].astype(str).str.strip()
    df["localidad_nombre"] = df["LOCALIDAD"].astype(str).str.strip()
    df["upz_nombre"] = df["UPZ"].astype(str).str.strip()
    df["tipo_incidente"] = df["TIPO_DETALLE"].astype(str).str.strip()
    df["cod_incidente"] = df["TIPO_INCIDENTE"].astype(str).str.strip()

    # Bucket "SIN LOCALIZACION" (cod_localidad = 99). Se marca, no se elimina en
    # bruto: es un hallazgo de calidad que se reporta y decide en el cruce (#8).
    sin_loc = df[config.KEY_LOCALIDAD] == "99"
    print(f"  filas brutas: {n_bruto:,} | 'SIN LOCALIZACION' (cod 99): "
          f"{sin_loc.sum():,} ({100*sin_loc.mean():.1f}%) -> {df.loc[sin_loc,'cant_incidentes'].sum():,} incidentes")

    # Recorte a la ventana 2018–2025.
    df = df[(df["anio"] >= config.ANIO_MIN) & (df["anio"] <= config.ANIO_MAX)].copy()

    out = df[[
        config.KEY_LOCALIDAD, "localidad_nombre", "cod_upz", "upz_nombre",
        "anio", "mes", "cod_incidente", "tipo_incidente", "cant_incidentes",
    ]].reset_index(drop=True)
    out.to_parquet(OUT, index=False)

    # ---- Verificación ----
    print(f"  filas 2018–2025: {len(out):,} | localidades: {out[config.KEY_LOCALIDAD].nunique()} "
          f"| UPZ: {out['cod_upz'].nunique()} | tipos incidente: {out['tipo_incidente'].nunique()}")
    print(f"  total llamadas tramitadas 2018–2025: {out['cant_incidentes'].sum():,}")
    print("  top 5 tipos de incidente por volumen:")
    top = out.groupby("tipo_incidente")["cant_incidentes"].sum().nlargest(5)
    for k, v in top.items():
        print(f"    {k[:45]:<45} -> {v:,}")
    print(f"  [ok] guardado: {OUT}")
    return out


if __name__ == "__main__":
    run(force="--force" in sys.argv)
