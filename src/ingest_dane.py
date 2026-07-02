"""
ingest_dane.py — Issue #6

Contexto socioeconómico por localidad (features de fondo para el predictivo y el
clustering). Dos variables, ambas AGREGADAS a nivel zona — cero microdatos
personales (Regla 3):

  - `poblacion`  : población proyectada por (localidad × año), Observatorio SDP
                   (base Censo DANE 2018), 2005–2035. Se agrega desde el CSV
                   desagregado por sexo/edad.
  - `ipm_pct`    : incidencia de pobreza multidimensional = personas pobres por
                   el IPM (Censo DANE 2018) / población 2018 de la localidad.
                   El dato de origen es un CONTEO de personas; se convierte a
                   tasa para que sea comparable entre localidades de tamaños muy
                   distintos. Variable estructural: se difunde (estática) a todos
                   los años del dataset analítico.

Fuentes (portal de datos abiertos de Bogotá, CKAN):
  - Población: dataset piramide-poblacional-bogota-d-c (CSV por localidad).
  - IPM      : dataset habitat-en-cifras-... (XLSX), indicador
               "Personas pobres por el índice de Pobreza Multidimensional - IPM
               Censo" (año 2018, 19 localidades; Sumapaz no está en la Encuesta
               Multipropósito → IPM queda nulo y se documenta).

El IPM viene por NOMBRE de localidad (la fuente no trae código). Se mapea a
`cod_localidad` con un diccionario explícito nombre-normalizado → código y se
valida que las 19 localidades mapeen; si alguna no mapea, el script falla en vez
de cruzar por texto libre (Regla 1).

Salida: data/interim/dane_contexto.parquet  (una fila por localidad × año).
"""

from __future__ import annotations

import io
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import utils

OUT = config.INTERIM / "dane_contexto.parquet"

POBLACION_CSV = config.RAW_DANE / "osb_demografia-poblacion-localidad.csv"
HABITAT_XLSX = config.RAW_DANE / "indicadores-calidad-de-vida-localidades.xlsx"

# Diccionario oficial nombre-normalizado -> código de localidad (01..20).
# Normalización = sin tildes, mayúsculas, espacios colapsados (ver _norm).
NOMBRE_A_CODIGO = {
    "USAQUEN": "01",
    "CHAPINERO": "02",
    "SANTA FE": "03",
    "SAN CRISTOBAL": "04",
    "USME": "05",
    "TUNJUELITO": "06",
    "BOSA": "07",
    "KENNEDY": "08",
    "FONTIBON": "09",
    "ENGATIVA": "10",
    "SUBA": "11",
    "BARRIOS UNIDOS": "12",
    "TEUSAQUILLO": "13",
    "LOS MARTIRES": "14",
    "ANTONIO NARINO": "15",
    "PUENTE ARANDA": "16",
    "LA CANDELARIA": "17",
    "RAFAEL URIBE URIBE": "18",
    "CIUDAD BOLIVAR": "19",
    "SUMAPAZ": "20",
}


