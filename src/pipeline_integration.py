"""
join_sources.py — Issue #8

Cruce por CÓDIGO de localidad (2 dígitos), nunca por nombre (Regla 1). Todas las
uniones son TABULARES: NUSE no tiene lat/lon por incidente, así que no hay spatial
join que hacer (el spatial join solo aplicaría con coordenadas puntuales).

Arquitectura del cruce:

  SIEDCO (spine)  ──  grano (cod_localidad × anio × tipo_delito), 1.760 filas.
        │  left join por (cod_localidad, anio)
  NUSE (anual)    ──  llamadas Línea 123 agregadas mes→año por localidad. Es una
        │             señal de zona-año (taxonomía propia); se difunde a cada
        │             tipo_delito de esa localidad-año como feature de contexto.
        │  left join por (cod_localidad, anio)
  DANE contexto   ──  poblacion (por año) + ipm_pct (Censo 2018, estático).
        ▼
  tabla analítica (cod_localidad × anio × tipo_delito)

La geometría (localidades.geojson, EPSG:4326) se adjunta aparte para el
`zonas_bogota.geojson`; el nombre canónico de localidad sale de la geometría
(los nombres de SIEDCO traen mojibake latin-1 → no se usan como referencia).

Expone:
  - `tabla_analitica()`  -> DataFrame (cod_localidad × anio × tipo_delito)
  - `tabla_zonas()`      -> GeoDataFrame de 20 polígonos (EPSG:4326)
  - `run()`              -> ejecuta los cruces y valida (sin escribir salidas
                            finales; eso es Issue #9 / build_dataset.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

SIEDCO_CLEAN = config.INTERIM / "siedco_clean.parquet"
NUSE_CLEAN = config.INTERIM / "nuse_clean.parquet"
DANE_CTX = config.INTERIM / "dane_contexto.parquet"
ZONAS_GEO = config.INTERIM / "localidades.geojson"

VALIDAS = {f"{i:02d}" for i in range(1, 21)}


def _nombres_canonicos() -> pd.DataFrame:
    """cod_localidad -> localidad_nombre canónico (desde la geometría, sin mojibake)."""
    g = gpd.read_file(ZONAS_GEO)
    return g[["cod_localidad", "localidad_nombre"]].drop_duplicates()


def _nuse_anual() -> pd.DataFrame:
    """NUSE limpio agregado mes→año: conteo_nuse por (cod_localidad, anio)."""
    n = pd.read_parquet(NUSE_CLEAN)
    out = (
        n.groupby(["cod_localidad", "anio"], as_index=False)["cant_incidentes"]
        .sum()
        .rename(columns={"cant_incidentes": "conteo_nuse"})
    )
    out["anio"] = out["anio"].astype("int64")
    out["conteo_nuse"] = out["conteo_nuse"].astype("int64")
    return out


def tabla_analitica() -> pd.DataFrame:
    """Tabla cruzada a nivel (cod_localidad × anio × tipo_delito)."""
    siedco = pd.read_parquet(SIEDCO_CLEAN)
    # El nombre de SIEDCO trae mojibake latin-1 → se descarta; el nombre canónico
    # viene de la geometría (_nombres_canonicos).
    siedco = siedco.drop(columns=[c for c in ["localidad_nombre"] if c in siedco.columns])
    siedco = siedco.rename(columns={"cod_delito": "tipo_delito",
                                    "tipo_delito": "tipo_delito_nombre",
                                    "conteo": "conteo_siedco"})

    nuse = _nuse_anual()
    dane = pd.read_parquet(DANE_CTX)
    nombres = _nombres_canonicos()

    df = siedco.merge(nombres, on="cod_localidad", how="left", validate="many_to_one")
    df = df.merge(nuse, on=["cod_localidad", "anio"], how="left", validate="many_to_one")
    df = df.merge(dane, on=["cod_localidad", "anio"], how="left", validate="many_to_one")

    # Cero estructural: una localidad-año ausente en NUSE = 0 incidentes registrados
    # (p. ej. Sumapaz 2018, sin llamadas Línea 123 ese año). No es dato faltante.
    df["conteo_nuse"] = df["conteo_nuse"].fillna(0).astype("int64")

    cols = ["cod_localidad", "localidad_nombre", "anio", "tipo_delito",
            "tipo_delito_nombre", "conteo_siedco", "conteo_nuse",
            "poblacion", "ipm_pct"]
    df = df[cols].sort_values(["cod_localidad", "anio", "tipo_delito"]).reset_index(drop=True)
    return df


def tabla_zonas() -> gpd.GeoDataFrame:
    """20 polígonos de localidad en EPSG:4326, con la llave y los códigos."""
    g = gpd.read_file(ZONAS_GEO)
    if g.crs is None or g.crs.to_epsg() != 4326:
        raise RuntimeError(f"CRS inesperado en zonas: {g.crs} (se requiere EPSG:4326)")
    g["cod_localidad"] = g["cod_localidad"].astype("string").str.strip().str.zfill(2)
    return g[["cod_localidad", "localidad_nombre", "cod_dane_mpio", "geometry"]]


def run() -> pd.DataFrame:
    print("== #8 Cruce por código de localidad ==")
    df = tabla_analitica()
    zonas = tabla_zonas()

    # --- Validaciones del cruce ---
    def locs(x):
        return set(x["cod_localidad"].unique())

    siedco = pd.read_parquet(SIEDCO_CLEAN)
    nuse = _nuse_anual()
    dane = pd.read_parquet(DANE_CTX)

    conjuntos = {
        "SIEDCO": locs(siedco), "NUSE": locs(nuse),
        "DANE": locs(dane), "geometría": set(zonas["cod_localidad"]),
    }
    for nombre, s in conjuntos.items():
        print(f"  localidades {nombre:9}: {len(s)}  {'OK' if s == VALIDAS else 'DISTINTO'}")
    if any(s != VALIDAS for s in conjuntos.values()):
        raise RuntimeError(f"Alguna fuente no tiene exactamente las 20 localidades: "
                           f"{ {k: sorted(v) for k, v in conjuntos.items()} }")

    # Sin pérdida de filas no justificada: la spine SIEDCO se conserva 1:1.
    assert len(df) == len(siedco), f"pérdida de filas en el cruce: {len(siedco)} -> {len(df)}"

    # Ceros estructurales NUSE: localidad-año sin llamadas Línea 123 (Sumapaz 2018).
    nuse_zero = _nuse_anual()
    combos_nuse = set(zip(nuse_zero["cod_localidad"], nuse_zero["anio"].astype(int)))
    combos_full = {(f"{i:02d}", y) for i in range(1, 21)
                   for y in range(config.ANIO_MIN, config.ANIO_MAX + 1)}
    ceros_nuse = sorted(combos_full - combos_nuse)

    n_sin_pob = int(df["poblacion"].isna().sum())
    sin_ipm = sorted(df.loc[df["ipm_pct"].isna(), "cod_localidad"].unique())
    print(f"  filas dataset: {len(df)}  (= filas SIEDCO, sin pérdida)")
    print(f"  NUSE ceros estructurales (localidad-año sin llamadas): {ceros_nuse}")
    print(f"  filas sin población: {n_sin_pob}")
    print(f"  IPM nulo (documentado, Sumapaz sin EM): {sin_ipm}")
    assert n_sin_pob == 0, "hueco inesperado en población (debe cubrir 20×años)"

    # % NUSE fuera por cod=99 (re-reportado desde el crudo, ver Issue #7).
    n_raw = pd.read_parquet(config.INTERIM / "nuse_incidentes.parquet")
    inc_tot = int(n_raw["cant_incidentes"].sum())
    inc_99 = int(n_raw.loc[n_raw["cod_localidad"].astype("string").str.zfill(2) == "99",
                           "cant_incidentes"].sum())
    print(f"  NUSE incidentes sin localidad (cod=99) fuera del cruce: "
          f"{inc_99:,} = {100*inc_99/inc_tot:.2f}%")

    print(f"  CRS geometría verificado: {zonas.crs} | polígonos: {len(zonas)}")
    print("  [ok] cruce validado")
    return df


if __name__ == "__main__":
    run()
