# flag_zscore() Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver `flag_zscore()`, the anomaly-detection function that compares
a citizen-reported crime count against the historical baseline (#26) for a
given `(cod_localidad, tipo_delito)`, closing Issue #29's 3 acceptance
criteria.

**Architecture:** One pure function in a new dedicated module
(`src/flag_zscore.py`), taking the already-computed `linea_base` DataFrame
(from `calcular_linea_base`, #26) as an explicit parameter — no file I/O,
matching the rest of the codebase's pure-function convention. Fully covered
by synthetic-data tests.

**Tech Stack:** Python, pandas, pytest.

## Global Constraints

- `flag_zscore` takes `linea_base` as an explicit 4th parameter (pure
  function, no I/O) — deviates intentionally from the backlog's literal
  3-argument signature; this deviation is documented and justified in the
  spec (`docs/superpowers/specs/2026-07-11-flag-zscore-design.md`).
- Parameter is `cod_localidad` (never a free-text locality name — global
  project rule, always cross-reference by DANE code).
- Anomaly threshold: `UMBRAL_Z = 2.0` (module-level constant, `abs(z_score) >
  UMBRAL_Z`).
- `desviacion == 0` case: `es_atipico = (conteo != media)`, `z_score = None`
  (never divide by zero).
- Missing `(cod_localidad, tipo_delito)` combo: raise `ValueError` with a
  clear message — never return a default/misleading result.
- Tests use **synthetic** data only (an in-memory `linea_base` DataFrame),
  never read `data/` or `models/clustering/*.parquet`.
- No leakage surface to introduce: `linea_base` is already train-only from
  #26; this function only consumes it.

---

### Task 1: `flag_zscore()` in `src/flag_zscore.py`

**Files:**
- Create: `src/flag_zscore.py`
- Create: `tests/test_flag_zscore.py`
- Modify: `BACKLOG.md` (mark Issue #29's 3 acceptance criteria as complete,
  same convention used for #26/#27/#28: `- [ ]` → `- [x]` under `### [CLUST]
  #29 — Función \`flag_zscore()\` para el reporte ciudadano`)

**Interfaces:**
- Consumes: nothing from other tasks (this is the only task in this plan).
- Produces: `flag_zscore(cod_localidad: str, tipo_delito: str, conteo: float, linea_base: pd.DataFrame) -> dict`
  — returns `{"es_atipico": bool, "z_score": float | None, "media": float,
  "desviacion": float}`. This is the function Issue #36 (dashboard citizen
  report form) will import and call in a future issue — not built here.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_flag_zscore.py`:

```python
"""Tests para flag_zscore, el flag de anomalia del reporte ciudadano (Issue #29).

Usa una tabla de linea_base sintetica (no el parquet real de #26): data/ y
models/clustering/linea_base_zscore.parquet no existen en CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flag_zscore import flag_zscore, UMBRAL_Z


def _linea_base_sintetica() -> pd.DataFrame:
    """2 combinaciones localidad-tipo: una con variacion historica normal,
    otra con desviacion 0 (mismo escenario real de Sumapaz en #26, donde el
    conteo historico fue 0 los 7 anios de train).
    """
    return pd.DataFrame([
        {"cod_localidad": "01", "tipo_delito": "A", "media": 100.0, "desviacion": 20.0},
        {"cod_localidad": "20", "tipo_delito": "HA", "media": 0.0, "desviacion": 0.0},
    ])


def test_flag_zscore_caso_normal_no_atipico():
    linea_base = _linea_base_sintetica()
    resultado = flag_zscore("01", "A", conteo=120.0, linea_base=linea_base)

    assert resultado["z_score"] == pytest.approx(1.0)
    assert resultado["es_atipico"] is False
    assert resultado["media"] == pytest.approx(100.0)
    assert resultado["desviacion"] == pytest.approx(20.0)


def test_flag_zscore_caso_normal_atipico():
    linea_base = _linea_base_sintetica()
    resultado = flag_zscore("01", "A", conteo=150.0, linea_base=linea_base)

    assert resultado["z_score"] == pytest.approx(2.5)
    assert resultado["es_atipico"] is True


def test_flag_zscore_umbral_es_dos():
    assert UMBRAL_Z == 2.0


def test_flag_zscore_desviacion_cero_conteo_igual_a_media_no_es_atipico():
    linea_base = _linea_base_sintetica()
    resultado = flag_zscore("20", "HA", conteo=0.0, linea_base=linea_base)

    assert resultado["z_score"] is None
    assert resultado["es_atipico"] is False
    assert resultado["media"] == pytest.approx(0.0)
    assert resultado["desviacion"] == pytest.approx(0.0)


def test_flag_zscore_desviacion_cero_conteo_distinto_es_atipico():
    linea_base = _linea_base_sintetica()
    resultado = flag_zscore("20", "HA", conteo=1.0, linea_base=linea_base)

    assert resultado["z_score"] is None
    assert resultado["es_atipico"] is True


def test_flag_zscore_combo_inexistente_lanza_value_error():
    linea_base = _linea_base_sintetica()

    with pytest.raises(ValueError):
        flag_zscore("99", "ZZ", conteo=10.0, linea_base=linea_base)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_flag_zscore.py -v`
Expected: `ModuleNotFoundError: No module named 'flag_zscore'`

- [ ] **Step 3: Write the implementation**

Create `src/flag_zscore.py`:

```python
"""
flag_zscore.py — Issue #29

Deteccion de anomalias para el reporte ciudadano simulado: compara un conteo
reciente reportado por un ciudadano contra la linea base historica de #26
(media/desviacion por cod_localidad-tipo_delito, calculada SOLO con train).
No hace I/O -- recibe la tabla de linea_base ya calculada como parametro,
para ser testeable con datos sinteticos (mismo patron que
src/feature_engineering.py y models/clustering/clustering.py). Consumida por
el formulario de reporte del dashboard (Issue #36, no implementado aqui).
"""
from __future__ import annotations

import pandas as pd

UMBRAL_Z = 2.0  # |z| > 2 ~ 95%, umbral estandar para un flag simple de anomalia


def flag_zscore(
    cod_localidad: str,
    tipo_delito: str,
    conteo: float,
    linea_base: pd.DataFrame,
) -> dict:
    """Compara conteo contra el historico de (cod_localidad, tipo_delito).

    linea_base debe tener las columnas cod_localidad, tipo_delito, media,
    desviacion (formato exacto de calcular_linea_base en
    src/feature_engineering.py, Issue #26 -- ya filtrado a train, sin fuga).

    Casos:
    - Normal (desviacion > 0): z_score = (conteo - media) / desviacion;
      es_atipico = abs(z_score) > UMBRAL_Z.
    - desviacion == 0 (historico perfectamente constante, p. ej. Sumapaz en
      datos reales): z_score = None (la formula no aplica, se evita
      ZeroDivisionError); es_atipico = conteo != media -- cualquier cambio
      es significativo si el historico nunca vario.

    Lanza ValueError si (cod_localidad, tipo_delito) no esta en linea_base,
    en vez de devolver un resultado por defecto enganoso.

    Devuelve {"es_atipico": bool, "z_score": float | None, "media": float,
    "desviacion": float}.
    """
    fila = linea_base[
        (linea_base["cod_localidad"] == cod_localidad)
        & (linea_base["tipo_delito"] == tipo_delito)
    ]
    if fila.empty:
        raise ValueError(
            f"No hay linea base para cod_localidad={cod_localidad!r}, "
            f"tipo_delito={tipo_delito!r}."
        )

    media = fila["media"].iloc[0]
    desviacion = fila["desviacion"].iloc[0]

    if desviacion == 0:
        return {
            "es_atipico": conteo != media,
            "z_score": None,
            "media": media,
            "desviacion": desviacion,
        }

    z_score = (conteo - media) / desviacion
    return {
        "es_atipico": abs(z_score) > UMBRAL_Z,
        "z_score": z_score,
        "media": media,
        "desviacion": desviacion,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_flag_zscore.py -v`
Expected: `6 passed`

- [ ] **Step 5: Run the full test suite to confirm no regressions**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests pass (16 pre-existing from before this branch + 6 new = 22).

- [ ] **Step 6: Mark Issue #29 complete in BACKLOG.md**

In `BACKLOG.md`, find the section `### [CLUST] #29 — Función \`flag_zscore()\`
para el reporte ciudadano` (around line 586) and change its 3 acceptance
criteria from `- [ ]` to `- [x]`:

```diff
 **Criterios de aceptación:**
-- [ ] `flag_zscore(localidad, tipo_delito, conteo)` documentada y testeada con casos límite.
-- [ ] Acordada con la vista de reporte del dashboard (#36).
-- [ ] Sin fuga: usa solo la línea base histórica de #26.
+- [x] `flag_zscore(localidad, tipo_delito, conteo)` documentada y testeada con casos límite.
+- [x] Acordada con la vista de reporte del dashboard (#36).
+- [x] Sin fuga: usa solo la línea base histórica de #26.
```

Do not touch any other line or any other issue's checkboxes in this file.

- [ ] **Step 7: Commit**

```bash
git add src/flag_zscore.py tests/test_flag_zscore.py BACKLOG.md
git commit -m "feat(clustering): agrega flag_zscore para el reporte ciudadano (issue #29)"
```

---

## Final Checklist

- [ ] The 3 acceptance criteria of Issue #29 (function documented + tested
  with edge cases, ready for #36 to consume, no leakage) are satisfied.
- [ ] `pytest tests/ -v` passes completely (22/22).
- [ ] `python -m compileall src pipelines tests` (what CI runs) does not fail.
- [ ] `BACKLOG.md` reflects Issue #29 as complete.