def _norm(s: str) -> str:
    """Normaliza un nombre de localidad: sin tildes, mayúsculas, espacios simples."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.upper().split())


def _load_poblacion(force: bool) -> pd.DataFrame:
    """Población total por (cod_localidad × año) en la ventana ANIO_MIN..ANIO_MAX."""
    utils.download(config.DANE_POBLACION_CSV_URL, POBLACION_CSV, force=force)
    df = pd.read_csv(POBLACION_CSV, sep=";", encoding="utf-8")

    # CODIGO_LOCALIDAD = 0 es el total de Bogotá; se descarta (no es una zona).
    df = df[df["CODIGO_LOCALIDAD"] != 0].copy()
    df["cod_localidad"] = df["CODIGO_LOCALIDAD"].astype(int).astype(str).str.zfill(2)
    df = df.rename(columns={"ANO": "anio"})

    pob = (
        df.groupby(["cod_localidad", "anio"], as_index=False)["POBLACION"]
        .sum()
        .rename(columns={"POBLACION": "poblacion"})
    )
    pob = pob[pob["anio"].between(config.ANIO_MIN, config.ANIO_MAX)].copy()
    pob["poblacion"] = pob["poblacion"].astype("int64")
    return pob


def _load_ipm(force: bool) -> pd.DataFrame:
    """Personas pobres por IPM (Censo 2018) por cod_localidad. Mapea nombre→código."""
    utils.download(config.DANE_HABITAT_XLSX_URL, HABITAT_XLSX, force=force)
    raw = HABITAT_XLSX.read_bytes()
    df = pd.read_excel(io.BytesIO(raw))
    df.columns = ["categoria", "indicador", "anio", "localidad", "valor", "fuente"]

    ipm = df[df["indicador"].str.contains("IPM", na=False)].copy()
    if ipm.empty:
        raise RuntimeError(
            "No encuentro el indicador de IPM en el XLSX de Hábitat en cifras. "
            "Revisar si cambió el nombre del indicador en la fuente."
        )
    ipm["cod_localidad"] = ipm["localidad"].map(lambda n: NOMBRE_A_CODIGO.get(_norm(n)))

    sin_match = ipm.loc[ipm["cod_localidad"].isna(), "localidad"].unique().tolist()
    if sin_match:
        raise RuntimeError(
            f"Localidades del IPM que no mapean a código (revisar NOMBRE_A_CODIGO): {sin_match}"
        )

    ipm = ipm[["cod_localidad", "valor"]].rename(columns={"valor": "personas_pobres_ipm"})
    ipm["personas_pobres_ipm"] = ipm["personas_pobres_ipm"].astype(float)
    print(f"  IPM: {len(ipm)} localidades (Censo 2018). "
          f"Faltantes vs 20: {sorted(set(NOMBRE_A_CODIGO.values()) - set(ipm['cod_localidad']))}")
    return ipm


def run(force: bool = False) -> pd.DataFrame:
    config.ensure_dirs()
    print("== #6 Contexto socioeconómico DANE/SDP ==")

    pob = _load_poblacion(force)
    ipm = _load_ipm(force)

    # Incidencia IPM = personas pobres (Censo 2018) / población de 2018 (misma base).
    pob_2018 = pob[pob["anio"] == config.IPM_ANIO_BASE][["cod_localidad", "poblacion"]]
    pob_2018 = pob_2018.rename(columns={"poblacion": "_pob_2018"})
    ipm = ipm.merge(pob_2018, on="cod_localidad", how="left")
    ipm["ipm_pct"] = 100.0 * ipm["personas_pobres_ipm"] / ipm["_pob_2018"]
    ipm = ipm.drop(columns="_pob_2018")

    # Variable estructural: se difunde (estática, base 2018) a todos los años.
    ctx = pob.merge(ipm, on="cod_localidad", how="left")
    ctx = ctx.sort_values(["cod_localidad", "anio"]).reset_index(drop=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    ctx.to_parquet(OUT, index=False)

    # ---- Verificación ----
    print(f"  filas: {len(ctx)}  (esperado 20 loc × {config.ANIO_MAX - config.ANIO_MIN + 1} años = "
          f"{20 * (config.ANIO_MAX - config.ANIO_MIN + 1)})")
    print(f"  localidades: {ctx['cod_localidad'].nunique()} | años: "
          f"{ctx['anio'].min()}–{ctx['anio'].max()}")
    print(f"  población total Bogotá 2024: {ctx.loc[ctx.anio == 2024, 'poblacion'].sum():,}")
    faltan_ipm = ctx.loc[ctx["ipm_pct"].isna(), "cod_localidad"].unique().tolist()
    print(f"  IPM nulo en (documentado): {faltan_ipm}")
    print(f"  ipm_pct rango: {ctx['ipm_pct'].min():.1f}%–{ctx['ipm_pct'].max():.1f}%")
    print(f"  [ok] guardado: {OUT}")
    return ctx


if __name__ == "__main__":
    run(force="--force" in sys.argv)
