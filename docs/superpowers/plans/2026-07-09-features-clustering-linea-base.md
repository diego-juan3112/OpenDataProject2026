# Features de perfil de zona + línea base z-score (Issue #26) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Producir la matriz de features de zona estandarizada (para K-Means en #27) y la línea base histórica media/desviación por localidad-tipo (para el flag z-score de #36), con las dos funciones puras que las calculan cubiertas por tests reales (los primeros del repo).

**Architecture:** Dos funciones puras y testeables en `src/feature_engineering.py` (reciben un `DataFrame`, no leen archivos — así los tests corren sin `data/`, que no existe en CI), un script orquestador nuevo en `models/clustering/build_features.py` que las invoca contra el dataset real y escribe los dos `.parquet` (gitignored, regenerables), y un diccionario de datos que documenta ambos artefactos.

**Tech Stack:** Python 3.14 (`.venv` del repo), pandas, pytest.

## Global Constraints

- **Sin fuga:** ambas funciones filtran `split == "train"` como primer paso — ninguna debe usar filas `split == "test"` (2025) para calcular tasas, estandarización o línea base.
- **Funciones puras:** `construir_features_zona(df)` y `calcular_linea_base(df)` reciben un `DataFrame` como parámetro y no leen ningún archivo — necesario porque `data/` no existe en CI (está en `.gitignore` y el pipeline de ingesta no corre ahí). Los tests usan un DataFrame sintético construido en el propio archivo de test.
- **Sumapaz:** único `cod_localidad` con `ipm_nbi` nulo en el dato real; se imputa con la mediana de las demás localidades, documentado explícitamente (no en silencio). La decisión final de tratamiento de Sumapaz en el clustering (incluir/excluir/cluster propio) queda para #27 — esta issue no la cierra.
- **Artefactos gitignored:** `models/clustering/features_zona.parquet` y `models/clustering/linea_base_zscore.parquet` caen bajo la regla global `*.parquet` de `.gitignore` — no se commitean, se regeneran corriendo `python models/clustering/build_features.py`.
- **Idioma:** docstrings, mensajes impresos y documentación en español, siguiendo la convención del resto del repositorio.

---

### Task 1: Funciones puras + tests (TDD)

**Files:**
- Modify: `src/feature_engineering.py`
- Create: `tests/test_feature_engineering.py`

**Interfaces:**
- Produces: `construir_features_zona(df, split_col="split", train_value="train") -> pd.DataFrame` (matriz localidad × features, estandarizada, indexada por `cod_localidad`) y `calcular_linea_base(df, split_col="split", train_value="train") -> pd.DataFrame` (columnas `cod_localidad, tipo_delito, media, desviacion`). Ambas consumidas por la Tarea 2.

- [ ] **Step 1: Escribir el test que falla primero**

Crear `tests/test_feature_engineering.py`:

