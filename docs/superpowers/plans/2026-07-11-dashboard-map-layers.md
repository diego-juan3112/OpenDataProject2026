# Dashboard Map Layers (Risk + NUSE + Typology) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Issue #32 mock with 3 real, togglable map layers
(risk coropleth, NUSE call density, K-Means typology), with a functional
year/tipo-de-delito selector, closing Issue #33's 3 acceptance criteria.

**Architecture:** A one-time generator reads real local pipeline outputs
(`dataset_analitico.parquet` #10, `zona_cluster.parquet` #27,
`nuse_incidentes.parquet` #4, `zonas_bogota.geojson` #5) and writes 4 small
committed JSON/GeoJSON fixtures under `app/data/` — geometry kept separate
from attributes so the year/tipo selector can slice real data at render
time. `app/data_loader.py` exposes 2 functions (`cargar_zonas_riesgo`,
`cargar_densidad_nuse`) that combine geometry + the selected slice into
GeoJSON. `app/streamlit_app.py` renders 3 Folium layers with a layer
control. The Issue #32 mock (`app/mock_data/`) is retired.

**Tech Stack:** Python, geopandas/pandas (generator only, root venv),
streamlit, folium, branca (already a folium dependency, no new install),
pytest.

## Global Constraints

- All 4 generated fixtures contain **real** data only — no fabrication (the
  Issue #19 predictive model still doesn't exist, so "risk" here means the
  real, already-computed `riesgo_alto` percentile-75 flag from Issue #10,
  never presented as a model probability).
- NUSE has no real UPZ geometry anywhere in the pipeline (verified) — the
  density layer aggregates to **localidad** level, using the same 20
  polygons as the other layers. This is a documented limitation, not a bug
  to silently fix by inventing geometry.
- NUSE aggregation excludes invalid locality codes `"99"` and `"-0"` (0.94%
  of raw rows) and fills missing `(localidad, año)` combinations with
  `conteo_nuse=0` (structural zero — verified real case: Sumapaz, 2018).
- Locality `"15"` (Antonio Nariño) gets the same mojibake correction as
  Issue #32's retired mock — applied only inside the generator script, never
  touching `src/`.
- Fixtures are JSON/GeoJSON (not parquet) so `app/requirements.txt` never
  needs `pandas`/`geopandas` at runtime — only the generator (run from the
  root venv) needs them.
- `cargar_zonas_riesgo(anio, tipo_delito)` in `app/data_loader.py` is the
  **only** function Issue #34 will change (swap its body for a real HTTP
  call to `GET /zonas-riesgo`) — it must match that future contract's shape.
  `cargar_densidad_nuse(anio)` is **not** part of that API contract (per
  `CLAUDE.md` §4, NUSE is a dashboard-only layer) and stays reading local
  files permanently — #34 does not touch it.
