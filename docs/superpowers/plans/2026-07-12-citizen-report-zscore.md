# Citizen Report + Z-Score Flag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a simulated citizen crime report form to the dashboard: click
the map to pick a location, fill in crime type + description, consent to a
privacy notice, submit — the report is evaluated against the real
historical baseline with `flag_zscore()` (#29) and rendered as a marker on
the map, all in `st.session_state` (no database). Closes Issue #36's 4
acceptance criteria.

**Architecture:** A 5th real, committed fixture (`app/data/linea_base_zscore.json`,
extending Issue #33's generator) supplies the historical baseline. A new
pure spatial-lookup module (`app/localidad_lookup.py`) resolves a map click
to one of the 20 real localities via point-in-polygon. A new module
(`app/reporte_ciudadano.py`) has a pure report-builder (reuses `src/flag_zscore.py`
from #29 verbatim, no reimplementation) plus the Streamlit form UI.
`app/streamlit_app.py` wires it together: draws markers for past reports,
renders the form using the map's last click.

**Tech Stack:** Python, pandas + shapely (new `app/` runtime dependencies,
both already installed in the shared venv), streamlit, folium (FontAwesome
icons via `prefix="fa"` — no emojis, per project convention), pytest.

## Global Constraints

- Each report is evaluated **independently with `conteo=1`** against the
  real annual historical baseline — never an accumulated session count.
  Verified real behavior: common case (`"01"`/`"DS"`, media≈296.4) →
  `es_atipico=True`, `z_score≈-4.37` (explain this as "below average," not
  a danger alert); zero-history case (`"20"`/`"HA"`, media=0,
  desviacion=0) → `es_atipico=True`, `z_score=None` (a genuine "never
  happened here before" signal — highlight differently in the UI).
- `flag_zscore()` from `src/flag_zscore.py` (#29) is reused verbatim — do
  not reimplement its logic.
- No emojis anywhere in new UI code — map markers use `folium.Icon` with
  FontAwesome (`prefix="fa"`) icon names; Streamlit headers/buttons use
  `:material/...:` shortcodes (supported since Streamlit 1.31+; confirmed
  working in the installed 1.59.1).
- Reports live only in `st.session_state` — no database, no persistence
  across sessions (already-fixed project-wide decision, not up for
  reinterpretation here).
- Input validation is required and must degrade gracefully: reject clicks
  outside Bogotá (`ubicar_localidad` returns `None`), reject empty
  descriptions, never crash on a missing/not-yet-registered click.
- Consent checkbox (Ley 1581/2012 notice) must block form submission until
  checked — this is explicitly called out in the backlog as "no se
  recorta."
- `app/data/linea_base_zscore.json` must be **real** data (from
  `calcular_linea_base()`, #26) — no fabrication.
- Tests reading real data read only real, git-committed fixtures under
  `app/data/` (never `data/`/`models/`, which are gitignored).

---

### Task 1: Real baseline fixture (extend `app/data/generar_datasets_mapa.py`)

**Files:**
- Modify: `app/data/generar_datasets_mapa.py`
- Create (by running the script): `app/data/linea_base_zscore.json`

**Interfaces:**
- Consumes: `data/03_primary/dataset_analitico.parquet` (already read by
  this script for `_generar_riesgo`) and
  `src/feature_engineering.py::calcular_linea_base` (#26, already exists,
  unmodified).
- Produces: `app/data/linea_base_zscore.json` — a JSON list of 220 dicts
  (`cod_localidad, tipo_delito, media, desviacion`), consumed by Task 4's
  `app/data_loader.py::cargar_linea_base()`. Verified exact shape (real
  numbers, confirmed by running this logic before writing this plan): 220
  rows, ~23,300 bytes. First row: `{"cod_localidad": "01", "tipo_delito":
  "DS", "media": 296.42857142857144, "desviacion": 67.63100162612099}`.

No unit test — one-time data-generation addition, same pattern as the rest
of this script (#33). Verified by running it and inspecting real output.

- [ ] **Step 1: Add the import and path constant**

In `app/data/generar_datasets_mapa.py`, find this line near the top:

```python
import config
```

Change it to:

```python
import config
import feature_engineering
```

Find this block of path constants:

```python
GEOMETRIA_PATH = OUT_DIR / "geometria_localidades.geojson"
RIESGO_PATH = OUT_DIR / "riesgo_por_zona.json"
TIPOLOGIA_PATH = OUT_DIR / "tipologia_zonas.json"
NUSE_PATH = OUT_DIR / "nuse_por_zona.json"
```

Add one more line after it:

```python
GEOMETRIA_PATH = OUT_DIR / "geometria_localidades.geojson"
RIESGO_PATH = OUT_DIR / "riesgo_por_zona.json"
TIPOLOGIA_PATH = OUT_DIR / "tipologia_zonas.json"
NUSE_PATH = OUT_DIR / "nuse_por_zona.json"
LINEA_BASE_PATH = OUT_DIR / "linea_base_zscore.json"
```

- [ ] **Step 2: Add the generator function**

Add this new function after `_generar_nuse()` (before `if __name__ ==
"__main__":`):

```python
def _generar_linea_base() -> None:
    df = pd.read_parquet(config.DATASET_ANALITICO)
    linea_base = feature_engineering.calcular_linea_base(df)
    linea_base["media"] = linea_base["media"].astype(float)
    linea_base["desviacion"] = linea_base["desviacion"].astype(float)
    registros = linea_base.to_dict(orient="records")

    assert len(registros) == 220, "esperadas 20 localidades x 11 tipos = 220 filas"
    with open(LINEA_BASE_PATH, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False)
    print(f"  linea_base_zscore.json: {len(registros)} filas, {LINEA_BASE_PATH.stat().st_size} bytes")
```

- [ ] **Step 3: Wire it into `run()`**

Find:

```python
def run() -> None:
    print("== #33 Generar datasets reales del mapa ==")
    _generar_geometria()
    _generar_riesgo()
    _generar_tipologia()
    _generar_nuse()
    print("\n  [ok] los 4 archivos de app/data/ estan listos")
```

Replace with:

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

- [ ] **Step 4: Run the script and verify the real output**

Run: `.venv/Scripts/python app/data/generar_datasets_mapa.py`

Expected: no assertion errors, all 5 files reported (the 4 from #33 plus
the new one), ending with:
`linea_base_zscore.json: 220 filas, ~23300 bytes` (exact byte count may
vary slightly — it must be in the tens of KB, not near-zero and not huge)
and `[ok] los 5 archivos de app/data/ estan listos`.

Then spot-check the real content:

Run: `.venv/Scripts/python -c "import json; d=json.load(open('app/data/linea_base_zscore.json', encoding='utf-8')); print(len(d)); print([r for r in d if r['cod_localidad']=='01' and r['tipo_delito']=='DS'][0])"`
Expected: `220` then a dict with `media` ≈ `296.43` and `desviacion` ≈
`67.63` (matching the numbers verified above — this is the exact same real
data used throughout this plan's tests).

- [ ] **Step 5: Commit**

```bash
git add app/data/generar_datasets_mapa.py app/data/linea_base_zscore.json
git commit -m "feat(dashboard): agrega linea base real para el flag z-score (issue #36)"
```

---

### Task 2: Point-in-polygon locality lookup (`app/localidad_lookup.py`)

**Files:**
- Create: `app/localidad_lookup.py`
- Create: `tests/test_localidad_lookup.py`

**Interfaces:**
- Consumes: a GeoJSON `FeatureCollection` dict (the real, committed
  `app/data/geometria_localidades.geojson` from #33 — tests read it
  directly since it's git-tracked and safe in CI).
- Produces: `ubicar_localidad(lat: float, lon: float, geometria: dict) -> str | None` —
  consumed by Task 4's `app/reporte_ciudadano.py`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_localidad_lookup.py`:

```python
"""Tests para ubicar_localidad (Issue #36).

A diferencia de la mayoria de tests puros del repo, este usa la geometria
REAL commiteada en app/data/geometria_localidades.geojson (de #33) -- es
seguro en CI porque, a diferencia de data/, esta versionada en git.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from localidad_lookup import ubicar_localidad

GEOMETRIA_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "geometria_localidades.geojson"


def _cargar_geometria_real() -> dict:
    with open(GEOMETRIA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_ubicar_localidad_punto_real_dentro_de_usaquen():
    geometria = _cargar_geometria_real()

    # Punto representativo real dentro del poligono de Usaquen (cod "01"),
    # verificado con shapely antes de escribir este test.
    cod = ubicar_localidad(4.745190674500066, -74.02788785657322, geometria)

    assert cod == "01"


def test_ubicar_localidad_fuera_de_bogota_devuelve_none():
    geometria = _cargar_geometria_real()

    cod = ubicar_localidad(0.0, 0.0, geometria)

    assert cod is None


def test_ubicar_localidad_otro_punto_real_dentro_de_bogota():
    geometria = _cargar_geometria_real()

    # Punto cerca del centro geografico de Bogota, cae dentro de
    # Teusaquillo (cod "13") -- verificado con shapely antes de escribir
    # este test.
    cod = ubicar_localidad(4.65, -74.1, geometria)

    assert cod == "13"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_localidad_lookup.py -v`
Expected: `ModuleNotFoundError: No module named 'localidad_lookup'`

- [ ] **Step 3: Write the implementation**

Create `app/localidad_lookup.py`:

```python
"""
localidad_lookup.py — Issue #36

Determina a que localidad de Bogota pertenece un punto (lat, lon), via
point-in-polygon sobre la geometria real de las 20 localidades (#33). No
lee archivos -- recibe la geometria ya cargada como parametro, mismo patron
de funciones puras del resto del proyecto (models/clustering/clustering.py,
src/feature_engineering.py).
"""
from __future__ import annotations

from shapely.geometry import Point, shape


def ubicar_localidad(lat: float, lon: float, geometria: dict) -> str | None:
    """cod_localidad de la zona que contiene (lat, lon), o None si esta
    fuera de las 20 localidades de Bogota (Issue #36, criterio: rechaza
    coordenadas fuera de Bogota).

    geometria es el GeoJSON de app/data/geometria_localidades.geojson
    (FeatureCollection, EPSG:4326 -- shapely.Point espera (lon, lat), no
    (lat, lon)).
    """
    punto = Point(lon, lat)
    for feature in geometria["features"]:
        poligono = shape(feature["geometry"])
        if poligono.contains(punto):
            return feature["properties"]["cod_localidad"]
    return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_localidad_lookup.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add app/localidad_lookup.py tests/test_localidad_lookup.py
git commit -m "feat(dashboard): agrega ubicar_localidad (point-in-polygon real) (issue #36)"
```

---

### Task 3: Report builder (`app/reporte_ciudadano.py::construir_reporte`)

**Files:**
- Create: `app/reporte_ciudadano.py` (this task only adds `construir_reporte`
  — Task 4 extends this same file with the Streamlit UI function)
- Create: `tests/test_reporte_ciudadano.py`

**Interfaces:**
- Consumes: `flag_zscore(cod_localidad, tipo_delito, conteo, linea_base) -> dict`
  from `src/flag_zscore.py` (#29, unmodified, imported verbatim).
- Produces: `construir_reporte(cod_localidad: str, tipo_delito: str, descripcion: str, lat: float, lon: float, linea_base: list[dict]) -> dict` —
  consumed by Task 4's UI function in this same module.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_reporte_ciudadano.py`:

```python
"""Tests para construir_reporte (Issue #36).

Usa una linea_base sintetica (no el fixture real de app/data/) -- mismo
patron que tests/test_flag_zscore.py (#29), funcion que este modulo
reutiliza tal cual.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from reporte_ciudadano import construir_reporte

LINEA_BASE_SINTETICA = [
    {"cod_localidad": "01", "tipo_delito": "A", "media": 100.0, "desviacion": 20.0},
    {"cod_localidad": "20", "tipo_delito": "HA", "media": 0.0, "desviacion": 0.0},
]


def test_construir_reporte_caso_comun_es_atipico_por_debajo():
    reporte = construir_reporte("01", "A", "vi algo raro", 4.7, -74.0, LINEA_BASE_SINTETICA)

    assert reporte["es_atipico"] is True
    assert reporte["z_score"] == pytest.approx(-4.95)
    assert reporte["descripcion"] == "vi algo raro"
    assert reporte["cod_localidad"] == "01"
    assert reporte["lat"] == 4.7
    assert reporte["lon"] == -74.0


def test_construir_reporte_caso_historial_nulo_es_atipico_senal_genuina():
    reporte = construir_reporte("20", "HA", "primera vez que pasa esto", 1.9, -74.2, LINEA_BASE_SINTETICA)

    assert reporte["es_atipico"] is True
    assert reporte["z_score"] is None


def test_construir_reporte_combo_inexistente_lanza_value_error():
    with pytest.raises(ValueError):
        construir_reporte("99", "ZZ", "x", 0.0, 0.0, LINEA_BASE_SINTETICA)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_reporte_ciudadano.py -v`
Expected: `ModuleNotFoundError: No module named 'reporte_ciudadano'`

- [ ] **Step 3: Write the implementation**

Create `app/reporte_ciudadano.py`:

```python
"""
reporte_ciudadano.py — Issue #36

Reporte ciudadano simulado: construye un reporte (localidad + tipo de
delito + descripcion + ubicacion) y lo evalua con flag_zscore() (#29,
src/flag_zscore.py, reutilizado tal cual, no reimplementado) contra la
linea base historica real (#26, app/data/linea_base_zscore.json).

Cada reporte se evalua de forma INDEPENDIENTE con conteo=1 (no un conteo
acumulado de la sesion): flag_zscore compara ese unico caso contra el
promedio HISTORICO ANUAL de esa localidad-tipo, asi que el resultado casi
siempre sale "por debajo del promedio" (z muy negativo) -- es la lectura
honesta, dado que 1 reporte nunca es comparable en escala a un promedio
anual. La excepcion real: localidades sin ningun historico para ese tipo
(desviacion=0), donde un solo reporte SI es una desviacion genuina (ver
docstring de flag_zscore para ese caso).

Sin base de datos: quien llama construir_reporte guarda el resultado en
st.session_state (ver la funcion de UI, agregada en un paso posterior de
este mismo modulo) -- se pierde al cerrar la sesion, decision de alcance ya
fijada en CLAUDE.md ss1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from flag_zscore import flag_zscore


def construir_reporte(
    cod_localidad: str,
    tipo_delito: str,
    descripcion: str,
    lat: float,
    lon: float,
    linea_base: list[dict],
) -> dict:
    """Construye un reporte evaluado contra la linea base real (#26).

    linea_base es la lista de dicts cod_localidad/tipo_delito/media/
    desviacion (formato de app/data/linea_base_zscore.json). Se evalua con
    conteo=1 (ver docstring del modulo). Lanza ValueError (de flag_zscore)
    si no hay linea base para (cod_localidad, tipo_delito).

    Devuelve un dict listo para st.session_state: los datos del reporte
    mas el resultado de flag_zscore (es_atipico, z_score, media,
    desviacion).
    """
    df_linea_base = pd.DataFrame(linea_base)
    resultado = flag_zscore(cod_localidad, tipo_delito, conteo=1, linea_base=df_linea_base)

    return {
        "cod_localidad": cod_localidad,
        "tipo_delito": tipo_delito,
        "descripcion": descripcion,
        "lat": lat,
        "lon": lon,
        **resultado,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_reporte_ciudadano.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add app/reporte_ciudadano.py tests/test_reporte_ciudadano.py
git commit -m "feat(dashboard): agrega construir_reporte, reutiliza flag_zscore real (issue #36)"
```

---

### Task 4: Form UI, map markers, deps, docs

**Files:**
- Modify: `app/data_loader.py` (add `cargar_linea_base()`)
- Modify: `app/reporte_ciudadano.py` (add the Streamlit form UI — extends
  Task 3's file, does not replace `construir_reporte`)
- Modify: `app/streamlit_app.py` (draw report markers, call the form)
- Modify: `app/requirements.txt` (add `pandas`, `shapely`)
- Modify: `app/README.md` (document the new feature)
- Modify: `BACKLOG.md` (mark Issue #36's 4 acceptance criteria complete)

**Interfaces:**
- Consumes: `construir_reporte(...)` (Task 3), `ubicar_localidad(...)`
  (Task 2), `app/data/linea_base_zscore.json` (Task 1).
- Produces: the running Streamlit app with the citizen report form — no
  other task depends on this one.

- [ ] **Step 1: Add `cargar_linea_base()` to `app/data_loader.py`**

Find this block near the top of `app/data_loader.py`:

```python
DATA_DIR = Path(__file__).resolve().parent / "data"
GEOMETRIA_PATH = DATA_DIR / "geometria_localidades.geojson"
RIESGO_PATH = DATA_DIR / "riesgo_por_zona.json"
TIPOLOGIA_PATH = DATA_DIR / "tipologia_zonas.json"
NUSE_PATH = DATA_DIR / "nuse_por_zona.json"
```

Add one more line:

```python
DATA_DIR = Path(__file__).resolve().parent / "data"
GEOMETRIA_PATH = DATA_DIR / "geometria_localidades.geojson"
RIESGO_PATH = DATA_DIR / "riesgo_por_zona.json"
TIPOLOGIA_PATH = DATA_DIR / "tipologia_zonas.json"
NUSE_PATH = DATA_DIR / "nuse_por_zona.json"
LINEA_BASE_PATH = DATA_DIR / "linea_base_zscore.json"
```

Add this function after `cargar_densidad_nuse` (at the end of the file):

```python
@st.cache_data
def cargar_linea_base() -> list[dict]:
    """Linea base historica real (#26): lista de dicts con cod_localidad,
    tipo_delito, media, desviacion. Consumida por
    app/reporte_ciudadano.py::construir_reporte (via flag_zscore, #29).
    """
    with open(LINEA_BASE_PATH, encoding="utf-8") as f:
        return json.load(f)
```

- [ ] **Step 2: Verify data_loader tests still pass**

Run: `.venv/Scripts/python -m pytest tests/test_data_loader.py -v`
Expected: `7 passed` (unchanged — this step only adds a new function, no
existing test should be affected; there's no new test for
`cargar_linea_base` itself, since it's a thin, obviously-correct wrapper
around the pattern already covered by this file's existing tests, and its
real behavior is exercised end-to-end by Task 4's own manual smoke test in
Step 6).

- [ ] **Step 3: Add the form UI to `app/reporte_ciudadano.py`**

Append this to the end of `app/reporte_ciudadano.py` (after
`construir_reporte`, keep everything from Task 3 as-is):

```python
import streamlit as st

import config  # src/ ya esta en sys.path por el sys.path.insert de la Tarea 3, arriba en este mismo archivo

from localidad_lookup import ubicar_localidad

AVISO_PRIVACIDAD = (
    "Los datos de este reporte (ubicación, tipo de delito, descripción) se "
    "usan únicamente para esta demostración, viven solo en tu sesión del "
    "navegador (no se guardan en ninguna base de datos) y se borran al "
    "cerrar la pestaña. No se comparten con terceros. Al continuar, aceptas "
    "el tratamiento de estos datos conforme a la Ley 1581 de 2012 "
    "(protección de datos personales, Colombia)."
)


def _mensaje_resultado(reporte: dict) -> None:
    if reporte["z_score"] is None:
        st.warning(
            ":material/report: Esta zona no tenía ningún caso histórico de "
            f"{reporte['tipo_delito']} en los datos de entrenamiento — tu "
            "reporte es una señal genuina de algo nuevo en esta localidad."
        )
        return

    st.info(
        f":material/info: Tu reporte es 1 caso puntual. El promedio "
        f"histórico anual para esta localidad y tipo de delito es de "
        f"{reporte['media']:.0f} casos (z={reporte['z_score']:.2f}) — es "
        "normal que un solo reporte quede muy por debajo de un promedio "
        "anual; esto no es una alerta de riesgo por sí solo."
    )


def render_formulario_reporte(zonas_riesgo: dict, linea_base: list[dict], ultimo_clic: dict | None) -> None:
    """Renderiza el formulario de reporte ciudadano (Issue #36).

    zonas_riesgo es el GeoJSON ya cargado por cargar_zonas_riesgo() (tiene
    la geometria real de las 20 localidades) -- se reutiliza aqui para
    ubicar_localidad(), sin cargar la geometria una segunda vez.

    ultimo_clic es el dict que devuelve st_folium() en 'last_clicked'
    ({"lat": .., "lng": ..}) de la corrida anterior del mapa, o None si
    todavia no se ha hecho clic (Issue #36, criterio: no rompe ante input
    faltante).
    """
    st.session_state.setdefault("reportes", [])
    st.session_state.setdefault("consentimiento_reporte", False)

    st.subheader(":material/campaign: Reporte ciudadano (simulado)")

    with st.expander("Aviso de privacidad", expanded=not st.session_state["consentimiento_reporte"]):
        st.write(AVISO_PRIVACIDAD)
        st.session_state["consentimiento_reporte"] = st.checkbox(
            "Acepto el tratamiento de mis datos para esta demostración",
            value=st.session_state["consentimiento_reporte"],
        )

    if not st.session_state["consentimiento_reporte"]:
        st.caption("Marca el checkbox de consentimiento para habilitar el formulario.")
        return

    if ultimo_clic is None:
        st.caption("Haz clic en el mapa para elegir la ubicación del reporte.")
        return

    lat, lon = ultimo_clic["lat"], ultimo_clic["lng"]
    cod_localidad = ubicar_localidad(lat, lon, zonas_riesgo)
    if cod_localidad is None:
        st.error("Esa ubicación está fuera de Bogotá. Haz clic dentro de una de las 20 localidades.")
        return

    with st.form("form_reporte_ciudadano", clear_on_submit=True):
        tipo_nombre = st.selectbox("Tipo de delito", options=list(config.SIEDCO_TIPOS.values()))
        descripcion = st.text_area("Descripción (requerida)")
        enviado = st.form_submit_button(":material/send: Enviar reporte")

    if enviado:
        if not descripcion.strip():
            st.error("La descripción es obligatoria.")
            return
        tipo_codigo = next(codigo for codigo, nombre in config.SIEDCO_TIPOS.items() if nombre == tipo_nombre)
        reporte = construir_reporte(cod_localidad, tipo_codigo, descripcion.strip(), lat, lon, linea_base)
        st.session_state["reportes"].append(reporte)
        _mensaje_resultado(reporte)
```

Note: Task 3 already ran `sys.path.insert(0, .../"src")` at module import
time (it's still in the file, unchanged) — that makes `src/` importable for
the rest of the module too, so this step's `import config` does **not**
need its own `sys.path.insert` call. Do not add one — it would be a
redundant duplicate of Task 3's. Only add the new `import streamlit as st`,
`import config`, and `from localidad_lookup import ubicar_localidad` lines
shown above, plus everything below `AVISO_PRIVACIDAD`.

- [ ] **Step 4: Wire markers and the form into `app/streamlit_app.py`**

Find the import block:

```python
from data_loader import cargar_zonas_riesgo, cargar_densidad_nuse
```

Replace with:

```python
from data_loader import cargar_zonas_riesgo, cargar_densidad_nuse, cargar_linea_base
from reporte_ciudadano import render_formulario_reporte
```

Find the start of `main()`:

```python
def main() -> None:
    st.set_page_config(page_title="Alerta Ciudadana", layout="wide")
    st.title("Alerta Ciudadana — Mapa de riesgo por zona")

    with st.sidebar:
```

Replace with:

```python
def main() -> None:
    st.set_page_config(page_title="Alerta Ciudadana", layout="wide")
    st.title("Alerta Ciudadana — Mapa de riesgo por zona")

    st.session_state.setdefault("reportes", [])

    with st.sidebar:
```

Find the end of `main()`:

```python
    if mostrar_tipologia:
        folium.GeoJson(
            zonas_riesgo,
            style_function=_estilo_tipologia,
            tooltip=folium.GeoJsonTooltip(
                fields=["localidad_nombre", "nombre_perfil"],
                aliases=["Localidad", "Perfil"],
            ),
        ).add_to(mapa)

    st_folium(mapa, height=600)


if __name__ == "__main__":
    main()
```

Replace with:

```python
    if mostrar_tipologia:
        folium.GeoJson(
            zonas_riesgo,
            style_function=_estilo_tipologia,
            tooltip=folium.GeoJsonTooltip(
                fields=["localidad_nombre", "nombre_perfil"],
                aliases=["Localidad", "Perfil"],
            ),
        ).add_to(mapa)

    for reporte in st.session_state["reportes"]:
        icono_nombre, color = ICONO_POR_ATIPICO[reporte["es_atipico"]]
        folium.Marker(
            location=[reporte["lat"], reporte["lon"]],
            popup=folium.Popup(
                f"<b>{config.SIEDCO_TIPOS.get(reporte['tipo_delito'], reporte['tipo_delito'])}</b>"
                f"<br>{reporte['descripcion']}",
                max_width=250,
            ),
            icon=folium.Icon(color=color, icon=icono_nombre, prefix="fa"),
        ).add_to(mapa)

    map_data = st_folium(mapa, height=600)

    linea_base = cargar_linea_base()
    render_formulario_reporte(zonas_riesgo, linea_base, (map_data or {}).get("last_clicked"))


if __name__ == "__main__":
    main()
```

Find the module-level constants block:

```python
COLOR_RIESGO = {1: "#e74c3c", 0: "#2ecc71"}
COLOR_TIPOLOGIA = {
    "Perfil de alto impacto generalizado": "#c0392b",
    "Perfil hurto de bienes / ingreso alto": "#f39c12",
    "Perfil de bajo incidente relativo": "#27ae60",
}
```

Add one more constant after it:

```python
COLOR_RIESGO = {1: "#e74c3c", 0: "#2ecc71"}
COLOR_TIPOLOGIA = {
    "Perfil de alto impacto generalizado": "#c0392b",
    "Perfil hurto de bienes / ingreso alto": "#f39c12",
    "Perfil de bajo incidente relativo": "#27ae60",
}
ICONO_POR_ATIPICO = {True: ("triangle-exclamation", "red"), False: ("circle-check", "green")}
```

- [ ] **Step 5: Add the new dependencies to `app/requirements.txt`**

`pandas==3.0.3` and `shapely==2.1.2` are already installed in this repo's
shared venv (confirmed: `pip show pandas shapely` reports these exact
versions, since they came in transitively via the root `requirements.txt`'s
`geopandas`) — no new `pip install` is needed, just declare them. Add these
two lines to `app/requirements.txt`:

```
pandas==3.0.3
shapely==2.1.2
```

- [ ] **Step 6: Smoke-test the app boots**

Same caveat as prior issues: no browser tool available, so this only
confirms the app **boots without crashing**, not that the form/markers
look right. Visual confirmation is the repo owner's job (see the Final
Checklist).

Run (background, headless, then check its output before killing it):

```bash
.venv/Scripts/streamlit run app/streamlit_app.py --server.headless true --server.port 8501
```

Expected within a few seconds: `You can now view your Streamlit app in your
browser.` and `Local URL: http://localhost:8501`, with **no Python
traceback**. Then:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
```

Expected: `200`. Stop the background Streamlit process afterward — it must
not be left running when you finish the task.

- [ ] **Step 7: Run the full test suite to confirm no regressions**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests pass (29 pre-existing + 3 from Task 2 + 3 from Task 3 =
35).

- [ ] **Step 8: Write `app/README.md` addition**

Add this new section to `app/README.md`, after the existing "## Las 3
capas del mapa (Issue #33)" section and before "## Datos: `app/data/`":

```markdown
## Reporte ciudadano simulado (Issue #36)

Haz clic en el mapa para elegir una ubicación, acepta el aviso de
privacidad, elige el tipo de delito y escribe una descripción — el reporte
se evalúa contra la línea base histórica real (Issue #26) con
`flag_zscore()` (Issue #29) y aparece como marcador en el mapa. Todo vive
en `st.session_state`: no hay base de datos, se pierde al cerrar la
pestaña (ver `CLAUDE.md` §1).

**Cómo leer el resultado:** cada reporte se evalúa solo (`conteo=1`) contra
un promedio **histórico anual** — por eso casi siempre sale "por debajo del
promedio" (un solo reporte nunca es comparable en escala a un año
completo). Esto es normal y se explica en el mensaje, no es una alerta de
peligro. La excepción real es una localidad sin ningún historial para ese
tipo de delito: ahí un solo reporte sí es una señal genuina.

Requiere `pandas` y `shapely` (agregados a `app/requirements.txt` en esta
issue — ambos ya estaban instalados en el venv compartido del repo, vía la
dependencia de `geopandas` del pipeline).
```

- [ ] **Step 9: Mark Issue #36 complete in BACKLOG.md**

In `BACKLOG.md`, find the section `### [CLUST] #36 — Reporte ciudadano
simulado en el dashboard + flag z-score (con Int. 4)` (around line 698) and
change its 4 acceptance criteria from `- [ ]` to `- [x]`:

```diff
 **Criterios de aceptación:**
-- [ ] El formulario añade un punto a la sesión y lo renderiza en el mapa.
-- [ ] El reporte dispara el flag z-score y muestra resultado interpretable.
-- [ ] Validación de input (rechaza coords fuera de Bogotá; campos requeridos; no rompe ante input ruidoso/faltante).
-- [ ] Checkbox de consentimiento opt-in + enlace al aviso de privacidad (Ley 1581/2012). **No se recorta.**
+- [x] El formulario añade un punto a la sesión y lo renderiza en el mapa.
+- [x] El reporte dispara el flag z-score y muestra resultado interpretable.
+- [x] Validación de input (rechaza coords fuera de Bogotá; campos requeridos; no rompe ante input ruidoso/faltante).
+- [x] Checkbox de consentimiento opt-in + enlace al aviso de privacidad (Ley 1581/2012). **No se recorta.**
```

Do not touch any other line or any other issue's checkboxes in this file.

- [ ] **Step 10: Commit**

```bash
git add app/data_loader.py app/reporte_ciudadano.py app/streamlit_app.py app/requirements.txt app/README.md BACKLOG.md
git commit -m "feat(dashboard): agrega formulario de reporte ciudadano + marcadores (issue #36)"
```

---

## Final Checklist

- [ ] The 4 acceptance criteria of Issue #36 (form adds a point rendered on
  the map, triggers the z-score flag with an interpretable result, input
  validation, opt-in consent checkbox not cut) are satisfied.
- [ ] `pytest tests/ -v` passes completely (35/35).
- [ ] `python -m compileall src pipelines tests` (what CI runs) does not
  fail. `app/` remains intentionally outside this invocation, same
  decision as Issues #32/#33.
- [ ] `BACKLOG.md` reflects Issue #36 as complete.
- [ ] No background `streamlit run` process was left running after Task 4
  Step 6.
- [ ] The repo owner does a final manual `streamlit run app/streamlit_app.py`
  and confirms visually: clicking the map, filling the form, submitting
  without consent (should block), submitting with an empty description
  (should error), submitting a valid report (should show an interpretable
  message and a marker with a non-emoji icon on the map). The smoke test
  in Task 4 only confirms the server boots and answers HTTP 200 — it
  cannot exercise the interactive click/form flow.
