# Dashboard Scaffold + Mock `/zonas-riesgo` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `app/`, the Streamlit dashboard, with a base Folium map of
Bogotá driven by a mock of `GET /zonas-riesgo` (#20 doesn't exist yet), so
Issue #32's 3 acceptance criteria are met and #33/#36 can build on it without
waiting for Integrante 2's predictivo/API work.

**Architecture:** A one-time mock-generation script combines **real**
geometry (#5) and **real** cluster typology (#27) with a **fake** risk field
(derived from the real cluster, since the predictivo #19 doesn't exist yet),
serialized to a small committed GeoJSON fixture. A thin `data_loader.py`
reads that fixture behind a stable function signature that #34 will later
swap for a real HTTP call. `streamlit_app.py` renders it on a Folium map
inside a minimal sidebar+map layout.

**Tech Stack:** Python, geopandas/pandas (mock generation only, root venv),
streamlit, folium, streamlit-folium (the dashboard itself), pytest.

## Global Constraints

- The mock's geometry and cluster/perfil fields are **real** data (from
  `data/03_primary/zonas_bogota.geojson` #5 and
  `models/clustering/zona_cluster.parquet` #27); only `nivel_riesgo` /
  `probabilidad_riesgo` / `anio` / `tipo_delito` are fabricated, and this is
  documented in the generator script's docstring — never presented as if it
  came from the real predictivo model.
- The mock fixture (`app/mock_data/zonas_riesgo_mock.geojson`) is **committed
  to git** (unlike `data/`, which is gitignored) so any teammate can run the
  dashboard without the data pipeline.
- Geometry is simplified (`tolerance=0.001`, `preserve_topology=True`) before
  being written to the fixture — verified locally: this shrinks the file from
  ~2.3 MB (full precision) to ~50 KB while keeping all 20 zones as valid
  single `Polygon`s. Do not skip this — an uncompressed fixture is
  impractical to commit and review.
- The mock corrects one pre-existing data bug: locality `"15"` (Antonio
  Nariño) arrives from the real `zonas_bogota.geojson` with a mangled name
  (`"ANTONIO NARI�O"`, an irreversible Unicode replacement character —
  verified by inspecting the raw bytes of the real file). This is fixed
  **only** inside `app/mock_data/generar_mock.py` via a documented
  correction dict — do **not** touch `src/` or the real pipeline; that bug
  belongs to Integrante 1's `ingest_divipola.py`/`data_cleaning.py`
  (out of scope for #32).
- `app/data_loader.py`'s `cargar_zonas_riesgo()` is the **only** function
  #34 needs to change (swap its body for a real HTTP call) — keep the rest
  of `streamlit_app.py` decoupled from where the data comes from.
- `app/requirements.txt` is separate from the root `requirements.txt`
  (root is the data pipeline's dependencies, Integrante 1's concern).
- Tests that don't need the real mock fixture use synthetic data; the one
  exception (`tests/test_data_loader.py`) reads the **real, committed** mock
  fixture directly, which is safe in CI because (unlike `data/`) it's
  versioned in git.

---

### Task 1: Mock fixture generator

**Files:**
- Create: `app/mock_data/generar_mock.py`
- Create (by running the script): `app/mock_data/zonas_riesgo_mock.geojson`

**Interfaces:**
- Consumes: `data/03_primary/zonas_bogota.geojson` (#5, real, local only —
  not in git) and `models/clustering/zona_cluster.parquet` (#27, real, local
  only — not in git). Both already exist in this working copy (the pipeline
  and clustering training have already been run locally).
- Produces: `app/mock_data/zonas_riesgo_mock.geojson`, a `FeatureCollection`
  of 20 `Polygon` features (EPSG:4326), each with properties
  `cod_localidad, localidad_nombre, cod_dane_mpio, cluster, nombre_perfil,
  nivel_riesgo, probabilidad_riesgo, anio, tipo_delito` — consumed by Task 2's
  `app/data_loader.py`.

No unit test for this task — it's a one-time data-generation script (same
pattern as `models/clustering/train.py`/`build_features.py`, which also have
no dedicated test file). Verified by running it and inspecting real output.

- [ ] **Step 1: Write the script**

Create `app/mock_data/generar_mock.py`:

```python
"""
generar_mock.py — Issue #32

Genera app/mock_data/zonas_riesgo_mock.geojson: un GeoJSON con la forma que
tendra GET /zonas-riesgo (#20, Integrante 2, aun no implementado), para que
el dashboard (#32) se pueda construir sin esperar a la API real.

Combina:
- Geometria + identidad REALES de data/03_primary/zonas_bogota.geojson (#5),
  simplificada (tolerancia 0.001 grados, ~100m) para que el fixture sea
  liviano y commiteable (el original pesa ~2.3 MB; simplificado, ~50 KB).
- Cluster + perfil REALES de models/clustering/zona_cluster.parquet (#27).
- Riesgo FALSO (nivel_riesgo, probabilidad_riesgo): el predictivo (#19,
  Integrante 2) no existe todavia. Se deriva del perfil de cluster REAL
  (alto impacto -> alto, hurto de bienes -> medio, bajo incidente -> bajo)
  mas un jitter deterministico (semilla fija = reproducible) para que no
  sea un unico valor repetido por perfil. NO es una prediccion real -- #34
  reemplaza esto por la respuesta real de GET /zonas-riesgo.
- Metadatos de consulta fijos (anio=2025, tipo_delito="HP"): la variacion
  por parametro es responsabilidad de #34, no de este scaffold.

Corrige tambien un bug de datos preexistente en el pipeline real (#5): la
localidad 15 llega con el nombre mal codificado ("ANTONIO NARI(replacement)O",
caracter de reemplazo Unicode irreversible -- verificado inspeccionando los
bytes crudos del geojson real). Se corrige SOLO en este fixture, documentado
aqui; el pipeline real de Integrante 1 sigue con el bug (fuera de alcance).

Uso:
    python app/mock_data/generar_mock.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
import config

OUT_PATH = Path(__file__).resolve().parent / "zonas_riesgo_mock.geojson"
ZONA_CLUSTER_PATH = config.ROOT / "models" / "clustering" / "zona_cluster.parquet"

TOLERANCIA_SIMPLIFICACION = 0.001  # ~100m, preserva la forma a escala de mapa web

CORRECCIONES_NOMBRE = {
    # Bug preexistente en zonas_bogota.geojson (#5): la localidad 15 llega con
    # caracter de reemplazo Unicode (U+FFFD), irreversible en el pipeline real.
    # Se corrige solo aqui -- no se toca src/ (fuera de alcance de #32).
    "15": "ANTONIO NARIÑO",
}

NIVEL_POR_PERFIL = {
    "Perfil de alto impacto generalizado": "alto",
    "Perfil hurto de bienes / ingreso alto": "medio",
    "Perfil de bajo incidente relativo": "bajo",
}
BASE_POR_NIVEL = {"alto": 0.8, "medio": 0.5, "bajo": 0.2}
SEMILLA_JITTER = 42
ANIO_MOCK = 2025
TIPO_DELITO_MOCK = "HP"  # Hurto Personas (ver src/config.py::SIEDCO_TIPOS)


def run() -> None:
    print("== #32 Generar mock de zonas-riesgo ==")
    gdf = gpd.read_file(config.ZONAS_GEOJSON)
    zona_cluster = pd.read_parquet(ZONA_CLUSTER_PATH)

    gdf = gdf.merge(zona_cluster[["cod_localidad", "cluster", "nombre_perfil"]],
                     on="cod_localidad", how="left")
    gdf = gdf.sort_values("cod_localidad").reset_index(drop=True)

    gdf["localidad_nombre"] = gdf.apply(
        lambda fila: CORRECCIONES_NOMBRE.get(fila["cod_localidad"], fila["localidad_nombre"]),
        axis=1,
    )
    gdf["geometry"] = gdf.geometry.simplify(TOLERANCIA_SIMPLIFICACION, preserve_topology=True)

    rng = random.Random(SEMILLA_JITTER)
    niveles, probabilidades = [], []
    for _, fila in gdf.iterrows():
        nivel = NIVEL_POR_PERFIL[fila["nombre_perfil"]]
        prob = round(BASE_POR_NIVEL[nivel] + rng.uniform(-0.1, 0.1), 3)
        niveles.append(nivel)
        probabilidades.append(prob)

    gdf["nivel_riesgo"] = niveles
    gdf["probabilidad_riesgo"] = probabilidades
    gdf["anio"] = ANIO_MOCK
    gdf["tipo_delito"] = TIPO_DELITO_MOCK

    gdf = gdf[["cod_localidad", "localidad_nombre", "cod_dane_mpio", "cluster",
               "nombre_perfil", "nivel_riesgo", "probabilidad_riesgo", "anio",
               "tipo_delito", "geometry"]]

    gdf.to_file(OUT_PATH, driver="GeoJSON")
    _verificar(gdf)


def _verificar(gdf: gpd.GeoDataFrame) -> None:
    assert len(gdf) == 20, "deben quedar exactamente 20 localidades"
    assert set(gdf["nivel_riesgo"]) <= {"bajo", "medio", "alto"}
    assert gdf.loc[gdf["cod_localidad"] == "15", "localidad_nombre"].iloc[0] == "ANTONIO NARIÑO"

    print(f"  {len(gdf)} localidades escritas en {OUT_PATH}")
    print(f"  distribucion nivel_riesgo:\n{gdf['nivel_riesgo'].value_counts().to_string()}")
    print(f"  tamano del archivo: {OUT_PATH.stat().st_size} bytes")
    print(f"\n  [ok] {OUT_PATH}")


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Run the script and verify the real output**

Run: `.venv/Scripts/python app/mock_data/generar_mock.py`

Expected: no assertion errors, and printed output showing:
- `20 localidades escritas en ...zonas_riesgo_mock.geojson`
- distribution: `bajo    12`, `medio    6`, `alto    2`
- file size in the tens of KB (roughly 45,000–60,000 bytes — the exact byte
  count can vary slightly by geopandas/pyogrio version, but it must be far
  smaller than the ~2.3 MB unsimplified source; if it's anywhere near that,
  the `simplify()` call is not taking effect — stop and investigate, don't
  proceed)
- ends with `[ok] .../zonas_riesgo_mock.geojson`

Then independently confirm the mojibake fix at the byte level (`repr()` in a
terminal can itself mis-render UTF-8 on Windows — verifying raw bytes is the
only reliable check):

Run: `grep -o "ANTONIO[^\"]*" app/mock_data/zonas_riesgo_mock.geojson | xxd | head -3`
Expected: the bytes after `NARI` are `c3 91` (UTF-8 for `Ñ`), followed by `4f`
(`O`) — i.e. `c3 91 4f` — not `ef bf bd` (which would be the U+FFFD
replacement character, meaning the fix did not apply).

- [ ] **Step 3: Commit**

```bash
git add app/mock_data/generar_mock.py app/mock_data/zonas_riesgo_mock.geojson
git commit -m "feat(dashboard): agrega generador de mock de zonas-riesgo (issue #32)"
```

---

### Task 2: Dashboard app (loader, Streamlit UI, deps, README)

**Files:**
- Create: `app/data_loader.py`
- Create: `tests/test_data_loader.py`
- Create: `app/streamlit_app.py`
- Create: `app/requirements.txt`
- Create: `app/README.md`
- Modify: `BACKLOG.md` (mark Issue #32's 3 acceptance criteria as complete)

**Interfaces:**
- Consumes: `app/mock_data/zonas_riesgo_mock.geojson` (Task 1, now committed).
- Produces: `cargar_zonas_riesgo() -> dict` in `app/data_loader.py` — the
  function Issue #34 will later modify (not the callers) to hit the real API.

- [ ] **Step 1: Install this task's dependencies into the local venv**

The test in Step 3 imports `app/data_loader.py`, which imports `streamlit` —
so `streamlit` (and `folium`/`streamlit-folium`, needed later in this same
task) must be installed before writing the test.

Run: `.venv/Scripts/pip install streamlit folium streamlit-folium`
Then capture the exact installed versions for `app/requirements.txt` (Step 5):
Run: `.venv/Scripts/pip freeze | findstr /I "streamlit folium"` (Windows) —
or `.venv/Scripts/pip freeze | grep -iE "streamlit|folium"` if using a
POSIX-compatible shell. Keep this output; you'll pin it verbatim in Step 5.

This repo currently uses one shared `.venv` for everything (root
`requirements.txt` documents the data pipeline's pinned versions —
`README.md`'s "Cómo correr" section installs it into the same venv used for
`streamlit run`). If `pip install` reports it needs to change the version of
an already-pinned pipeline dependency (e.g. `pandas`, `numpy`, `pyarrow`) to
satisfy `streamlit`/`folium`, **stop and report BLOCKED** with the exact pip
output instead of letting it silently downgrade/upgrade a pipeline
dependency — that could break Integrante 1's already-merged code, and
deciding how to resolve it (accept the new version, pin an older
Streamlit, or split into a separate venv) is not this task's call to make
alone.

- [ ] **Step 2: Write the failing test**

Create `tests/test_data_loader.py`:

```python
"""Tests para data_loader.cargar_zonas_riesgo (Issue #32).

A diferencia de la mayoria de tests del repo (que usan datos sinteticos),
este lee el fixture mock REAL: app/mock_data/zonas_riesgo_mock.geojson SI
esta commiteado en git (a diferencia de data/), asi que es seguro leerlo en
CI -- es un archivo estatico versionado, no el pipeline real.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from data_loader import cargar_zonas_riesgo

PROPIEDADES_ESPERADAS = {
    "cod_localidad", "localidad_nombre", "cod_dane_mpio", "cluster",
    "nombre_perfil", "nivel_riesgo", "probabilidad_riesgo", "anio", "tipo_delito",
}


def test_cargar_zonas_riesgo_devuelve_20_localidades():
    geojson = cargar_zonas_riesgo()

    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 20


def test_cargar_zonas_riesgo_propiedades_completas():
    geojson = cargar_zonas_riesgo()

    for feature in geojson["features"]:
        assert PROPIEDADES_ESPERADAS.issubset(feature["properties"].keys())
        assert feature["properties"]["nivel_riesgo"] in {"bajo", "medio", "alto"}


def test_cargar_zonas_riesgo_distribucion_nivel_riesgo():
    geojson = cargar_zonas_riesgo()
    niveles = [f["properties"]["nivel_riesgo"] for f in geojson["features"]]

    assert niveles.count("bajo") == 12
    assert niveles.count("medio") == 6
    assert niveles.count("alto") == 2


def test_cargar_zonas_riesgo_corrige_mojibake_antonio_narino():
    geojson = cargar_zonas_riesgo()
    nombres = {f["properties"]["cod_localidad"]: f["properties"]["localidad_nombre"]
               for f in geojson["features"]}

    assert nombres["15"] == "ANTONIO NARIÑO"
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_data_loader.py -v`
Expected: `ModuleNotFoundError: No module named 'data_loader'`

- [ ] **Step 4: Write the loader**

Create `app/data_loader.py`:

```python
"""
data_loader.py — Issue #32

Carga el GeoJSON de zonas-riesgo. Hoy lee el fixture mock commiteado en
app/mock_data/zonas_riesgo_mock.geojson (generado por
app/mock_data/generar_mock.py, #32); la Issue #34 reemplaza el CUERPO de
cargar_zonas_riesgo() por una llamada HTTP real a GET /zonas-riesgo (#20),
sin cambiar su firma ni el resto de streamlit_app.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

MOCK_PATH = Path(__file__).resolve().parent / "mock_data" / "zonas_riesgo_mock.geojson"


@st.cache_data
def cargar_zonas_riesgo() -> dict:
    """Devuelve el GeoJSON de zonas-riesgo (mock, Issue #32).

    dict con forma de FeatureCollection: 20 features, cada una con geometry +
    properties (cod_localidad, localidad_nombre, cluster, nombre_perfil,
    nivel_riesgo, probabilidad_riesgo, anio, tipo_delito).
    """
    with open(MOCK_PATH, encoding="utf-8") as f:
        return json.load(f)
```

Note: calling an `@st.cache_data`-decorated function outside of a running
`streamlit run` process (i.e. directly from `pytest`) may print a Streamlit
warning like `missing ScriptRunContext! This warning can be ignored when
running in bare mode` to stderr. This is expected, harmless Streamlit
behavior in this situation — do not treat it as a test failure, and do not
add warning-suppression code to silence it (that could mask real issues
elsewhere). Just note it in your report if you see it.

- [ ] **Step 5: Run the test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_data_loader.py -v`
Expected: `4 passed` (possibly with the harmless Streamlit stderr note above)

- [ ] **Step 6: Write the Streamlit app**

Create `app/streamlit_app.py`:

```python
"""
streamlit_app.py — Issue #32

Dashboard analitico de Alerta Ciudadana. Hoy: mapa base de Bogota + mock de
zonas-riesgo (via app/data_loader.py). La Issue #33 agrega las capas
completas (coropletico con leyenda, densidad NUSE, control de capas); la
Issue #34 reemplaza el mock por la API real GET /zonas-riesgo (#20).
"""
from __future__ import annotations

import sys
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config

from data_loader import cargar_zonas_riesgo

# Cubre las 20 localidades reales (incluida la rural Sumapaz al sur),
# verificado contra data/03_primary/zonas_bogota.geojson:
# lon [-74.4498, -73.9865], lat [3.7310, 4.8368]
LIMITES_BOGOTA = [[3.7310, -74.4498], [4.8368, -73.9865]]

COLOR_POR_NIVEL = {"bajo": "#2ecc71", "medio": "#f1c40f", "alto": "#e74c3c"}


def _estilo_zona(feature: dict) -> dict:
    nivel = feature["properties"]["nivel_riesgo"]
    return {
        "fillColor": COLOR_POR_NIVEL.get(nivel, "#95a5a6"),
        "color": "#555555",
        "weight": 1,
        "fillOpacity": 0.6,
    }


def main() -> None:
    st.set_page_config(page_title="Alerta Ciudadana", layout="wide")
    st.title("Alerta Ciudadana — Mapa de riesgo por zona")

    with st.sidebar:
        st.header("Controles")
        st.selectbox("Tipo de delito", options=list(config.SIEDCO_TIPOS.values()), index=2)
        st.select_slider("Año", options=list(range(2018, 2026)), value=2025)
        st.caption(
            "Datos de ejemplo (mock): el riesgo mostrado no proviene todavía "
            "del modelo predictivo real ni varía con estos controles — se "
            "conecta a la API real en la Issue #34."
        )

    zonas_riesgo = cargar_zonas_riesgo()

    mapa = folium.Map()
    mapa.fit_bounds(LIMITES_BOGOTA)
    folium.GeoJson(
        zonas_riesgo,
        name="Riesgo por zona (mock)",
        style_function=_estilo_zona,
        tooltip=folium.GeoJsonTooltip(
            fields=["localidad_nombre", "nombre_perfil", "nivel_riesgo"],
            aliases=["Localidad", "Perfil", "Nivel de riesgo"],
        ),
    ).add_to(mapa)

    st_folium(mapa, height=600)


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Smoke-test the app boots**

Streamlit apps don't have a "run once and exit" mode, and there's no browser
tool available to visually confirm the rendered map — so this step only
confirms the app **boots without crashing** (import errors, missing-file
errors, template errors). Visual confirmation of the actual map rendering is
the repo owner's job on their machine (see the report note below).

Run (background, headless, then check its output before killing it):

```bash
.venv/Scripts/streamlit run app/streamlit_app.py --server.headless true --server.port 8501
```

Expected within a few seconds: console output containing
`You can now view your Streamlit app in your browser.` and a `Local URL:
http://localhost:8501` line, with **no Python traceback**. Then, from a
second command, confirm the server actually answers:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
```

Expected: `200`. After confirming both, stop the background Streamlit
process (it must not be left running when you finish the task).

- [ ] **Step 8: Write `app/requirements.txt`**

Create `app/requirements.txt`, pinning the **exact versions** captured in
Step 1's `pip freeze` output (replace the example versions below with what
you actually captured — do not guess or leave the example values if they
don't match):

```
# Dashboard Streamlit — Alerta Ciudadana (Integrante 3)
# Instalar en el mismo venv del repo: .venv/Scripts/pip install -r app/requirements.txt
streamlit==1.38.0
folium==0.17.0
streamlit-folium==0.23.1
```

- [ ] **Step 9: Write `app/README.md`**

Create `app/README.md`:

```markdown
# app/ — Dashboard Streamlit (Integrante 3)

Panel donde se exploran los resultados del análisis: mapa de riesgo por zona
(hoy con datos de ejemplo — ver nota abajo), tipología de zonas por perfil
delictivo (Issue #33) y reporte ciudadano simulado con detección de
anomalías por z-score (Issue #36).

## Cómo correr

```bash
.venv/Scripts/pip install -r app/requirements.txt
.venv/Scripts/streamlit run app/streamlit_app.py
```

Abre <http://localhost:8501>.

## Estado (Issue #32 — scaffold)

El mapa hoy usa **datos de ejemplo** (`app/mock_data/zonas_riesgo_mock.geojson`),
no el modelo predictivo real: la geometría y la tipología de cluster son
reales (de `data/03_primary/zonas_bogota.geojson` y
`models/clustering/zona_cluster.parquet`), pero el nivel de riesgo se derivó
del perfil de cluster con una regla simple, no del modelo Random
Forest/Gradient Boosting (Issue #19, Integrante 2 — aún no implementado). No
requiere correr el pipeline de datos ni instalar `geopandas`: el fixture ya
está commiteado en `app/mock_data/`.

Para regenerar el fixture (si cambia el clustering o la geometría real):

```bash
.venv/Scripts/python app/mock_data/generar_mock.py
```

(Requiere haber corrido `pipelines/pipeline_ml.py` y
`models/clustering/train.py` localmente — este script sí necesita
`geopandas`, vía el `requirements.txt` raíz del repo, no el de `app/`.)

La Issue #34 reemplaza el mock por una llamada real a `GET /zonas-riesgo`
(Issue #20) dentro de `app/data_loader.py`, sin tocar el resto del
dashboard.
```

- [ ] **Step 10: Run the full test suite to confirm no regressions**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests pass (22 pre-existing from before this branch + 4 new =
26).

- [ ] **Step 11: Mark Issue #32 complete in BACKLOG.md**

In `BACKLOG.md`, find the section `### [CLUST] #32 — Scaffold del dashboard
+ consumo de \`/zonas-riesgo\` (con mock)` (around line 636) and change its 3
acceptance criteria from `- [ ]` to `- [x]`:

```diff
 **Criterios de aceptación:**
-- [ ] `streamlit run app/streamlit_app.py` levanta y muestra el mapa base de Bogotá.
-- [ ] Función de carga del GeoJSON (mock con el shape acordado en #20).
-- [ ] Layout base (sidebar de controles + área de mapa) + README de cómo correr.
+- [x] `streamlit run app/streamlit_app.py` levanta y muestra el mapa base de Bogotá.
+- [x] Función de carga del GeoJSON (mock con el shape acordado en #20).
+- [x] Layout base (sidebar de controles + área de mapa) + README de cómo correr.
```

Do not touch any other line or any other issue's checkboxes in this file.

- [ ] **Step 12: Commit**

```bash
git add app/data_loader.py app/streamlit_app.py app/requirements.txt app/README.md tests/test_data_loader.py BACKLOG.md
git commit -m "feat(dashboard): agrega scaffold de app/ con mapa base y mock de zonas-riesgo (issue #32)"
```

---

## Final Checklist

- [ ] The 3 acceptance criteria of Issue #32 (app boots and shows the base
  Bogotá map, mock loader function with #20's agreed shape, sidebar+map
  layout with a README) are satisfied.
- [ ] `pytest tests/ -v` passes completely (26/26).
- [ ] `python -m compileall src pipelines tests` (what CI runs) does not
  fail. Note: `app/` is intentionally **not** added to this `compileall`
  invocation in this task — it's outside `src`/`pipelines`/`tests`, matching
  what CI already checks; if the repo owner wants `app/` covered by CI too,
  that's a separate decision, not part of this plan.
- [ ] `BACKLOG.md` reflects Issue #32 as complete.
- [ ] No background `streamlit run` process was left running after Step 7.
- [ ] The repo owner does a final manual `streamlit run app/streamlit_app.py`
  and confirms visually in a browser that the map looks right — the smoke
  test in Task 2 Step 7 only confirms the server boots and answers HTTP
  200, not that the map renders correctly to the eye.