- `app/mock_data/` (Issue #32's generator + fixture) is deleted — nothing
  should reference it after this plan.
- Tests reading real data read only the real, git-committed fixtures under
  `app/data/` — never `data/` or `models/` (gitignored, don't exist in CI).

---

### Task 1: Real data generator (`app/data/generar_datasets_mapa.py`)

**Files:**
- Create: `app/data/generar_datasets_mapa.py`
- Create (by running the script): `app/data/geometria_localidades.geojson`,
  `app/data/riesgo_por_zona.json`, `app/data/tipologia_zonas.json`,
  `app/data/nuse_por_zona.json`

**Interfaces:**
- Consumes: `data/03_primary/dataset_analitico.parquet` (#10, real, local
  only), `models/clustering/zona_cluster.parquet` (#27, real, local only),
  `data/02_intermediate/nuse_incidentes.parquet` (#4, real, local only),
  `data/03_primary/zonas_bogota.geojson` (#5, real, local only, via
  `config.ZONAS_GEOJSON`). All 4 already exist in this working copy.
- Produces: the 4 files above, consumed by Task 2's `app/data_loader.py`.
  Verified exact shapes (real numbers, already confirmed by running this
  exact logic before writing this plan): `geometria_localidades.geojson` —
  20 features, ~49,600 bytes; `riesgo_por_zona.json` — 1760 rows (20
  localidades × 8 años × 11 tipos), 416 with `riesgo_alto=1`; 
  `tipologia_zonas.json` — 20 rows; `nuse_por_zona.json` — 160 rows (20 × 8
  años), 1 structural zero (`cod_localidad="20"`, `anio=2018`).

No unit test for this task — one-time data-generation script, same pattern
as `models/clustering/train.py` / `app/mock_data/generar_mock.py` (#32).
Verified by running it and inspecting real output.

- [ ] **Step 1: Write the script**

Create `app/data/generar_datasets_mapa.py`:

```python
"""
generar_datasets_mapa.py — Issue #33

Genera los 4 archivos de datos reales que consumen las 3 capas del mapa
(app/data_loader.py): geometria_localidades.geojson, riesgo_por_zona.json,
tipologia_zonas.json, nuse_por_zona.json. A diferencia del mock de la Issue
#32 (ya retirado), todos los valores aqui son REALES: riesgo_alto y
conteo_siedco vienen de dataset_analitico.parquet (#10), cluster/
nombre_perfil de zona_cluster.parquet (#27), y conteo_nuse de
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

OUT_DIR = Path(__file__).resolve().parent
GEOMETRIA_PATH = OUT_DIR / "geometria_localidades.geojson"
RIESGO_PATH = OUT_DIR / "riesgo_por_zona.json"
TIPOLOGIA_PATH = OUT_DIR / "tipologia_zonas.json"
NUSE_PATH = OUT_DIR / "nuse_por_zona.json"

ZONA_CLUSTER_PATH = config.ROOT / "models" / "clustering" / "zona_cluster.parquet"
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
    print("== #33 Generar datasets reales del mapa ==")
    _generar_geometria()
    _generar_riesgo()
    _generar_tipologia()
    _generar_nuse()
    print("\n  [ok] los 4 archivos de app/data/ estan listos")


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


def _generar_riesgo() -> None:
    df = pd.read_parquet(config.DATASET_ANALITICO)
    riesgo = df[["cod_localidad", "anio", "tipo_delito", "riesgo_alto", "conteo_siedco"]].copy()
    riesgo["anio"] = riesgo["anio"].astype(int)
    riesgo["riesgo_alto"] = riesgo["riesgo_alto"].astype(int)
    riesgo["conteo_siedco"] = riesgo["conteo_siedco"].astype(int)
    registros = riesgo.to_dict(orient="records")

    assert len(registros) == 1760, "esperadas 20 localidades x 8 anios x 11 tipos = 1760 filas"
    with open(RIESGO_PATH, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False)
    print(f"  riesgo_por_zona.json: {len(registros)} filas, "
          f"{sum(r['riesgo_alto'] for r in registros)} en riesgo alto, "
          f"{RIESGO_PATH.stat().st_size} bytes")


def _generar_tipologia() -> None:
    zc = pd.read_parquet(ZONA_CLUSTER_PATH)
    registros = zc[["cod_localidad", "cluster", "nombre_perfil"]].to_dict(orient="records")
    for fila in registros:
        fila["cluster"] = int(fila["cluster"])

    assert len(registros) == 20, "deben quedar exactamente 20 localidades"
    with open(TIPOLOGIA_PATH, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False)
    print(f"  tipologia_zonas.json: {len(registros)} localidades, {TIPOLOGIA_PATH.stat().st_size} bytes")


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


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Run the script and verify the real output**

Run: `.venv/Scripts/python app/data/generar_datasets_mapa.py`

Expected: no assertion errors, and printed output showing (these exact
numbers were verified by running this logic before writing this plan — they
should match, since the underlying real data hasn't changed):
- `geometria_localidades.geojson: 20 localidades, ~49600 bytes` (some
  variance in exact byte count is fine — it must NOT be anywhere near the
  full ~2.3MB unsimplified source)
- `riesgo_por_zona.json: 1760 filas, 416 en riesgo alto, ~176000 bytes`
- `tipologia_zonas.json: 20 localidades, ~1900 bytes`
- `nuse_por_zona.json: 160 filas, 1 en cero estructural:
  [{'cod_localidad': '20', 'anio': 2018, 'conteo_nuse': 0}], ~9800 bytes`
- ends with `[ok] los 4 archivos de app/data/ estan listos`

Then independently confirm the mojibake fix at the byte level (a terminal
`repr()` can itself mis-render UTF-8 on Windows — verifying raw bytes is the
only reliable check, same as Issue #32):

Run: `grep -o "ANTONIO[^\"]*" app/data/geometria_localidades.geojson | xxd | head -3`
Expected: the bytes after `NARI` are `c3 91` (UTF-8 for `Ñ`), followed by
`4f` (`O`) — i.e. `c3 91 4f` — not `ef bf bd` (U+FFFD replacement
character, meaning the fix did not apply).

- [ ] **Step 3: Commit**

```bash
git add app/data/generar_datasets_mapa.py app/data/geometria_localidades.geojson app/data/riesgo_por_zona.json app/data/tipologia_zonas.json app/data/nuse_por_zona.json
git commit -m "feat(dashboard): agrega generador de datasets reales del mapa (issue #33)"
```

---

### Task 2: `app/data_loader.py` (real risk + NUSE loaders)

**Files:**
- Modify: `app/data_loader.py` (full rewrite — replaces Issue #32's single
  mock-reading function)
- Modify: `tests/test_data_loader.py` (full rewrite — Issue #32's tests
  covered the retired mock function; these test the new real functions)

**Interfaces:**
- Consumes: `app/data/geometria_localidades.geojson`,
  `app/data/riesgo_por_zona.json`, `app/data/tipologia_zonas.json`,
  `app/data/nuse_por_zona.json` (Task 1, now committed).
- Produces: `cargar_zonas_riesgo(anio: int, tipo_delito: str) -> dict`
  (GeoJSON, properties include `riesgo_alto`, `conteo_siedco`, `cluster`,
  `nombre_perfil`) and `cargar_densidad_nuse(anio: int) -> dict` (GeoJSON,
  properties include `conteo_nuse`) — both consumed by Task 3's
  `app/streamlit_app.py`.

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `tests/test_data_loader.py`:

```python
"""Tests para data_loader (Issue #33): cargar_zonas_riesgo y
cargar_densidad_nuse.

A diferencia de la mayoria de tests del repo (que usan datos sinteticos),
estos leen los fixtures reales commiteados en app/data/ (generados por
app/data/generar_datasets_mapa.py, Issue #33) -- son seguros en CI porque,
a diferencia de data/, SI estan versionados en git.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from data_loader import cargar_zonas_riesgo, cargar_densidad_nuse


def test_cargar_zonas_riesgo_devuelve_20_localidades_con_riesgo_y_tipologia():
    geojson = cargar_zonas_riesgo(2025, "HP")

    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 20
    for feature in geojson["features"]:
        props = feature["properties"]
        assert props["riesgo_alto"] in (0, 1)
        assert isinstance(props["conteo_siedco"], int)
        assert props["nombre_perfil"] in {
            "Perfil de alto impacto generalizado",
            "Perfil hurto de bienes / ingreso alto",
            "Perfil de bajo incidente relativo",
        }


def test_cargar_zonas_riesgo_valores_reales_2025_hp():
    geojson = cargar_zonas_riesgo(2025, "HP")
    riesgo_por_localidad = {
        f["properties"]["cod_localidad"]: f["properties"]["riesgo_alto"]
        for f in geojson["features"]
    }

    # Kennedy (08), Engativa (10), Suba (11): las 3 unicas localidades en
    # riesgo alto para 2025/HP en el dato real (verificado corriendo el
    # generador contra dataset_analitico.parquet antes de escribir este test).
    assert riesgo_por_localidad["08"] == 1
    assert riesgo_por_localidad["10"] == 1
    assert riesgo_por_localidad["11"] == 1
    assert riesgo_por_localidad["01"] == 0
    assert sum(riesgo_por_localidad.values()) == 3


def test_cargar_zonas_riesgo_corrige_mojibake_antonio_narino():
    geojson = cargar_zonas_riesgo(2025, "HP")
    nombres = {f["properties"]["cod_localidad"]: f["properties"]["localidad_nombre"]
               for f in geojson["features"]}

    assert nombres["15"] == "ANTONIO NARIÑO"


def test_cargar_zonas_riesgo_combo_inexistente_lanza_value_error():
    with pytest.raises(ValueError):
        cargar_zonas_riesgo(2030, "HP")


def test_cargar_densidad_nuse_devuelve_20_localidades():
    geojson = cargar_densidad_nuse(2025)

    assert len(geojson["features"]) == 20
    for feature in geojson["features"]:
        assert isinstance(feature["properties"]["conteo_nuse"], int)
        assert feature["properties"]["conteo_nuse"] >= 0


def test_cargar_densidad_nuse_cero_estructural_sumapaz_2018():
    geojson = cargar_densidad_nuse(2018)
    conteo_sumapaz = next(
        f["properties"]["conteo_nuse"] for f in geojson["features"]
        if f["properties"]["cod_localidad"] == "20"
    )

    assert conteo_sumapaz == 0


def test_cargar_densidad_nuse_anio_inexistente_lanza_value_error():
    with pytest.raises(ValueError):
        cargar_densidad_nuse(2030)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_data_loader.py -v`
Expected: failures — `app/data_loader.py` still has Issue #32's
`cargar_zonas_riesgo()` with no arguments and no `cargar_densidad_nuse` at
all, so this will fail with a `TypeError` (wrong argument count) and/or
`ImportError`/`AttributeError` depending on collection order. Confirm the
failures are because the new functions/signatures don't exist yet, not for
an unrelated reason.

- [ ] **Step 3: Write the loader**

Replace the full contents of `app/data_loader.py`:

```python
"""
data_loader.py — Issue #33 (reemplaza la funcion de mock de la Issue #32)

Carga los datos de las 3 capas del mapa desde app/data/ (generado por
app/data/generar_datasets_mapa.py, Issue #33 -- todos los valores son
reales, ver ese script y el spec de #33 para el detalle). Combina la
geometria (que no cambia) con los atributos del anio/tipo de delito
seleccionados, en tiempo de render.

cargar_zonas_riesgo(anio, tipo_delito) tiene la misma forma que tendra el
contrato real de GET /zonas-riesgo (#20, ver CLAUDE.md ss4) -- es la UNICA
funcion que la Issue #34 reemplaza por una llamada HTTP real, ahora
parametrizada de verdad (en #32 no tomaba parametros porque el mock era
estatico).

cargar_densidad_nuse(anio) es local siempre: NUSE no forma parte del
contrato de /zonas-riesgo (CLAUDE.md la describe como una capa propia del
dashboard, no del endpoint unico), asi que la Issue #34 no la toca.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"
GEOMETRIA_PATH = DATA_DIR / "geometria_localidades.geojson"
RIESGO_PATH = DATA_DIR / "riesgo_por_zona.json"
TIPOLOGIA_PATH = DATA_DIR / "tipologia_zonas.json"
NUSE_PATH = DATA_DIR / "nuse_por_zona.json"


@st.cache_data
def _cargar_geometria() -> dict:
    with open(GEOMETRIA_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def _cargar_riesgo() -> list[dict]:
    with open(RIESGO_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def _cargar_tipologia() -> list[dict]:
    with open(TIPOLOGIA_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def _cargar_nuse_crudo() -> list[dict]:
    with open(NUSE_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def cargar_zonas_riesgo(anio: int, tipo_delito: str) -> dict:
    """GeoJSON de las 20 localidades con riesgo real (#10) y tipologia real
    (#27) para el anio y tipo de delito elegidos.

    Cada feature agrega, ademas de la geometria: riesgo_alto (0/1),
    conteo_siedco, cluster y nombre_perfil. Lanza ValueError si no hay dato
    para la combinacion (anio, tipo_delito) pedida.
    """
    geojson = _cargar_geometria()
    riesgo_por_localidad = {
        fila["cod_localidad"]: fila
        for fila in _cargar_riesgo()
        if fila["anio"] == anio and fila["tipo_delito"] == tipo_delito
    }
    if not riesgo_por_localidad:
        raise ValueError(f"No hay datos de riesgo para anio={anio!r}, tipo_delito={tipo_delito!r}.")

    tipologia_por_localidad = {fila["cod_localidad"]: fila for fila in _cargar_tipologia()}

    for feature in geojson["features"]:
        cod = feature["properties"]["cod_localidad"]
        riesgo = riesgo_por_localidad[cod]
        tipologia = tipologia_por_localidad[cod]
        feature["properties"]["riesgo_alto"] = riesgo["riesgo_alto"]
        feature["properties"]["conteo_siedco"] = riesgo["conteo_siedco"]
        feature["properties"]["cluster"] = tipologia["cluster"]
        feature["properties"]["nombre_perfil"] = tipologia["nombre_perfil"]

    return geojson


@st.cache_data
def cargar_densidad_nuse(anio: int) -> dict:
    """GeoJSON de las 20 localidades con conteo_nuse real (agregado desde
    UPZ a nivel localidad, ver limitacion documentada en el spec de #33)
    para el anio elegido.

    Lanza ValueError si no hay dato para ese anio.
    """
    geojson = _cargar_geometria()
    nuse_por_localidad = {
        fila["cod_localidad"]: fila["conteo_nuse"]
        for fila in _cargar_nuse_crudo()
        if fila["anio"] == anio
    }
    if not nuse_por_localidad:
        raise ValueError(f"No hay datos de NUSE para anio={anio!r}.")

    for feature in geojson["features"]:
        cod = feature["properties"]["cod_localidad"]
        feature["properties"]["conteo_nuse"] = nuse_por_localidad[cod]

    return geojson
```

Note: `_cargar_geometria()` is itself `@st.cache_data`-decorated, and both
public functions mutate the dict it returns (adding properties per feature)
before returning it. This is safe specifically because `st.cache_data`
returns a **copy** of the cached object on every call (that's the documented
difference from `st.cache_resource`, which does not copy) — so mutating the
dict inside `cargar_zonas_riesgo`/`cargar_densidad_nuse` never corrupts
`_cargar_geometria`'s cache for other callers. Do not add manual
`copy.deepcopy()` calls here — they would be redundant.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_data_loader.py -v`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add app/data_loader.py tests/test_data_loader.py
git commit -m "feat(dashboard): agrega cargar_zonas_riesgo y cargar_densidad_nuse reales (issue #33)"
```

---

### Task 3: 3-layer map, retire the Issue #32 mock, docs

**Files:**
- Modify: `app/streamlit_app.py` (full rewrite — 3 Folium layers + layer
  control, replaces Issue #32's single mock layer)
- Delete: `app/mock_data/generar_mock.py`, `app/mock_data/zonas_riesgo_mock.geojson`
- Modify: `app/README.md` (full rewrite — real layers instead of mock)
- Modify: `BACKLOG.md` (mark Issue #33's 3 acceptance criteria as complete)

**Interfaces:**
- Consumes: `cargar_zonas_riesgo(anio, tipo_delito) -> dict` and
  `cargar_densidad_nuse(anio) -> dict` from Task 2's `app/data_loader.py`.
- Produces: the running Streamlit app — no other task depends on this one.

- [ ] **Step 1: Delete the retired Issue #32 mock**

Delete these two files (and the now-empty `app/mock_data/` directory):
- `app/mock_data/generar_mock.py`
- `app/mock_data/zonas_riesgo_mock.geojson`

Confirm nothing else in the repo still imports or reads from
`app/mock_data/` (it shouldn't, after Task 2 rewrote `app/data_loader.py` —
but grep to be sure): run `grep -rn "mock_data" app/ tests/` and confirm no
matches remain.

- [ ] **Step 2: Write the Streamlit app**

Replace the full contents of `app/streamlit_app.py`:

```python
"""
streamlit_app.py — Issue #33 (reemplaza el mapa de un solo layer de la Issue #32)

Dashboard analitico de Alerta Ciudadana. 3 capas reales, togglables:
coropletico de riesgo (percentil historico, #10), densidad NUSE (agregada a
nivel localidad -- no existe geometria real de UPZ, ver app/README.md), y
tipologia de zonas (K-Means real, #27). La Issue #34 reemplaza
cargar_zonas_riesgo() por la API real GET /zonas-riesgo (#20);
cargar_densidad_nuse() se queda local para siempre (NUSE no forma parte del
contrato de esa API).
"""
from __future__ import annotations

import sys
from pathlib import Path

import branca.colormap as cm
import folium
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config

from data_loader import cargar_zonas_riesgo, cargar_densidad_nuse

# Cubre las 20 localidades reales (incluida la rural Sumapaz al sur),
# verificado contra data/03_primary/zonas_bogota.geojson:
# lon [-74.4498, -73.9865], lat [3.7310, 4.8368]
LIMITES_BOGOTA = [[3.7310, -74.4498], [4.8368, -73.9865]]

COLOR_RIESGO = {1: "#e74c3c", 0: "#2ecc71"}
COLOR_TIPOLOGIA = {
    "Perfil de alto impacto generalizado": "#c0392b",
    "Perfil hurto de bienes / ingreso alto": "#f39c12",
    "Perfil de bajo incidente relativo": "#27ae60",
}


def _estilo_riesgo(feature: dict) -> dict:
    riesgo_alto = feature["properties"]["riesgo_alto"]
    return {"fillColor": COLOR_RIESGO[riesgo_alto], "color": "#555555", "weight": 1, "fillOpacity": 0.6}


def _estilo_tipologia(feature: dict) -> dict:
    perfil = feature["properties"]["nombre_perfil"]
    return {"fillColor": COLOR_TIPOLOGIA.get(perfil, "#95a5a6"), "color": "#555555", "weight": 1, "fillOpacity": 0.6}


def main() -> None:
    st.set_page_config(page_title="Alerta Ciudadana", layout="wide")
    st.title("Alerta Ciudadana — Mapa de riesgo por zona")

    with st.sidebar:
        st.header("Controles")
        tipo_nombre = st.selectbox("Tipo de delito", options=list(config.SIEDCO_TIPOS.values()), index=2)
        tipo_codigo = next(codigo for codigo, nombre in config.SIEDCO_TIPOS.items() if nombre == tipo_nombre)
        anio = st.select_slider(
            "Año", options=list(range(config.ANIO_MIN, config.ANIO_MAX + 1)), value=config.ANIO_MAX
        )
        st.caption(
            "El coroplético de riesgo usa un umbral histórico (percentil 75 "
            "de incidentes), no el modelo predictivo real — se conecta a la "
            "API real en la Issue #34."
        )

    zonas_riesgo = cargar_zonas_riesgo(anio, tipo_codigo)
    densidad_nuse = cargar_densidad_nuse(anio)

    mapa = folium.Map()
    mapa.fit_bounds(LIMITES_BOGOTA)

    folium.GeoJson(
        zonas_riesgo,
        name="Riesgo por zona",
        style_function=_estilo_riesgo,
        tooltip=folium.GeoJsonTooltip(
            fields=["localidad_nombre", "riesgo_alto", "conteo_siedco"],
            aliases=["Localidad", "¿Riesgo alto?", "Incidentes registrados"],
        ),
        show=True,
    ).add_to(mapa)

    conteos_nuse = [f["properties"]["conteo_nuse"] for f in densidad_nuse["features"]]
    colormap = cm.LinearColormap(
        colors=["#fff5cc", "#e67e22", "#7b241c"], vmin=min(conteos_nuse), vmax=max(conteos_nuse)
    )
    colormap.caption = "Llamadas al 123 (agregado por localidad)"
    folium.GeoJson(
        densidad_nuse,
        name="Densidad NUSE (por localidad)",
        style_function=lambda feature: {
            "fillColor": colormap(feature["properties"]["conteo_nuse"]),
            "color": "#555555",
            "weight": 1,
            "fillOpacity": 0.7,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["localidad_nombre", "conteo_nuse"],
            aliases=["Localidad", "Llamadas al 123"],
        ),
        show=False,
    ).add_to(mapa)
    colormap.add_to(mapa)

    folium.GeoJson(
        zonas_riesgo,
        name="Tipología de zonas",
        style_function=_estilo_tipologia,
        tooltip=folium.GeoJsonTooltip(
            fields=["localidad_nombre", "nombre_perfil"],
            aliases=["Localidad", "Perfil"],
        ),
        show=False,
    ).add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)
    st_folium(mapa, height=600)


if __name__ == "__main__":
    main()
```

Note: `branca.colormap` is already installed as a dependency of `folium`
(confirmed: `branca==0.8.2` present in this venv after Issue #32's `pip
install folium`) — no new entry needed in `app/requirements.txt`.

- [ ] **Step 3: Smoke-test the app boots**

Same caveat as Issue #32: no browser tool available, so this only confirms
the app **boots without crashing**, not that it looks right. Visual
confirmation is the repo owner's job (see the Final Checklist).

Run (background, headless, then check its output before killing it):

```bash
.venv/Scripts/streamlit run app/streamlit_app.py --server.headless true --server.port 8501
```

Expected within a few seconds: `You can now view your Streamlit app in your
browser.` and a `Local URL: http://localhost:8501` line, with **no Python
traceback**. Then:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
```

Expected: `200`. Stop the background Streamlit process afterward — it must
not be left running when you finish the task.

- [ ] **Step 4: Write `app/README.md`**

Replace the full contents of `app/README.md`:

```markdown
# app/ — Dashboard Streamlit (Integrante 3)

Panel donde se exploran los resultados del análisis: mapa de riesgo por
zona, densidad de llamadas NUSE, y tipología de zonas por perfil delictivo.
El reporte ciudadano simulado con detección de anomalías por z-score llega
en la Issue #36.

## Cómo correr

```bash
.venv/Scripts/pip install -r app/requirements.txt
.venv/Scripts/streamlit run app/streamlit_app.py
```

Abre <http://localhost:8501>.

## Las 3 capas del mapa (Issue #33)

Los datos de las 3 capas son **reales**, no un mock (a diferencia del
scaffold inicial de la Issue #32, ya retirado — `app/mock_data/` no existe
más):

1. **Riesgo por zona**: colorea cada localidad según `riesgo_alto`
   (percentil 75 histórico de `conteo_siedco`, calculado en la Issue #10 —
   **no** es la probabilidad del modelo predictivo real, Issue #19, que
   Integrante 2 aún no ha implementado). El selector de año/tipo de delito
   del sidebar sí funciona: cambia de verdad el coroplético.
2. **Densidad NUSE**: llamadas al 123 por localidad, coloreadas con una
   escala continua. *Limitación conocida:* el dato abierto real trae
   resolución de UPZ (más fina que localidad), pero el pipeline nunca
   ingirió la geometría de esas UPZ (solo la de localidad, Issue #5) — la
   capa muestra el agregado a nivel localidad. Ingerir geometría real de UPZ
   queda como trabajo futuro para Integrante 1.
3. **Tipología de zonas**: colorea por el perfil de K-Means real (Issue
   #27), con tooltip en lenguaje no técnico.

Activa/desactiva capas con el control en la esquina superior derecha del
mapa.

## Datos: `app/data/`

Los 4 archivos en `app/data/*.json`/`*.geojson` están **commiteados** (a
diferencia de `data/`, que es gitignored) para que cualquiera del equipo
corra el dashboard sin haber corrido el pipeline completo. Se generaron una
sola vez con datos reales:

```bash
.venv/Scripts/python app/data/generar_datasets_mapa.py
```

(Requiere haber corrido `pipelines/pipeline_ml.py` y
`models/clustering/train.py` localmente — este script sí necesita
`pandas`/`geopandas`, vía el `requirements.txt` raíz del repo, no el de
`app/`. Solo hace falta regenerarlo si cambian los datos o el clustering
reales.)

La Issue #34 reemplaza `cargar_zonas_riesgo()` (en `app/data_loader.py`) por
una llamada real a `GET /zonas-riesgo` (Issue #20) — `cargar_densidad_nuse()`
se queda local para siempre, porque NUSE no forma parte del contrato de esa
API (ver `CLAUDE.md` §4).
```

- [ ] **Step 5: Run the full test suite to confirm no regressions**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests pass (26 pre-existing minus the 4 retired Issue #32
`test_data_loader.py` tests, plus the 7 new ones from Task 2 = 29).

- [ ] **Step 6: Mark Issue #33 complete in BACKLOG.md**

In `BACKLOG.md`, find the section `### [CLUST] #33 — Capas del mapa:
coroplético de riesgo + puntos NUSE + tipología` (around line 653) and
change its 3 acceptance criteria from `- [ ]` to `- [x]`:

```diff
 **Criterios de aceptación:**
-- [ ] Coroplético colorea las localidades por riesgo, con selector de año/tipo de delito y leyenda + tooltip por localidad.
-- [ ] Capa de densidad NUSE activable, coloreada por volumen de llamadas por localidad/UPZ (sin puntos, porque el dato es agregado).
-- [ ] Capa de tipología que colorea las zonas por cluster con la etiqueta de perfil (#27) y tooltip en lenguaje no técnico.
+- [x] Coroplético colorea las localidades por riesgo, con selector de año/tipo de delito y leyenda + tooltip por localidad.
+- [x] Capa de densidad NUSE activable, coloreada por volumen de llamadas por localidad/UPZ (sin puntos, porque el dato es agregado).
+- [x] Capa de tipología que colorea las zonas por cluster con la etiqueta de perfil (#27) y tooltip en lenguaje no técnico.
```

Do not touch any other line or any other issue's checkboxes in this file.

- [ ] **Step 7: Commit**

```bash
git add app/streamlit_app.py app/README.md BACKLOG.md
git rm app/mock_data/generar_mock.py app/mock_data/zonas_riesgo_mock.geojson
git commit -m "feat(dashboard): agrega 3 capas reales del mapa y retira el mock de #32 (issue #33)"
```

---

## Final Checklist

- [ ] The 3 acceptance criteria of Issue #33 (risk coropleth with working
  year/tipo selector + legend/tooltip, togglable NUSE density layer,
  typology layer with plain-language tooltip) are satisfied.
- [ ] `pytest tests/ -v` passes completely (29/29).
- [ ] `python -m compileall src pipelines tests` (what CI runs) does not
  fail. `app/` remains intentionally outside this invocation, same decision
  as Issue #32.
- [ ] `BACKLOG.md` reflects Issue #33 as complete.
- [ ] `app/mock_data/` no longer exists; nothing references it.
- [ ] No background `streamlit run` process was left running after Task 3
  Step 3.
- [ ] The repo owner does a final manual `streamlit run app/streamlit_app.py`
  and confirms visually in a browser that all 3 layers look right and the
  layer control / sidebar selectors actually change the map — the smoke
  test in Task 3 only confirms the server boots and answers HTTP 200.
