# Dashboard Real API Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dashboard's locally-synthesized risk/typology fixture
(from Issue #33) with the real `GET /zonas-riesgo` API (Issue #20, already
built by Integrante 2), closing Issue #34's 3 acceptance criteria.

**Architecture:** `app/data_loader.py::cargar_zonas_riesgo(anio,
tipo_delito)` swaps its body from reading local JSON fixtures to an HTTP
`GET` against the real API (`requests`, cached with `@st.cache_data(ttl=300)`,
graceful error handling). The now-obsolete local risk/typology fixtures
(`app/data/riesgo_por_zona.json`, `app/data/tipologia_zonas.json`) and
their generators are retired. `app/streamlit_app.py`'s risk layer is
rebuilt around the API's real 3-level `nivel_riesgo` field instead of the
old synthetic 2-level `riesgo_alto`.

**Tech Stack:** Python, `requests` (new `app/` runtime dependency, already
installed via the root `requirements.txt`), `unittest.mock` (test-only, for
mocking the HTTP boundary — the one legitimate exception to this repo's
"real or synthetic data, never mocks" convention, since a unit test must
not depend on a live server), FastAPI/uvicorn (already installed locally
for the end-to-end smoke test in Task 3).

## Global Constraints

- `cargar_zonas_riesgo(anio, tipo_delito)` must call the real API — no
  fallback to any local mock/fixture in the final state (backlog: "Sin
  datos mock en la demo final").
- API base URL is configurable via the `ALERTA_API_URL` environment
  variable, defaulting to `http://localhost:8000` (matches the API's own
  documented default port in `api/README.md`).
- Cached with `@st.cache_data(ttl=300)` — not re-fetched on every sidebar
  interaction, but not stuck on stale data indefinitely either (5 minutes).
- If the API is unreachable or returns an error, `cargar_zonas_riesgo` must
  raise a clear `RuntimeError` (never let a raw `requests` exception or an
  unhandled crash reach the user) — `streamlit_app.py` catches it and shows
  `st.error(...)` + `st.stop()`.
- The real API's response schema (verified by actually running it — see
  below) is: `cod_localidad, localidad_nombre, cod_dane_mpio, cluster,
  nombre_perfil, nivel_riesgo ("bajo"|"medio"|"alto"), probabilidad_riesgo,
  riesgo_predicho, anio, tipo_delito, tipo_delito_nombre` + `geometry`. It
  does **not** have `riesgo_alto` or `conteo_siedco` (those were this
  repo's own local proxy from #33) — all consuming code must use the real
  field names.
- `cargar_densidad_nuse`, `cargar_linea_base`, and the private
  `_cargar_geometria`/`_cargar_nuse_crudo` helpers in `app/data_loader.py`
  are **not** part of this change — NUSE and the citizen-report baseline
  are not served by `/zonas-riesgo` (per `CLAUDE.md` §4) and keep reading
  local committed fixtures.
- `app/data/geometria_localidades.geojson` and `app/data/nuse_por_zona.json`
  stay (still needed for the NUSE layer). `app/data/riesgo_por_zona.json`
  and `app/data/tipologia_zonas.json` are deleted (superseded by the live
  API).

---

### Task 1: `app/data_loader.py` — real API call for `cargar_zonas_riesgo`

**Files:**
- Modify: `app/data_loader.py` (full rewrite)
- Modify: `tests/test_data_loader.py` (full rewrite — replaces the 4
  fixture-based risk tests from #33 with 3 mocked-HTTP tests; the 3
  `cargar_densidad_nuse` tests are unchanged, just carried over verbatim)

**Interfaces:**
- Consumes: the real API's `GET /zonas-riesgo?anio=X&tipo=Y` endpoint
  (Issue #20, already running code in `api/main.py`/`api/state.py` — not
  modified by this plan).
- Produces: `cargar_zonas_riesgo(anio: int, tipo_delito: str) -> dict` (same
  name/signature as before, now backed by a real HTTP call) and
  `API_BASE_URL: str` (module-level constant) — both consumed by Task 3's
  `app/streamlit_app.py`.

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `tests/test_data_loader.py`:

```python
"""Tests para data_loader (Issue #34): cargar_zonas_riesgo ahora llama a la
API real via requests, en vez de leer fixtures locales (retirados en esta
issue). cargar_densidad_nuse sigue local (NUSE no esta en el contrato de la
API) -- sus tests, de la Issue #33, no cambian.

Se mockea requests.get (frontera de red) -- unica excepcion al patron de
"datos reales o sinteticos, nunca mocks" de este repo: una unit test no
debe depender de que la API este corriendo. La prueba end-to-end real (API
+ dashboard corriendo juntos) se hace aparte, ver la Tarea 3 de este plan.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from data_loader import API_BASE_URL, cargar_densidad_nuse, cargar_zonas_riesgo

GEOJSON_EJEMPLO = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "cod_localidad": "01",
                "localidad_nombre": "USAQUEN",
                "nivel_riesgo": "medio",
                "probabilidad_riesgo": 0.4354,
                "riesgo_predicho": 0,
                "cluster": 0,
                "nombre_perfil": "Perfil de bajo incidente relativo",
                "anio": 2025,
                "tipo_delito": "HP",
            },
            "geometry": {"type": "Polygon", "coordinates": []},
        }
    ],
}


def test_cargar_zonas_riesgo_llama_a_la_api_con_los_parametros_correctos():
    cargar_zonas_riesgo.clear()
    with patch("data_loader.requests.get") as mock_get:
        mock_get.return_value = Mock(json=lambda: GEOJSON_EJEMPLO)
        mock_get.return_value.raise_for_status = lambda: None

        resultado = cargar_zonas_riesgo(2025, "HP")

    mock_get.assert_called_once_with(
        f"{API_BASE_URL}/zonas-riesgo",
        params={"anio": 2025, "tipo": "HP"},
        timeout=10,
    )
    assert resultado == GEOJSON_EJEMPLO


def test_cargar_zonas_riesgo_api_caida_lanza_runtime_error_claro():
    cargar_zonas_riesgo.clear()
    with patch("data_loader.requests.get", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(RuntimeError, match=API_BASE_URL):
            cargar_zonas_riesgo(2024, "H")


def test_cargar_zonas_riesgo_error_http_lanza_runtime_error():
    cargar_zonas_riesgo.clear()
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("422 tipo invalido")
    with patch("data_loader.requests.get", return_value=mock_response):
        with pytest.raises(RuntimeError):
            cargar_zonas_riesgo(2030, "ZZ")


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
Expected: failures — `app/data_loader.py` still has the old fixture-based
`cargar_zonas_riesgo()` (no `API_BASE_URL` export, doesn't call
`requests.get`), so `from data_loader import API_BASE_URL` will fail with
`ImportError`, or the mock assertions will fail. Confirm the failures are
because the new API-backed behavior doesn't exist yet, not for an
unrelated reason.

- [ ] **Step 3: Rewrite the loader**

Replace the full contents of `app/data_loader.py`:

```python
"""
data_loader.py — Issue #34 (reemplaza el fixture local de riesgo/tipologia
de la Issue #33 por la API real)

cargar_zonas_riesgo() llama a la API real GET /zonas-riesgo (#20, de
Integrante 2) -- ya no lee fixtures locales de riesgo/tipologia (esos
quedaron obsoletos y se retiraron en esta issue, ver
app/data/generar_datasets_mapa.py). cargar_densidad_nuse() y
cargar_linea_base() SIGUEN leyendo fixtures locales: NUSE no forma parte
del contrato de la API (CLAUDE.md ss4) y la linea base del reporte
ciudadano (#36) tampoco.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"
GEOMETRIA_PATH = DATA_DIR / "geometria_localidades.geojson"
NUSE_PATH = DATA_DIR / "nuse_por_zona.json"
LINEA_BASE_PATH = DATA_DIR / "linea_base_zscore.json"

API_BASE_URL = os.environ.get("ALERTA_API_URL", "http://localhost:8000")


@st.cache_data
def _cargar_geometria() -> dict:
    with open(GEOMETRIA_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def _cargar_nuse_crudo() -> list[dict]:
    with open(NUSE_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=300)
def cargar_zonas_riesgo(anio: int, tipo_delito: str) -> dict:
    """GeoJSON de las 20 localidades con riesgo REAL (modelo predictivo,
    #19) y tipologia REAL (#27), pedido a la API real GET /zonas-riesgo
    (#20). Cacheado 5 minutos (ttl=300): no se re-pide en cada interaccion
    del sidebar, pero tampoco queda pegado indefinidamente si la API se
    reinicia con un modelo nuevo.

    Lanza RuntimeError con un mensaje claro si la API no responde (caida,
    timeout, error HTTP) -- streamlit_app.py lo atrapa y muestra con
    st.error en vez de dejar que tumbe la app.
    """
    try:
        respuesta = requests.get(
            f"{API_BASE_URL}/zonas-riesgo",
            params={"anio": anio, "tipo": tipo_delito},
            timeout=10,
        )
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"No se pudo conectar a la API en {API_BASE_URL}/zonas-riesgo "
            f"(anio={anio}, tipo={tipo_delito}). ¿Está corriendo "
            f"`uvicorn api.main:app`? Detalle: {exc}"
        ) from exc


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


@st.cache_data
def cargar_linea_base() -> list[dict]:
    """Linea base historica real (#26): lista de dicts con cod_localidad,
    tipo_delito, media, desviacion. Consumida por
    app/reporte_ciudadano.py::construir_reporte (via flag_zscore, #29).
    """
    with open(LINEA_BASE_PATH, encoding="utf-8") as f:
        return json.load(f)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_data_loader.py -v`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add app/data_loader.py tests/test_data_loader.py
git commit -m "feat(dashboard): cargar_zonas_riesgo llama a la API real (issue #34)"
```

---

### Task 2: Retire the obsolete local risk/typology fixtures

**Files:**
- Modify: `app/data/generar_datasets_mapa.py`
- Delete: `app/data/riesgo_por_zona.json`, `app/data/tipologia_zonas.json`

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing new — this task only removes now-dead code/data. No
  other task depends on it, but Task 3's `streamlit_app.py` must not
  reference the removed fixtures either (it doesn't — it goes through
  `cargar_zonas_riesgo()`, already fixed in Task 1).

- [ ] **Step 1: Delete the obsolete fixture files**

Delete these two files:
- `app/data/riesgo_por_zona.json`
- `app/data/tipologia_zonas.json`

- [ ] **Step 2: Update the module docstring**

Find the docstring at the top of `app/data/generar_datasets_mapa.py`:

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
```

Replace with:

```python
"""
generar_datasets_mapa.py — Issue #33 (riesgo/tipologia retirados en #34)

Genera los 3 archivos de datos reales que el dashboard sigue necesitando
localmente: geometria_localidades.geojson (capa NUSE, #33),
nuse_por_zona.json (capa NUSE, #33) y linea_base_zscore.json (reporte
ciudadano, #36). Riesgo y tipologia (antes generados aqui como
riesgo_por_zona.json / tipologia_zonas.json) se RETIRARON en la Issue #34:
ahora vienen de la API real GET /zonas-riesgo (#20), no de un fixture local
-- ver app/data_loader.py::cargar_zonas_riesgo(). conteo_nuse viene de
nuse_incidentes.parquet (#4), agregado a nivel localidad porque no existe
geometria real de UPZ en el pipeline (verificado: ni data/02_intermediate/
ni data/03_primary/ tienen limites de UPZ, solo de localidad).
```

(Leave the rest of the docstring — the mojibake and NUSE-structural-zero
paragraphs below it — unchanged.)

- [ ] **Step 3: Remove the now-dead path constants**

Find:

```python
OUT_DIR = Path(__file__).resolve().parent
GEOMETRIA_PATH = OUT_DIR / "geometria_localidades.geojson"
RIESGO_PATH = OUT_DIR / "riesgo_por_zona.json"
TIPOLOGIA_PATH = OUT_DIR / "tipologia_zonas.json"
NUSE_PATH = OUT_DIR / "nuse_por_zona.json"
LINEA_BASE_PATH = OUT_DIR / "linea_base_zscore.json"

ZONA_CLUSTER_PATH = config.ROOT / "models" / "clustering" / "zona_cluster.parquet"
NUSE_INCIDENTES_PATH = config.ROOT / "data" / "02_intermediate" / "nuse_incidentes.parquet"
```

Replace with:

```python
OUT_DIR = Path(__file__).resolve().parent
GEOMETRIA_PATH = OUT_DIR / "geometria_localidades.geojson"
NUSE_PATH = OUT_DIR / "nuse_por_zona.json"
LINEA_BASE_PATH = OUT_DIR / "linea_base_zscore.json"

NUSE_INCIDENTES_PATH = config.ROOT / "data" / "02_intermediate" / "nuse_incidentes.parquet"
```

(`ZONA_CLUSTER_PATH` was used only by `_generar_tipologia`, removed in Step
5 below — safe to remove here too. `import feature_engineering` and
`import config` stay, both still used by `_generar_linea_base` and
`_generar_geometria`/`_generar_nuse`.)

- [ ] **Step 4: Update `run()`**

Find:

```python
def run() -> None:
    print("== #33/#36 Generar datasets reales del mapa ==")
    _generar_geometria()
    _generar_riesgo()
    _generar_tipologia()
    _generar_nuse()
    _generar_linea_base()
    print("\n  [ok] los 5 archivos de app/data/ estan listos")
```

Replace with:

```python
def run() -> None:
    print("== #33/#34/#36 Generar datasets reales del mapa ==")
    _generar_geometria()
    _generar_nuse()
    _generar_linea_base()
    print("\n  [ok] los 3 archivos de app/data/ estan listos")
```

- [ ] **Step 5: Remove `_generar_riesgo()` and `_generar_tipologia()`**

Delete these two full functions from `app/data/generar_datasets_mapa.py`
(everything between `_generar_geometria()` and `_generar_nuse()`):

```python
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
```

(Delete the whole block above, including the two blank lines that
separate it from `_generar_nuse()` on one side — leave exactly one blank
line of separation between `_generar_geometria()` and `_generar_nuse()`,
matching the file's existing two-blank-lines-between-functions style.)

- [ ] **Step 6: Run the script and verify the real output**

Run: `.venv/Scripts/python app/data/generar_datasets_mapa.py`

Expected: no assertion errors, only 3 files reported (geometria, nuse,
linea_base — same real numbers as before: geometria ~49,600 bytes / 20
localidades; nuse 160 filas / 1 cero estructural; linea_base 220 filas),
ending with `[ok] los 3 archivos de app/data/ estan listos`.

- [ ] **Step 7: Commit**

```bash
git rm app/data/riesgo_por_zona.json app/data/tipologia_zonas.json
git add app/data/generar_datasets_mapa.py
git commit -m "feat(dashboard): retira los fixtures locales de riesgo/tipologia (issue #34)"
```

---

### Task 3: Rewire the risk layer, error handling, deps, docs, end-to-end test

**Files:**
- Modify: `app/streamlit_app.py`
- Modify: `app/requirements.txt` (+ `requests`)
- Modify: `app/README.md`
- Modify: `BACKLOG.md` (mark Issue #34's 3 acceptance criteria complete)

**Interfaces:**
- Consumes: `cargar_zonas_riesgo(anio, tipo_delito) -> dict` (Task 1, now
  API-backed) and `API_BASE_URL` (Task 1).
- Produces: the running dashboard, now fully API-driven for risk/typology
  — no other task depends on this one.

- [ ] **Step 1: Update the module docstring and imports**

Find:

```python
"""
streamlit_app.py — Issue #33 (reemplaza el mapa de un solo layer de la Issue #32)

Dashboard analitico de Alerta Ciudadana. 3 capas reales, togglables:
coropletico de riesgo (percentil historico, #10, siempre visible), densidad
NUSE (agregada a nivel localidad -- no existe geometria real de UPZ, ver
app/README.md) y tipologia de zonas (K-Means real, #27), estas dos ultimas
activables con checkboxes del sidebar (no con el LayerControl nativo de
Leaflet, para mantener un solo lugar de controles consistente con el resto
de la app). La Issue #34 reemplaza cargar_zonas_riesgo() por la API real
GET /zonas-riesgo (#20); cargar_densidad_nuse() se queda local para siempre
(NUSE no forma parte del contrato de esa API).
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

from data_loader import cargar_zonas_riesgo, cargar_densidad_nuse, cargar_linea_base
from reporte_ciudadano import render_formulario_reporte
```

Replace with:

```python
"""
streamlit_app.py — Issue #34 (conecta el coropletico de riesgo a la API real)

Dashboard analitico de Alerta Ciudadana. 3 capas, togglables: coropletico
de riesgo (modelo predictivo REAL via GET /zonas-riesgo, #20, #34, siempre
visible), densidad NUSE (agregada a nivel localidad -- no existe geometria
real de UPZ, ver app/README.md) y tipologia de zonas (K-Means real, #27),
estas dos ultimas activables con checkboxes del sidebar (no con el
LayerControl nativo de Leaflet, para mantener un solo lugar de controles
consistente con el resto de la app). cargar_densidad_nuse() se queda local
para siempre (NUSE no forma parte del contrato de esa API).
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

from data_loader import API_BASE_URL, cargar_zonas_riesgo, cargar_densidad_nuse, cargar_linea_base
from reporte_ciudadano import render_formulario_reporte
```

- [ ] **Step 2: Update the risk color map and style function**

Find:

```python
COLOR_RIESGO = {1: "#e74c3c", 0: "#2ecc71"}
COLOR_TIPOLOGIA = {
    "Perfil de alto impacto generalizado": "#c0392b",
    "Perfil hurto de bienes / ingreso alto": "#f39c12",
    "Perfil de bajo incidente relativo": "#27ae60",
}
ICONO_POR_ATIPICO = {True: ("triangle-exclamation", "red"), False: ("circle-check", "green")}


def _estilo_riesgo(feature: dict) -> dict:
    riesgo_alto = feature["properties"]["riesgo_alto"]
    return {"fillColor": COLOR_RIESGO[riesgo_alto], "color": "#555555", "weight": 1, "fillOpacity": 0.6}
```

Replace with:

```python
COLOR_RIESGO = {"bajo": "#2ecc71", "medio": "#f1c40f", "alto": "#e74c3c"}
COLOR_TIPOLOGIA = {
    "Perfil de alto impacto generalizado": "#c0392b",
    "Perfil hurto de bienes / ingreso alto": "#f39c12",
    "Perfil de bajo incidente relativo": "#27ae60",
}
ICONO_POR_ATIPICO = {True: ("triangle-exclamation", "red"), False: ("circle-check", "green")}


def _estilo_riesgo(feature: dict) -> dict:
    nivel = feature["properties"]["nivel_riesgo"]
    return {"fillColor": COLOR_RIESGO.get(nivel, "#95a5a6"), "color": "#555555", "weight": 1, "fillOpacity": 0.6}
```

- [ ] **Step 3: Update the sidebar caption**

Find:

```python
        st.caption(
            "El coroplético de riesgo usa un umbral histórico (percentil 75 "
            "de incidentes), no el modelo predictivo real — se conecta a la "
            "API real en la Issue #34."
        )
```

Replace with:

```python
        st.caption(
            f"El coroplético de riesgo viene del modelo predictivo real, "
            f"vía la API en {API_BASE_URL}."
        )
```

- [ ] **Step 4: Wrap the API call in error handling and update the tooltip**

Find:

```python
    zonas_riesgo = cargar_zonas_riesgo(anio, tipo_codigo)

    mapa = folium.Map()
    mapa.fit_bounds(LIMITES_BOGOTA)

    folium.GeoJson(
        zonas_riesgo,
        style_function=_estilo_riesgo,
        tooltip=folium.GeoJsonTooltip(
            fields=["localidad_nombre", "riesgo_alto", "conteo_siedco"],
            aliases=["Localidad", "¿Riesgo alto?", "Incidentes registrados"],
        ),
    ).add_to(mapa)
```

Replace with:

```python
    try:
        zonas_riesgo = cargar_zonas_riesgo(anio, tipo_codigo)
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    mapa = folium.Map()
    mapa.fit_bounds(LIMITES_BOGOTA)

    folium.GeoJson(
        zonas_riesgo,
        style_function=_estilo_riesgo,
        tooltip=folium.GeoJsonTooltip(
            fields=["localidad_nombre", "tipo_delito_nombre", "nivel_riesgo", "probabilidad_riesgo"],
            aliases=["Localidad", "Tipo de delito", "Nivel de riesgo", "Probabilidad"],
        ),
    ).add_to(mapa)
```

- [ ] **Step 5: Add `requests` to `app/requirements.txt`**

`requests==2.34.2` is already installed in this repo's shared venv
(confirmed: it's a real dependency of Integrante 1's pipeline, declared in
the root `requirements.txt`) — no new `pip install` needed, just declare
it in `app/requirements.txt` too, since the dashboard now genuinely depends
on it directly. Add this line to `app/requirements.txt`:

```
requests==2.34.2
```

- [ ] **Step 6: Start the real API and the dashboard together — end-to-end test**

This is the actual "criterio 3" verification: not just that each process
boots, but that the dashboard genuinely reflects what the live API
returns.

First, confirm the artifacts the API needs exist (they should already, from
prior work in this repo): `models/predictivo/model.joblib`,
`models/clustering/clusters.joblib`, `models/clustering/zona_cluster.parquet`,
`data/03_primary/dataset_analitico.parquet`, `data/03_primary/zonas_bogota.geojson`.
If any are missing, regenerate per `api/README.md`'s instructions before
continuing.

Start the API in the background:

```bash
.venv/Scripts/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 &
```

Wait a few seconds, then confirm it's really serving real data:

```bash
curl -s "http://127.0.0.1:8000/zonas-riesgo?anio=2025&tipo=HP" | .venv/Scripts/python -c "import json,sys; d=json.load(sys.stdin); print(d['features'][0]['properties'])"
```

Expected: a dict with `nivel_riesgo`, `probabilidad_riesgo`, etc. (real
values — don't hardcode an expected number here, the model may have been
retrained since this plan was written; just confirm the shape is right and
note the actual value).

Now start the dashboard in the background, pointed at that same API
(default `ALERTA_API_URL` already matches `http://localhost:8000`):

```bash
.venv/Scripts/streamlit run app/streamlit_app.py --server.headless true --server.port 8501 &
```

Wait a few seconds, confirm it boots:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
```

Expected: `200`, no traceback in the Streamlit process's output.

This confirms both processes run together without errors, which is the
automatable part of "criterio 3." **Visual confirmation that the map's
colors/tooltip genuinely match the API's real per-locality values is the
repo owner's job** (no browser tool available here) — call this out
explicitly in your report, don't claim to have visually verified it.

Stop both background processes when done (do not leave them running):

```bash
# find and kill both the uvicorn and streamlit processes you started
```

- [ ] **Step 7: Run the full test suite to confirm no regressions**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests pass (35 pre-existing, unchanged count — Task 1
replaced 4 old tests with 3 new ones in `test_data_loader.py`, net −1, but
this plan's Task 1 Step 4 already confirmed `test_data_loader.py` alone has
6 passing; the full-suite total is 35 − 4 + 3 = **34**).

- [ ] **Step 8: Update `app/README.md`**

Find:

```markdown
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
```

Replace with:

```markdown
## Las 3 capas del mapa (Issues #33, #34)

1. **Riesgo por zona**: colorea cada localidad según `nivel_riesgo`
   (`"bajo"|"medio"|"alto"`), calculado por el **modelo predictivo real**
   (Random Forest/XGBoost, Issue #19) y servido en vivo por
   `GET /zonas-riesgo` (Issue #20) — no hay ningún mock ni fixture local
   para esta capa desde la Issue #34. El selector de año/tipo de delito del
   sidebar re-consulta la API de verdad. Requiere que la API esté corriendo
   (`uvicorn api.main:app`, ver más abajo) — si no responde, el dashboard
   muestra un error claro en vez de romperse.
2. **Densidad NUSE**: llamadas al 123 por localidad, coloreadas con una
   escala continua. *Limitación conocida:* el dato abierto real trae
   resolución de UPZ (más fina que localidad), pero el pipeline nunca
   ingirió la geometría de esas UPZ (solo la de localidad, Issue #5) — la
   capa muestra el agregado a nivel localidad. Ingerir geometría real de UPZ
   queda como trabajo futuro para Integrante 1. Esta capa **no** viene de
   la API (NUSE no forma parte de su contrato, ver `CLAUDE.md` §4) — sigue
   leyendo el fixture local `app/data/nuse_por_zona.json`.
3. **Tipología de zonas**: colorea por el perfil de K-Means real (Issue
   #27), con tooltip en lenguaje no técnico — viene de la misma respuesta
   de `GET /zonas-riesgo` que la capa de riesgo.

## Cómo correr con la API real (Issue #34)

El dashboard necesita la API corriendo para la capa de riesgo/tipología:

```bash
# Terminal 1 — API (necesita los artefactos entrenados, ver api/README.md)
.venv/Scripts/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — dashboard
.venv/Scripts/pip install -r app/requirements.txt
.venv/Scripts/streamlit run app/streamlit_app.py
```

Por defecto el dashboard apunta a `http://localhost:8000`. Para apuntar a
otra URL (ej. la API corriendo en otra máquina de la red), define la
variable de entorno `ALERTA_API_URL` antes de correr `streamlit run`.
```

Find:

```markdown
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

Replace with:

```markdown
## Datos: `app/data/`

Los 3 archivos en `app/data/*.json`/`*.geojson` están **commiteados** (a
diferencia de `data/`, que es gitignored) — los sigue necesitando la capa
NUSE (`geometria_localidades.geojson`, `nuse_por_zona.json`) y el reporte
ciudadano (`linea_base_zscore.json`, Issue #36). La capa de riesgo/tipología
ya **no** usa un fixture local (retirado en la Issue #34) — viene de la API
real. Se generan una sola vez con datos reales:

```bash
.venv/Scripts/python app/data/generar_datasets_mapa.py
```

(Requiere haber corrido `pipelines/pipeline_ml.py` y
`models/clustering/train.py` localmente — este script sí necesita
`pandas`/`geopandas`, vía el `requirements.txt` raíz del repo, no el de
`app/`. Solo hace falta regenerarlo si cambian los datos o el clustering
reales.)
```

- [ ] **Step 9: Mark Issue #34 complete in BACKLOG.md**

In `BACKLOG.md`, find the section `### [CLUST] #34 — Integrar la API real
en el dashboard (reemplazar mock)` (around line 670) and change its 3
acceptance criteria from `- [ ]` to `- [x]`:

```diff
 **Criterios de aceptación:**
-- [ ] El mapa de riesgo y la tipología se alimentan del endpoint real.
-- [ ] GeoJSON cacheado (`@st.cache_data`), no re-pedido por cada interacción.
-- [ ] Prueba end-to-end: API → dashboard lo refleja. Sin mocks.
+- [x] El mapa de riesgo y la tipología se alimentan del endpoint real.
+- [x] GeoJSON cacheado (`@st.cache_data`), no re-pedido por cada interacción.
+- [x] Prueba end-to-end: API → dashboard lo refleja. Sin mocks.
```

Do not touch any other line or any other issue's checkboxes in this file.

- [ ] **Step 10: Commit**

```bash
git add app/streamlit_app.py app/requirements.txt app/README.md BACKLOG.md
git commit -m "feat(dashboard): conecta el coropletico de riesgo a la API real (issue #34)"
```

---

## Final Checklist

- [ ] The 3 acceptance criteria of Issue #34 (real endpoint feeds risk +
  typology, cached not re-fetched per interaction, end-to-end proof with
  no mocks) are satisfied.
- [ ] `pytest tests/ -v` passes completely (34/34).
- [ ] `python -m compileall src pipelines tests` (what CI runs) does not
  fail. `app/` remains intentionally outside this invocation, same
  decision as prior dashboard issues.
- [ ] `BACKLOG.md` reflects Issue #34 as complete.
- [ ] `app/data/riesgo_por_zona.json` and `app/data/tipologia_zonas.json`
  no longer exist; nothing references them.
- [ ] No background `uvicorn`/`streamlit run` process was left running
  after Task 3 Step 6.
- [ ] The repo owner does a final manual check: start the API
  (`uvicorn api.main:app`) and the dashboard (`streamlit run
  app/streamlit_app.py`) together, change the year/tipo de delito
  selectors, and confirm the map's colors and tooltip values genuinely
  change and match what `curl`ing `/zonas-riesgo` directly returns for the
  same parameters — the automated smoke test in Task 3 only confirms both
  processes boot without errors, not that the visual rendering is correct.