```python
"""Tests para las features de perfil de zona y la linea base z-score (Issue #26).

Usan un DataFrame sintetico (no el parquet real): data/ no existe en CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from feature_engineering import construir_features_zona, calcular_linea_base


def _df_sintetico(incluir_test: bool = False) -> pd.DataFrame:
    """DataFrame sintetico con el esquema de dataset_analitico.parquet:
    3 localidades x 2 tipos de delito x 7 anios de train (2018-2024),
    mas opcionalmente 1 fila de test (2025) para la prueba de fuga.
    """
    filas = []
    anios_train = range(2018, 2025)  # 7 anios

    conteos = {
        ("01", "A"): [10, 10, 10, 10, 10, 10, 10],  # constante -> desviacion 0
        ("01", "B"): [1, 2, 3, 4, 5, 6, 7],          # caso conocido: media 4, std ddof=1 ~2.1602
        ("02", "A"): [5, 15, 25, 5, 15, 25, 5],
        ("02", "B"): [20, 20, 20, 20, 20, 20, 20],
        ("03", "A"): [3, 6, 9, 3, 6, 9, 3],
        ("03", "B"): [50, 40, 30, 50, 40, 30, 50],
    }
    nuse_por_loc = {"01": 1000, "02": 2000, "03": 500}
    ipm_por_loc = {"01": 5.0, "02": 15.0, "03": np.nan}  # "03" simula a Sumapaz

    for (loc, tipo), valores in conteos.items():
        for anio, conteo in zip(anios_train, valores):
            filas.append({
                "cod_localidad": loc, "tipo_delito": tipo, "anio": anio,
                "conteo_siedco": conteo, "conteo_nuse": nuse_por_loc[loc],
                "poblacion": 100_000, "ipm_nbi": ipm_por_loc[loc], "split": "train",
            })

    if incluir_test:
        filas.append({
            "cod_localidad": "01", "tipo_delito": "A", "anio": 2025,
            "conteo_siedco": 999_999, "conteo_nuse": 1000,
            "poblacion": 100_000, "ipm_nbi": 5.0, "split": "test",
        })

    return pd.DataFrame(filas)


def test_features_zona_estandarizada_media_cero():
    df = _df_sintetico()
    features = construir_features_zona(df)

    assert features.shape == (3, 4)  # 3 localidades x (tasa_A, tasa_B, tasa_nuse, ipm_nbi)
    medias = features.mean()
    stds = features.std(ddof=0)
    assert medias.abs().max() < 1e-9
    assert (stds.round(6) == 1.0).all()


def test_ipm_nbi_sumapaz_se_imputa_con_mediana():
    df = _df_sintetico()
    features = construir_features_zona(df)
    # ipm_nbi crudo = [5.0, 15.0, NaN]; mediana de las 2 conocidas = 10.0.
    # Tras estandarizar, la localidad "03" (valor imputado == mediana) debe
    # quedar en 0 desviaciones estandar en la columna ipm_nbi.
    assert features.loc["03", "ipm_nbi"] == pytest.approx(0.0, abs=1e-9)


def test_linea_base_media_std_correctos():
    df = _df_sintetico()
    base = calcular_linea_base(df)

    fila = base[(base["cod_localidad"] == "01") & (base["tipo_delito"] == "B")].iloc[0]
    assert fila["media"] == pytest.approx(4.0)
    assert fila["desviacion"] == pytest.approx(2.160246899469287)

    fila_constante = base[(base["cod_localidad"] == "01") & (base["tipo_delito"] == "A")].iloc[0]
    assert fila_constante["media"] == pytest.approx(10.0)
    assert fila_constante["desviacion"] == pytest.approx(0.0)


def test_sin_fuga_solo_usa_train():
    df_sin_test = _df_sintetico(incluir_test=False)
    df_con_test = _df_sintetico(incluir_test=True)

    features_sin = construir_features_zona(df_sin_test)
    features_con = construir_features_zona(df_con_test)
    pd.testing.assert_frame_equal(features_sin, features_con)

    base_sin = calcular_linea_base(df_sin_test)
    base_con = calcular_linea_base(df_con_test)
    pd.testing.assert_frame_equal(base_sin, base_con)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_feature_engineering.py -v`
Expected: `ImportError` o `ModuleNotFoundError` — `construir_features_zona`/`calcular_linea_base` no existen todavía en `src/feature_engineering.py` (todos los tests fallan en el import).

- [ ] **Step 3: Implementar las dos funciones**

En `src/feature_engineering.py`, agregar estas dos funciones **después** de `add_target_riesgo_alto` y **antes** del bloque `if __name__ == "__main__":`:

```python
def construir_features_zona(
    df: pd.DataFrame,
    split_col: str = "split",
    train_value: str = "train",
) -> pd.DataFrame:
    """Matriz localidad x features estandarizada para el clustering (Issue #26).

    Usa SOLO `split == train_value` (sin fuga): tasa anual promedio por 100.000
    habitantes por tipo de delito, tasa de llamadas NUSE por 100.000 hab., y
    contexto socioeconomico (`ipm_nbi`). Sumapaz (unica localidad con `ipm_nbi`
    nulo) se imputa con la mediana de las demas localidades -- imputacion
    documentada, no en silencio; ver `docs/data-dictionaries/features_clustering.md`.
    La decision final de como tratar a Sumapaz en el clustering (incluir con
    este valor imputado, excluir, o cluster propio) queda para la Issue #27.

    Devuelve la matriz ya estandarizada (z-score, ddof=0, media 0 / desviacion 1
    por columna), indexada por `cod_localidad`, lista para `KMeans.fit(...)`.
    """
    train = df[df[split_col] == train_value].copy()

    train["tasa_anual"] = train["conteo_siedco"] / train["poblacion"] * 100000
    tasa_tipo = train.pivot_table(index="cod_localidad", columns="tipo_delito",
                                   values="tasa_anual", aggfunc="mean")
    tasa_tipo.columns = [f"tasa_{c}" for c in tasa_tipo.columns]

    # conteo_nuse/poblacion vienen repetidos por tipo dentro de una misma
    # localidad-anio (es una senal de zona-anio, no de zona-tipo); se deduplica
    # antes de promediar para no contar el mismo anio 11 veces.
    nuse = (train.drop_duplicates(subset=["cod_localidad", "anio"])
                 .assign(tasa_nuse_anual=lambda d: d["conteo_nuse"] / d["poblacion"] * 100000)
                 .groupby("cod_localidad")["tasa_nuse_anual"].mean()
                 .rename("tasa_nuse"))

    ipm = (train.drop_duplicates(subset=["cod_localidad"])
                .set_index("cod_localidad")["ipm_nbi"])
    ipm = ipm.fillna(ipm.median())

    features = tasa_tipo.join(nuse).join(ipm.rename("ipm_nbi"))
    return (features - features.mean()) / features.std(ddof=0)


def calcular_linea_base(
    df: pd.DataFrame,
    split_col: str = "split",
    train_value: str = "train",
) -> pd.DataFrame:
    """Linea base historica (media/desviacion) por localidad-tipo (Issue #26).

    Usa SOLO `split == train_value` (sin fuga). Media y desviacion estandar
    muestral (`ddof=1`) de `conteo_siedco` sobre los anios de entrenamiento,
    por (`cod_localidad`, `tipo_delito`). Es el insumo directo de `flag_zscore`
    (Issue #36): dado un conteo reciente para una localidad-tipo, #36 calculara
    `z = (conteo_reciente - media) / desviacion`. Esta funcion NO calcula ese
    z-score, solo produce la linea base contra la que se comparara.

    Algunas combinaciones (p. ej. Sumapaz en tipos de conteo casi nulo) pueden
    tener `desviacion == 0` si los 7 conteos anuales son identicos -- no se
    corrige aqui; documentado para que #36 evite dividir por cero.
    """
    train = df[df[split_col] == train_value]
    return (train.groupby(["cod_localidad", "tipo_delito"])["conteo_siedco"]
                 .agg(media="mean", desviacion=lambda s: s.std(ddof=1))
                 .reset_index())
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_feature_engineering.py -v`
Expected: `4 passed` (test_features_zona_estandarizada_media_cero, test_ipm_nbi_sumapaz_se_imputa_con_mediana, test_linea_base_media_std_correctos, test_sin_fuga_solo_usa_train).

- [ ] **Step 5: Commit**

```bash
git add src/feature_engineering.py tests/test_feature_engineering.py
git commit -m "feat(clustering): agrega construir_features_zona y calcular_linea_base + tests (issue #26)"
```

---

### Task 2: Script orquestador `models/clustering/build_features.py`

**Files:**
- Create: `models/clustering/build_features.py`

