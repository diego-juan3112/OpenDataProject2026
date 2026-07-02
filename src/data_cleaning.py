"""
clean_normalize.py — Issue #7

Limpieza consolidada: aplica las MISMAS reglas de calidad a cada fuente antes de
cruzarlas (Issue #8). No mezcla taxonomías: SIEDCO (11 tipos de delito) y NUSE
(tipos de incidente) se limpian por separado y se mantienen como variables
distintas — no son la misma cosa.

Reglas aplicadas (documentadas en el reporte de calidad):

  SIEDCO
    - `cod_localidad` normalizado a string de 2 dígitos.
    - Se descarta cualquier localidad fuera de 01..20 (incl. 99 "Sin
      Localización"; en SIEDCO no hay 99, la regla es defensiva).

  NUSE
    - `cod_localidad` normalizado a string de 2 dígitos.
    - Se descarta cod=99 ("Sin Localización") — se reporta el % de incidentes.
    - Se descarta la fila basura cod='-0'.
    - Sumapaz (cod=20) se CONSERVA pero se marca como posible outlier (volumen
      muy bajo de llamadas).

Salidas:
  data/interim/siedco_clean.parquet
  data/interim/nuse_clean.parquet
  docs/data-dictionaries/reporte_calidad.md   (reporte de calidad por fuente)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

SIEDCO_IN = config.INTERIM / "siedco_delitos.parquet"
NUSE_IN = config.INTERIM / "nuse_incidentes.parquet"
SIEDCO_OUT = config.INTERIM / "siedco_clean.parquet"
NUSE_OUT = config.INTERIM / "nuse_clean.parquet"
REPORTE = config.DOCS_DICT / "reporte_calidad.md"

VALIDAS = {f"{i:02d}" for i in range(1, 21)}


def _norm_cod(serie: pd.Series) -> pd.Series:
    """Código de localidad como string de 2 dígitos con cero a la izquierda."""
    return serie.astype("string").str.strip().str.zfill(2)


def clean_siedco() -> tuple[pd.DataFrame, list[dict]]:
    df = pd.read_parquet(SIEDCO_IN)
    n0 = len(df)
    report = [{"fuente": "SIEDCO", "paso": "filas originales", "filas": n0, "razon": ""}]

    df["cod_localidad"] = _norm_cod(df["cod_localidad"])

    fuera = df[~df["cod_localidad"].isin(VALIDAS)]
    if len(fuera):
        report.append({"fuente": "SIEDCO", "paso": "descartar localidad fuera de 01..20",
                       "filas": -len(fuera),
                       "razon": f"códigos: {sorted(fuera['cod_localidad'].unique())}"})
    df = df[df["cod_localidad"].isin(VALIDAS)].copy()

    report.append({"fuente": "SIEDCO", "paso": "filas finales", "filas": len(df),
                   "razon": f"{df['tipo_delito'].nunique()} tipos de delito · "
                            f"{df['cod_localidad'].nunique()} localidades · "
                            f"{df['anio'].min()}–{df['anio'].max()}"})
    return df, report


def clean_nuse() -> tuple[pd.DataFrame, list[dict]]:
    df = pd.read_parquet(NUSE_IN)
    n0 = len(df)
    inc0 = int(df["cant_incidentes"].sum())
    report = [{"fuente": "NUSE", "paso": "filas originales", "filas": n0,
               "razon": f"{inc0:,} incidentes"}]

    df["cod_localidad"] = _norm_cod(df["cod_localidad"])

    # cod=99 "Sin Localización": se descarta y se reporta el % de incidentes.
    m99 = df["cod_localidad"] == "99"
    inc99 = int(df.loc[m99, "cant_incidentes"].sum())
    report.append({"fuente": "NUSE", "paso": "descartar cod=99 (Sin Localización)",
                   "filas": -int(m99.sum()),
                   "razon": f"{inc99:,} incidentes = {100*inc99/inc0:.2f}% del total sin localidad"})

    # Fila basura cod='-0' (queda '-0' tras zfill porque no es numérica limpia).
    mbasura = ~df["cod_localidad"].isin(VALIDAS) & ~m99
    if mbasura.any():
        report.append({"fuente": "NUSE", "paso": "descartar filas basura",
                       "filas": -int(mbasura.sum()),
                       "razon": f"códigos inválidos: {sorted(df.loc[mbasura,'cod_localidad'].unique())}"})

    df = df[df["cod_localidad"].isin(VALIDAS)].copy()

    # Sumapaz: se conserva, se marca como posible outlier (volumen muy bajo).
    inc_sumapaz = int(df.loc[df["cod_localidad"] == "20", "cant_incidentes"].sum())
    report.append({"fuente": "NUSE", "paso": "Sumapaz (20) CONSERVADO — posible outlier",
                   "filas": 0, "razon": f"solo {inc_sumapaz:,} incidentes en toda la serie"})

    report.append({"fuente": "NUSE", "paso": "filas finales", "filas": len(df),
                   "razon": f"{int(df['cant_incidentes'].sum()):,} incidentes · "
                            f"{df['cod_localidad'].nunique()} localidades · "
                            f"taxonomía NUSE ({df['tipo_incidente'].nunique()} tipos, "
                            f"separada de SIEDCO)"})
    return df, report


def _escribir_reporte(reportes: list[dict]) -> None:
    lines = ["# Reporte de calidad — limpieza consolidada (Issue #7)", "",
             "Generado por `src/data_cleaning.py`. Filas negativas = descartes.", "",
             "| Fuente | Paso | Δ filas | Razón |", "|---|---|---:|---|"]
    for r in reportes:
        lines.append(f"| {r['fuente']} | {r['paso']} | {r['filas']:+,} | {r['razon']} |")
    REPORTE.parent.mkdir(parents=True, exist_ok=True)
    REPORTE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> None:
    print("== #7 Limpieza consolidada ==")

    siedco, rep_s = clean_siedco()
    nuse, rep_n = clean_nuse()

    siedco.to_parquet(SIEDCO_OUT, index=False)
    nuse.to_parquet(NUSE_OUT, index=False)

    reportes = rep_s + rep_n
    _escribir_reporte(reportes)

    for r in reportes:
        print(f"  [{r['fuente']:6}] {r['paso']:42} {r['filas']:+9,}  {r['razon']}")
    print(f"  [ok] {SIEDCO_OUT.name}  ({len(siedco):,} filas)")
    print(f"  [ok] {NUSE_OUT.name}  ({len(nuse):,} filas)")
    print(f"  [ok] reporte: {REPORTE}")


if __name__ == "__main__":
    run()
