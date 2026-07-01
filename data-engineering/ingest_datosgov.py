"""
ingest_datosgov.py — Consumo DIRECTO del API oficial de datos.gov.co (Socrata).

Este script es la evidencia de "Uso de datos abiertos": consulta y filtra los
microdatos de la Policía Nacional publicados en datos.gov.co **por su API SoQL**
(no descarga un archivo servido por otro portal). Filtra a Bogotá (DANE 11001000)
y agrega a nivel ciudad × año (× tipo, cuando el dataset lo permite).

Naturaleza y rol:
  - Grano espacial: MUNICIPIO (Bogotá = un solo registro). NO por localidad.
  - Rol: triangulación/validación de las cifras de SIEDCO y señal de estacionalidad
    mensual a nivel ciudad. NO es el backbone del dataset analítico (ese es SIEDCO
    por localidad).
  - `fecha_hecho` viene como texto DD/MM/YYYY → se parsea en cliente.

Salida: data/interim/datosgov_policia.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

OUT = config.INTERIM / "datosgov_policia.parquet"
_HEADERS = {"User-Agent": "Mozilla/5.0 (AlertaCiudadana-pipeline)"}
_PAGE = 50000  # máximo de filas por página en Socrata sin app token


def _fetch_bogota(dataset: dict) -> pd.DataFrame:
    """Trae por API todas las filas de Bogotá de un dataset, con paginación SoQL."""
    url = f"{config.DATOSGOV_BASE}/{dataset['id']}.json"
    where = f"{dataset['filtro_col']}='{dataset['filtro_val']}'"
    filas, offset = [], 0
    while True:
        params = {"$where": where, "$limit": _PAGE, "$offset": offset}
        r = requests.get(url, params=params, headers=_HEADERS, timeout=120)
        r.raise_for_status()
        lote = r.json()
        filas.extend(lote)
        if len(lote) < _PAGE:
            break
        offset += _PAGE
    return pd.DataFrame(filas)


def _parse_anio(serie: pd.Series) -> pd.Series:
    """fecha_hecho puede venir como DD/MM/YYYY (texto) o ISO. Extrae el año."""
    dt = pd.to_datetime(serie, format="%d/%m/%Y", errors="coerce")
    dt = dt.fillna(pd.to_datetime(serie, errors="coerce"))  # fallback ISO
    return dt.dt.year


def run(force: bool = False) -> pd.DataFrame:
    config.ensure_dirs()
    print("== datos.gov.co (API Socrata directo) ==")

    partes = []
    for nombre, ds in config.DATOSGOV_DATASETS.items():
        print(f"  [api ] {nombre} ({ds['id']}) — GET {config.DATOSGOV_BASE}/{ds['id']}.json")
        raw = _fetch_bogota(ds)
        print(f"         {len(raw):,} filas de Bogotá recibidas por API")

        raw["anio"] = _parse_anio(raw["fecha_hecho"])
        raw["cantidad"] = pd.to_numeric(raw["cantidad"], errors="coerce").fillna(0).astype("int64")
        raw = raw[(raw["anio"] >= config.ANIO_MIN) & (raw["anio"] <= config.ANIO_MAX)]

        tipo_col = ds["tipo_col"]
        if tipo_col and tipo_col in raw.columns:
            g = raw.groupby(["anio", tipo_col])["cantidad"].sum().reset_index()
            g = g.rename(columns={tipo_col: "subtipo"})
        else:
            g = raw.groupby(["anio"])["cantidad"].sum().reset_index()
            g["subtipo"] = "TOTAL"

        g["delito"] = nombre
        g["fuente"] = f"datos.gov.co/{ds['id']}"
        partes.append(g[["delito", "anio", "subtipo", "cantidad", "fuente"]])

    out = pd.concat(partes, ignore_index=True).sort_values(["delito", "anio", "subtipo"])
    out = out.reset_index(drop=True)
    out.to_parquet(OUT, index=False)

    # ---- Verificación ----
    print("\n  Resumen por delito × año (Bogotá, vía API datos.gov.co):")
    piv = out.groupby(["delito", "anio"])["cantidad"].sum().reset_index()
    for delito in piv["delito"].unique():
        sub = piv[piv["delito"] == delito]
        serie = ", ".join(f"{int(r.anio)}:{int(r.cantidad):,}" for r in sub.itertuples())
        print(f"    {delito}: {serie}")
    print(f"  [ok] guardado: {OUT}")
    return out


if __name__ == "__main__":
    run(force="--force" in sys.argv)