**Interfaces:**
- Consumes: `feature_engineering.construir_features_zona`, `feature_engineering.calcular_linea_base` (Tarea 1); `config.DATASET_ANALITICO` (ruta ya definida en `src/config.py`).
- Produces: `models/clustering/features_zona.parquet` y `models/clustering/linea_base_zscore.parquet` (gitignored, consumidos por #27/#36 — no por otra tarea de este plan).

- [ ] **Step 1: Crear el script**

Crear `models/clustering/build_features.py`:

```python
"""
build_features.py — Issue #26

Orquestador: features de perfil de zona (estandarizadas) + linea base
historica z-score, a partir de data/03_primary/dataset_analitico.parquet.
Escribe los dos entregables que desbloquean #27 (K-Means) y #36 (flag z-score).

Uso:
    python models/clustering/build_features.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
import config
import feature_engineering

OUT_DIR = Path(__file__).resolve().parent
FEATURES_PATH = OUT_DIR / "features_zona.parquet"
LINEA_BASE_PATH = OUT_DIR / "linea_base_zscore.parquet"


def run() -> None:
    print("== #26 Features de perfil de zona + linea base z-score ==")
    df = pd.read_parquet(config.DATASET_ANALITICO)

    features = feature_engineering.construir_features_zona(df)
    features.to_parquet(FEATURES_PATH)

    linea_base = feature_engineering.calcular_linea_base(df)
    linea_base.to_parquet(LINEA_BASE_PATH, index=False)

    _verificar(features, linea_base)


def _verificar(features: pd.DataFrame, linea_base: pd.DataFrame) -> None:
    print(f"  features_zona: {features.shape[0]} localidades x {features.shape[1]} columnas")
    assert features.shape == (20, 13), "forma inesperada de la matriz de features"
    print(f"  media por columna (desviacion max respecto a 0): {features.mean().abs().max():.2e}")
    print(f"  std por columna (debe ser 1.0): {features.std(ddof=0).round(3).to_dict()}")

    print(f"  linea_base: {linea_base.shape[0]} filas (esperado 220 = 20 localidades x 11 tipos)")
    assert linea_base.shape[0] == 220, "conteo de filas inesperado en la linea base"
    ceros = linea_base[linea_base["desviacion"] == 0]
    print(f"  filas con desviacion == 0 (revisar en #36 antes de dividir): {len(ceros)}")
    if len(ceros):
        print(ceros.to_string(index=False))

    print(f"\n  [ok] {FEATURES_PATH}")
    print(f"  [ok] {LINEA_BASE_PATH}")


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Correr el script contra el dataset real y verificar**

Run: `.venv/Scripts/python.exe models/clustering/build_features.py`
Expected (entre otras líneas):
```
  features_zona: 20 localidades x 13 columnas
  linea_base: 220 filas (esperado 220 = 20 localidades x 11 tipos)
  filas con desviacion == 0 (revisar en #36 antes de dividir): 4
cod_localidad tipo_delito  media  desviacion
           20          HA    0.0         0.0
           20          HB    0.0         0.0
           20         HCE    0.0         0.0
           20          HR    0.0         0.0

  [ok] models/clustering/features_zona.parquet
  [ok] models/clustering/linea_base_zscore.parquet
```

- [ ] **Step 3: Verificar que los dos parquet quedan fuera de git (regla global `*.parquet`)**

Run: `git status --short models/clustering/`
Expected: sin salida (los `.parquet` recién escritos no aparecen como untracked — confirma que `.gitignore` los excluye). Si aparecieran, **detenerse y reportar BLOCKED** antes de commitear nada — significaría que `.gitignore` no los está cubriendo como se espera.

- [ ] **Step 4: Commit**

```bash
git add models/clustering/build_features.py
git commit -m "feat(clustering): agrega script orquestador build_features.py (issue #26)"
```

---

### Task 3: Diccionario de datos

**Files:**
- Create: `docs/data-dictionaries/features_clustering.md`
- Modify: `docs/data_dictionary.md`

**Interfaces:**
- Consumes: ningún código — solo documenta los artefactos producidos por las Tareas 1-2 (usa los números reales ya verificados en este plan).
- Produces: nada consumido por código; es el entregable de "documentada" del criterio de aceptación 1.

- [ ] **Step 1: Crear el diccionario**

Crear `docs/data-dictionaries/features_clustering.md`:

```markdown
# Features de perfil de zona + línea base z-score (Issue #26)

**Responsable:** Integrante 3 (Clustering) · **Estado:** calculado, insumo directo
de #27 (K-Means) y #36 (flag z-score) · **Fecha:** 2026-07-09

Este documento define las dos salidas de la Issue #26, generadas por
`python models/clustering/build_features.py` a partir de
`data/03_primary/dataset_analitico.parquet`. Ninguna de las dos se versiona en
git (`.gitignore`, regla global `*.parquet`) — se regeneran corriendo el script.

---

## 1. `models/clustering/features_zona.parquet`

Matriz **20 localidades × 13 columnas**, indexada por `cod_localidad`, calculada
**solo con `split == "train"` (2018–2024)** y **ya estandarizada** (z-score,
media 0 / desviación 1 por columna) — lista para `KMeans.fit(...)` en #27 sin
transformación adicional.

| Columna | Qué mide | Cómo se calcula |
|---|---|---|
| `tasa_<tipo_delito>` (11 columnas: `tasa_H`, `tasa_LP`, `tasa_HP`, `tasa_HR`, `tasa_HA`, `tasa_HB`, `tasa_HC`, `tasa_HCE`, `tasa_HM`, `tasa_DS`, `tasa_VI`) | Tasa anual promedio de ese tipo de delito, por 100.000 habitantes | Por año: `conteo_siedco / poblacion * 100000`; promedio sobre los 7 años train |
| `tasa_nuse` | Tasa anual promedio de llamadas a la Línea 123, por 100.000 habitantes | Igual que arriba con `conteo_nuse`, deduplicando el valor (repetido por tipo dentro de una misma localidad-año) antes de promediar |
| `ipm_nbi` | Contexto socioeconómico (pobreza multidimensional, Censo 2018) | Valor estático por localidad; **Sumapaz (única con valor nulo, sin Encuesta Multipropósito) se imputa con la mediana de las otras 19** (mediana real: 5.08) |

### Por qué tasas por 100k (no conteos crudos)

Mismo razonamiento que el EDA de #25: la población varía en órdenes de magnitud
entre localidades (Sumapaz ~3.172 hab. vs. Suba >1.2M), así que comparar
conteos crudos sesgaría el clustering hacia las localidades más grandes.
Ejemplo real: `tasa_HP` (Hurto Personas) va de **26.7/100k en Sumapaz** a
**8.389.97/100k en localidad 14 (Los Mártires)** — casi tres órdenes de
magnitud, imposible de comparar con conteos crudos.

### Decisión de imputación de Sumapaz

Sumapaz es la única localidad sin `ipm_nbi` (no cubierta por la Encuesta
Multipropósito). Se imputa con la **mediana de las otras 19 localidades**
(5.08), documentado explícitamente — no se descarta la fila ni se deja `NaN`
(rompería el z-score de toda la matriz). **Esta imputación no decide el
tratamiento final de Sumapaz en el clustering**: #27 debe decidir explícitamente
si la incluye con este valor, la excluye, o la trata como cluster propio (ver
`docs/HANDOFF_INT1.md`, sección "Lo que NO está resuelto").

---

## 2. `models/clustering/linea_base_zscore.parquet`

Tabla de **220 filas** (20 localidades × 11 tipos de delito), columnas
`cod_localidad, tipo_delito, media, desviacion`, calculada **solo con
`split == "train"`**: media y desviación estándar muestral (`ddof=1`) de
`conteo_siedco` sobre los 7 conteos anuales (2018–2024) de cada combinación
localidad-tipo.

Es el insumo directo de `flag_zscore` (#36): dado un conteo reciente para una
localidad-tipo, #36 calculará `z = (conteo_reciente - media) / desviacion`.
**Esta issue no implementa `flag_zscore`**, solo produce y guarda la línea
base contra la que se comparará.

### Caso de desviación cero

**4 de las 220 filas tienen `desviacion == 0`** — todas en Sumapaz (`cod_localidad
"20"`), en los tipos Hurto Automotores, Hurto Bicicletas, Hurto Celulares y
Hurto Residencias: los 7 conteos anuales son `0` en los siete años train (media
`0.0`, desviación `0.0`). **#36 debe evitar dividir por cero** en estas 4
combinaciones al calcular el z-score (p. ej. tratar cualquier conteo positivo
reportado ahí como automáticamente anómalo, dado que el histórico es
consistentemente cero).

---

## 3. Sin fuga

Ambas salidas se calculan filtrando `split == "train"` como primer paso — las
filas `split == "test"` (2025) nunca intervienen ni en las tasas/estandarización
de la matriz de features ni en la media/desviación de la línea base. Verificado
con un test dedicado (`tests/test_feature_engineering.py::test_sin_fuga_solo_usa_train`).
```

- [ ] **Step 2: Agregar la entrada al índice `docs/data_dictionary.md`**

Editar la tabla "Diccionarios por fuente de origen" en `docs/data_dictionary.md`:

Antes:
```
| Variable objetivo `riesgo_alto` (#10) | [`data-dictionaries/variable_objetivo.md`](data-dictionaries/variable_objetivo.md) |
| Reporte de calidad (Issue #7) | [`data-dictionaries/reporte_calidad.md`](data-dictionaries/reporte_calidad.md) |
```

Después:
```
| Variable objetivo `riesgo_alto` (#10) | [`data-dictionaries/variable_objetivo.md`](data-dictionaries/variable_objetivo.md) |
| Features de zona + línea base z-score (#26) | [`data-dictionaries/features_clustering.md`](data-dictionaries/features_clustering.md) |
| Reporte de calidad (Issue #7) | [`data-dictionaries/reporte_calidad.md`](data-dictionaries/reporte_calidad.md) |
```

- [ ] **Step 3: Commit**

```bash
git add docs/data-dictionaries/features_clustering.md docs/data_dictionary.md
git commit -m "docs(clustering): agrega diccionario de features de zona + linea base z-score (issue #26)"
```

---

### Task 4: Marcar la Issue #26 como completa en `BACKLOG.md`

**Files:**
- Modify: `BACKLOG.md`

**Interfaces:**
- Consumes: el estado de las Tareas 1-3 (todas completas y revisadas).
- Produces: nada consumido por código.

- [ ] **Step 1: Marcar los 3 checkboxes**

En `BACKLOG.md`, dentro del bloque `### [CLUST] #26 — Features de perfil de zona + línea base z-score`:

Antes:
```
- [ ] Matriz localidad × features estandarizada y documentada.
- [ ] Línea base (media + desviación) por localidad–tipo de delito, calculada con los conteos anuales del histórico, y guardada.
- [ ] Sin fuga: la línea base solo usa histórico, no el reporte que se evaluará.
```

Después:
```
- [x] Matriz localidad × features estandarizada y documentada.
- [x] Línea base (media + desviación) por localidad–tipo de delito, calculada con los conteos anuales del histórico, y guardada.
- [x] Sin fuga: la línea base solo usa histórico, no el reporte que se evaluará.
```

- [ ] **Step 2: Verificación final — correr toda la suite de tests**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: `4 passed` (los 4 tests de la Tarea 1; ya no hay "no tests collected").

- [ ] **Step 3: Commit**

```bash
git add BACKLOG.md
git commit -m "docs(backlog): marca issue #26 (features de zona + linea base z-score) como completa"
```

---

## Notas para quien retome este trabajo (Issue #27)

- `models/clustering/features_zona.parquet` ya está estandarizado — #27 no debe
  volver a escalar/normalizar antes de `KMeans.fit`.
- La decisión de Sumapaz (incluir con `ipm_nbi` imputado, excluir, o cluster
  propio) sigue abierta — ver `docs/data-dictionaries/features_clustering.md`
  y `docs/HANDOFF_INT1.md`.
- `models/clustering/linea_base_zscore.parquet` tiene 4 filas con `desviacion
  == 0` (todas Sumapaz) — #36 debe manejarlas explícitamente al implementar
  `flag_zscore` para no dividir por cero.
