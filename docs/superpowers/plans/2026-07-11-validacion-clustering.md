# Validación interna del clustering — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Demostrar y documentar que la segmentación K-Means de #27 (k=3) es
estable y no arbitraria, cumpliendo los 3 criterios de aceptación del Issue
#28: silhouette por cluster, prueba de estabilidad ante semillas, y un
argumento formal de por qué la tipología aporta más que ordenar zonas por
conteo total.

**Architecture:** 4 funciones puras nuevas en `models/clustering/clustering.py`
(mismo patrón sin I/O que las de #27, testeables con datos sintéticos) + 1
función de agregación nueva en `src/feature_engineering.py` (mismo patrón que
`construir_features_zona`/`calcular_linea_base`) + 1 script orquestador
`models/clustering/validate.py` que las conecta contra el modelo real de #27
+ 1 documento de reporte con los resultados ya verificados.

**Tech Stack:** Python, pandas, scikit-learn (`silhouette_samples`,
`adjusted_rand_score`, `KMeans`), pytest.

## Global Constraints

- Cruce y agregaciones siempre por `cod_localidad` (nunca por nombre).
- Cualquier agregación sobre `dataset_analitico.parquet` usa **solo**
  `split == "train"` (sin fuga de 2025).
- `k=3`, `n_init=10`, `random_state=42` son los parámetros del modelo final
  de #27 — no se reentrena ni se cambia el modelo, solo se valida.
- Semillas de estabilidad: `range(0, 10)`.
- Los tests usan datos **sintéticos**, nunca leen `data/` ni
  `models/clustering/*.parquet` (esos archivos no están versionados y no
  existen en CI).
- No se generan figuras nuevas; el reporte es texto + tablas.

---

### Task 1: `conteo_total_por_zona` en `src/feature_engineering.py`

**Files:**
- Modify: `src/feature_engineering.py` (agregar función al final del módulo,
  antes del bloque `if __name__ == "__main__":`)
- Test: `tests/test_feature_engineering.py`

**Interfaces:**
- Produces: `conteo_total_por_zona(df: pd.DataFrame, split_col: str = "split", train_value: str = "train") -> pd.Series`
  — serie indexada por `cod_localidad`, nombre `conteo_total`, suma de
  `conteo_siedco` sobre todos los `tipo_delito` y años de `train`.

- [ ] **Step 1: Escribir el test que falla**

Añade al final de `tests/test_feature_engineering.py` (reusa el import ya
existente en la línea 16, agregando el nombre nuevo):

```python
def test_conteo_total_por_zona_suma_solo_train():
    df = _df_sintetico()
    conteo = conteo_total_por_zona(df)

    # "01": tipo A = 10*7=70, tipo B = 1+2+3+4+5+6+7=28 -> 98
    # "02": tipo A = 5+15+25+5+15+25+5=95, tipo B = 20*7=140 -> 235
    # "03": tipo A = 3+6+9+3+6+9+3=39, tipo B = 50+40+30+50+40+30+50=290 -> 329
    assert conteo.loc["01"] == 98
    assert conteo.loc["02"] == 235
    assert conteo.loc["03"] == 329
    assert conteo.name == "conteo_total"


def test_conteo_total_por_zona_sin_fuga():
    df_sin_test = _df_sintetico(incluir_test=False)
    df_con_test = _df_sintetico(incluir_test=True)

    conteo_sin = conteo_total_por_zona(df_sin_test)
    conteo_con = conteo_total_por_zona(df_con_test)
    pd.testing.assert_series_equal(conteo_sin, conteo_con)
```

Actualiza el import de la línea 16 a:

```python
from feature_engineering import (
    construir_features_zona,
    calcular_linea_base,
    conteo_total_por_zona,
)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `.venv/Scripts/python -m pytest tests/test_feature_engineering.py -v`
Expected: `ImportError: cannot import name 'conteo_total_por_zona'`

- [ ] **Step 3: Implementar la función**

Añade en `src/feature_engineering.py`, justo antes de `if __name__ == "__main__":`:

```python
def conteo_total_por_zona(
    df: pd.DataFrame,
    split_col: str = "split",
    train_value: str = "train",
) -> pd.Series:
    """Conteo total de conteo_siedco por localidad, SOLO train (Issue #28).

    Suma conteo_siedco de todos los tipos de delito y anios de entrenamiento
    para cada cod_localidad. Es el insumo del baseline trivial de
    `terciles_por_conteo` (models/clustering/clustering.py): un ordenamiento
    de zonas por volumen bruto, sin normalizar por poblacion ni distinguir
    tipo de delito, para contrastar contra la tipologia real de K-Means.

    Devuelve una serie indexada por cod_localidad, nombre `conteo_total`.
    """
    train = df[df[split_col] == train_value]
    return train.groupby("cod_localidad")["conteo_siedco"].sum().rename("conteo_total")
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `.venv/Scripts/python -m pytest tests/test_feature_engineering.py -v`
Expected: `6 passed` (las 4 existentes + las 2 nuevas)

- [ ] **Step 5: Commit**

Da estos comandos al usuario para que los ejecute (nunca corras `git add`/`git commit` tú mismo en este proyecto):

```bash
git add src/feature_engineering.py tests/test_feature_engineering.py
git commit -m "feat(clustering): agrega conteo_total_por_zona para el baseline trivial (issue #28)"
```

---

### Task 2: `silhouette_por_cluster` en `models/clustering/clustering.py`

**Files:**
- Modify: `models/clustering/clustering.py` (agregar import y función al final)
- Test: `tests/test_validacion_clustering.py` (nuevo archivo)

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `silhouette_por_cluster(features: pd.DataFrame, modelo: KMeans) -> pd.DataFrame`
  — columnas `cluster, n, silhouette_medio, silhouette_min`.

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_validacion_clustering.py`:

```python
"""Tests para la validacion interna del clustering (Issue #28).

Usan matrices/etiquetas sinteticas (no el parquet real): data/ y
models/clustering/*.parquet no existen en CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
from sklearn.cluster import KMeans

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "models" / "clustering"))

from clustering import silhouette_por_cluster


def _features_2_grupos_separados() -> pd.DataFrame:
    """8 zonas en 2 grupos muy separados (2 features): A1-A4 cerca de (0,0),
    B1-B4 cerca de (10,10). Separacion clara -> silhouette alto esperado.
    """
    filas = {
        "A1": {"x": 0.0, "y": 0.0},
        "A2": {"x": 0.1, "y": -0.1},
        "A3": {"x": -0.1, "y": 0.1},
        "A4": {"x": 0.05, "y": 0.05},
        "B1": {"x": 10.0, "y": 10.0},
        "B2": {"x": 10.1, "y": 9.9},
        "B3": {"x": 9.9, "y": 10.1},
        "B4": {"x": 10.05, "y": 10.05},
    }
    df = pd.DataFrame(filas).T
    df.index.name = "cod_localidad"
    return df


def test_silhouette_por_cluster_ambos_grupos_cohesivos():
    features = _features_2_grupos_separados()
    modelo = KMeans(n_clusters=2, n_init=10, random_state=42).fit(features.values)

    resumen = silhouette_por_cluster(features, modelo)

    assert list(resumen.columns) == ["cluster", "n", "silhouette_medio", "silhouette_min"]
    assert resumen["n"].tolist() == [4, 4]
    assert (resumen["silhouette_medio"] > 0.9).all()
    assert resumen["silhouette_medio"].iloc[0] == pytest.approx(0.9888, abs=0.001)
    assert resumen["silhouette_min"].iloc[0] == pytest.approx(0.9863, abs=0.001)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `.venv/Scripts/python -m pytest tests/test_validacion_clustering.py -v`
Expected: `ImportError: cannot import name 'silhouette_por_cluster'`

- [ ] **Step 3: Implementar la función**

En `models/clustering/clustering.py`, cambia el import de la línea 11-12 de:

```python
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
```

a:

```python
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, silhouette_samples, adjusted_rand_score
```

Añade al final del archivo (después de `construir_zona_cluster`):

```python
def silhouette_por_cluster(features: pd.DataFrame, modelo: KMeans) -> pd.DataFrame:
    """Silhouette medio y minimo por cluster (Issue #28).

    A diferencia de evaluar_k (que reporta un unico silhouette global por k),
    esta funcion desagrega por cluster: un cluster grande y cohesivo puede
    esconder un cluster pequeno y debil en el promedio global.

    Devuelve un DataFrame con columnas cluster, n, silhouette_medio,
    silhouette_min, ordenado por cluster.
    """
    etiquetas = modelo.predict(features.values)
    valores = silhouette_samples(features.values, etiquetas)
    detalle = pd.DataFrame({"cluster": etiquetas, "silhouette": valores})
    return (detalle.groupby("cluster")["silhouette"]
                    .agg(n="count", silhouette_medio="mean", silhouette_min="min")
                    .reset_index())
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `.venv/Scripts/python -m pytest tests/test_validacion_clustering.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add models/clustering/clustering.py tests/test_validacion_clustering.py
git commit -m "feat(clustering): agrega silhouette_por_cluster (issue #28)"
```

---

### Task 3: `comparar_particiones` en `models/clustering/clustering.py`

**Files:**
- Modify: `models/clustering/clustering.py`
- Test: `tests/test_validacion_clustering.py`

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `comparar_particiones(etiquetas_a, etiquetas_b) -> float`
  — Adjusted Rand Index entre dos particiones (acepta listas, arrays o
  `pd.Series`).

- [ ] **Step 1: Escribir el test que falla**

Añade a `tests/test_validacion_clustering.py` (actualiza el import de la
línea 16 para incluir el nombre nuevo):

```python
from clustering import silhouette_por_cluster, comparar_particiones
```

```python
def test_comparar_particiones_identica_da_ari_uno():
    et_a = [0, 0, 0, 0, 1, 1, 1, 1]
    et_b = [0, 0, 0, 0, 1, 1, 1, 1]
    assert comparar_particiones(et_a, et_b) == pytest.approx(1.0)


def test_comparar_particiones_es_invariante_a_permutar_numeros_de_cluster():
    et_a = [0, 0, 0, 0, 1, 1, 1, 1]
    et_b_permutada = [1, 1, 1, 1, 0, 0, 0, 0]  # mismos grupos, etiquetas invertidas
    assert comparar_particiones(et_a, et_b_permutada) == pytest.approx(1.0)


def test_comparar_particiones_sin_relacion_da_ari_bajo():
    et_a = [0, 0, 0, 0, 1, 1, 1, 1]
    et_b_intercalada = [0, 1, 0, 1, 0, 1, 0, 1]  # no respeta los grupos de et_a
    assert comparar_particiones(et_a, et_b_intercalada) == pytest.approx(-0.1667, abs=0.001)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `.venv/Scripts/python -m pytest tests/test_validacion_clustering.py -v`
Expected: `ImportError: cannot import name 'comparar_particiones'`

- [ ] **Step 3: Implementar la función**

Añade en `models/clustering/clustering.py`, después de `silhouette_por_cluster`:

```python
def comparar_particiones(etiquetas_a, etiquetas_b) -> float:
    """Adjusted Rand Index entre dos particiones (Issue #28).

    Invariante a como se numeren los clusters (una permutacion de etiquetas
    da el mismo ARI): compara si las MISMAS zonas quedan agrupadas juntas,
    no si los numeros de cluster coinciden. Se reutiliza tanto para la
    prueba de estabilidad de semillas como para comparar contra el baseline
    trivial de terciles por conteo.
    """
    return adjusted_rand_score(etiquetas_a, etiquetas_b)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `.venv/Scripts/python -m pytest tests/test_validacion_clustering.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add models/clustering/clustering.py tests/test_validacion_clustering.py
git commit -m "feat(clustering): agrega comparar_particiones (ARI) (issue #28)"
```

---

### Task 4: `evaluar_estabilidad_semillas` en `models/clustering/clustering.py`

**Files:**
- Modify: `models/clustering/clustering.py`
- Test: `tests/test_validacion_clustering.py`

**Interfaces:**
- Consumes: `comparar_particiones(etiquetas_a, etiquetas_b) -> float` (Task 3).
- Produces: `evaluar_estabilidad_semillas(features: pd.DataFrame, etiquetas_referencia, k: int, semillas: Iterable[int], n_init: int = 10) -> pd.DataFrame`
  — columnas `semilla, ari`.

- [ ] **Step 1: Escribir el test que falla**

Actualiza el import en `tests/test_validacion_clustering.py`:

```python
from clustering import (
    silhouette_por_cluster,
    comparar_particiones,
    evaluar_estabilidad_semillas,
)
```

Añade:

```python
def test_evaluar_estabilidad_semillas_particion_separada_es_perfectamente_estable():
    features = _features_2_grupos_separados()
    modelo_referencia = KMeans(n_clusters=2, n_init=10, random_state=42).fit(features.values)
    etiquetas_referencia = modelo_referencia.predict(features.values)

    tabla = evaluar_estabilidad_semillas(features, etiquetas_referencia, k=2, semillas=[0, 1, 2])

    assert list(tabla.columns) == ["semilla", "ari"]
    assert tabla["semilla"].tolist() == [0, 1, 2]
    assert (tabla["ari"] == pytest.approx(1.0)).all()
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `.venv/Scripts/python -m pytest tests/test_validacion_clustering.py -v`
Expected: `ImportError: cannot import name 'evaluar_estabilidad_semillas'`

- [ ] **Step 3: Implementar la función**

Añade en `models/clustering/clustering.py`, después de `comparar_particiones`:

```python
def evaluar_estabilidad_semillas(
    features: pd.DataFrame,
    etiquetas_referencia,
    k: int,
    semillas,
    n_init: int = 10,
) -> pd.DataFrame:
    """ARI de K-Means reentrenado con cada semilla vs. las etiquetas de
    referencia (Issue #28).

    etiquetas_referencia son las del modelo final ya entrenado (p. ej.
    random_state=42). Para cada semilla en `semillas` se reentrena un
    K-Means nuevo con ese random_state y se compara contra la referencia
    con comparar_particiones. ARI cercano a 1.0 en todas las semillas
    indica que la particion no depende de la inicializacion aleatoria.

    Devuelve un DataFrame con columnas semilla, ari.
    """
    filas = []
    for semilla in semillas:
        modelo = KMeans(n_clusters=k, n_init=n_init, random_state=semilla)
        etiquetas = modelo.fit_predict(features.values)
        filas.append({
            "semilla": semilla,
            "ari": comparar_particiones(etiquetas_referencia, etiquetas),
        })
    return pd.DataFrame(filas)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `.venv/Scripts/python -m pytest tests/test_validacion_clustering.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add models/clustering/clustering.py tests/test_validacion_clustering.py
git commit -m "feat(clustering): agrega evaluar_estabilidad_semillas (issue #28)"
```

---

### Task 5: `terciles_por_conteo` en `models/clustering/clustering.py`

**Files:**
- Modify: `models/clustering/clustering.py`
- Test: `tests/test_validacion_clustering.py`

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `terciles_por_conteo(conteo_total: pd.Series, k: int) -> pd.Series`
  — enteros `0..k-1`, mismo índice que `conteo_total`.

- [ ] **Step 1: Escribir el test que falla**

Actualiza el import en `tests/test_validacion_clustering.py`:

```python
from clustering import (
    silhouette_por_cluster,
    comparar_particiones,
    evaluar_estabilidad_semillas,
    terciles_por_conteo,
)
```

Añade:

```python
def test_terciles_por_conteo_corta_en_3_grupos_ordenados():
    conteo = pd.Series(
        {"01": 10, "02": 20, "03": 30, "04": 40, "05": 50, "06": 60},
        name="conteo_total",
    )

    terciles = terciles_por_conteo(conteo, k=3)

    assert terciles.loc["01"] == 0
    assert terciles.loc["02"] == 0
    assert terciles.loc["03"] == 1
    assert terciles.loc["04"] == 1
    assert terciles.loc["05"] == 2
    assert terciles.loc["06"] == 2
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `.venv/Scripts/python -m pytest tests/test_validacion_clustering.py -v`
Expected: `ImportError: cannot import name 'terciles_por_conteo'`

- [ ] **Step 3: Implementar la función**

Añade en `models/clustering/clustering.py`, después de `evaluar_estabilidad_semillas`:

```python
def terciles_por_conteo(conteo_total: pd.Series, k: int) -> pd.Series:
    """Agrupa zonas en k grupos por conteo total, via cuantiles (Issue #28).

    Baseline trivial para contrastar contra la tipologia real de K-Means: un
    ordenamiento de una sola dimension (volumen bruto), sin las 13 features
    del perfil de zona. Usa el mismo k que el clustering real para que la
    comparacion (via comparar_particiones) sea directa.

    Devuelve una serie de enteros 0..k-1 (0 = grupo de menor conteo), mismo
    indice que conteo_total. Si hay empates que impiden cortar en
    exactamente k grupos, pd.qcut reduce el numero de grupos
    (duplicates="drop") en vez de fallar.
    """
    return pd.qcut(conteo_total, q=k, labels=False, duplicates="drop")
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `.venv/Scripts/python -m pytest tests/test_validacion_clustering.py -v`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add models/clustering/clustering.py tests/test_validacion_clustering.py
git commit -m "feat(clustering): agrega terciles_por_conteo (issue #28)"
```

---

### Task 6: Orquestador `models/clustering/validate.py`

**Files:**
- Create: `models/clustering/validate.py`

**Interfaces:**
- Consumes:
  - `clustering.silhouette_por_cluster(features, modelo) -> pd.DataFrame` (Task 2)
  - `clustering.comparar_particiones(etiquetas_a, etiquetas_b) -> float` (Task 3)
  - `clustering.evaluar_estabilidad_semillas(features, etiquetas_referencia, k, semillas, n_init) -> pd.DataFrame` (Task 4)
  - `clustering.terciles_por_conteo(conteo_total, k) -> pd.Series` (Task 5)
  - `feature_engineering.conteo_total_por_zona(df, split_col, train_value) -> pd.Series` (Task 1)
  - `config.DATASET_ANALITICO: Path` (ya existe en `src/config.py`)
- Produces: script ejecutable, sin artefactos serializados nuevos (solo
  imprime a consola — el reporte se documenta a mano en Task 7, mismo patrón
  que `train.py`/`clustering_perfiles.md` en #27).

No lleva test unitario propio: es un script de orquestación de I/O (lee
parquet/joblib reales), como `train.py` y `build_features.py`; se verifica
corriéndolo (Step 2).

- [ ] **Step 1: Crear el script**

Crea `models/clustering/validate.py`:

```python
"""
validate.py — Issue #28

Orquestador: valida que la segmentacion de #27 (K-Means, k=3) es estable y
no arbitraria. Corre las 3 pruebas del criterio de aceptacion (silhouette
por cluster, estabilidad ante semillas, comparacion contra el baseline
trivial de terciles por conteo) contra el modelo real serializado en
clusters.joblib, e imprime el resumen a consola. Los numeros se documentan
a mano en docs/data-dictionaries/validacion_clustering.md (mismo patron que
train.py -> clustering_perfiles.md en #27: este script no escribe el .md).

Uso:
    python models/clustering/validate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
import clustering
import config
import feature_engineering

SEMILLAS_ESTABILIDAD = range(10)

OUT_DIR = Path(__file__).resolve().parent
CLUSTERS_JOBLIB = OUT_DIR / "clusters.joblib"
FEATURES_PATH = OUT_DIR / "features_zona.parquet"


def run() -> None:
    print("== #28 Validacion interna del clustering ==")
    features = pd.read_parquet(FEATURES_PATH)
    bundle = joblib.load(CLUSTERS_JOBLIB)
    modelo = bundle["modelo"]
    nombres = bundle["nombre_perfil"]
    k = bundle["k"]
    n_init = bundle["n_init"]
    etiquetas_ref = modelo.predict(features.values)

    print("\n-- 1. Silhouette por cluster --")
    resumen_sil = clustering.silhouette_por_cluster(features, modelo)
    resumen_sil["nombre_perfil"] = resumen_sil["cluster"].map(nombres)
    print(resumen_sil.round(3).to_string(index=False))

    print("\n-- 2. Estabilidad ante semillas --")
    tabla_ari = clustering.evaluar_estabilidad_semillas(
        features, etiquetas_ref, k, SEMILLAS_ESTABILIDAD, n_init
    )
    print(tabla_ari.round(3).to_string(index=False))
    print(f"  media={tabla_ari['ari'].mean():.3f} min={tabla_ari['ari'].min():.3f} max={tabla_ari['ari'].max():.3f}")

    print("\n-- 3. Comparacion contra terciles por conteo total --")
    df = pd.read_parquet(config.DATASET_ANALITICO)
    conteo_total = feature_engineering.conteo_total_por_zona(df).reindex(features.index)
    terciles = clustering.terciles_por_conteo(conteo_total, k)
    ari_terciles = clustering.comparar_particiones(etiquetas_ref, terciles.values)
    print(f"  ARI (K-Means real vs. terciles por conteo total) = {ari_terciles:.3f}")
    crosstab = pd.crosstab(
        pd.Series(etiquetas_ref, index=features.index).map(nombres).rename("perfil_kmeans"),
        terciles.rename("tercil_conteo"),
    )
    print(crosstab.to_string())

    _verificar(resumen_sil, tabla_ari, ari_terciles)


def _verificar(resumen_sil: pd.DataFrame, tabla_ari: pd.DataFrame, ari_terciles: float) -> None:
    assert resumen_sil["n"].sum() == 20, "las 20 localidades deben quedar cubiertas"
    assert tabla_ari["ari"].between(-1.0, 1.0).all(), "ARI fuera de rango valido"
    assert -1.0 <= ari_terciles <= 1.0, "ARI fuera de rango valido"
    print("\n  [ok] validacion completa")


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Correr el script y verificar la salida**

Run: `.venv/Scripts/python models/clustering/validate.py`
Expected: imprime las 3 secciones y termina con `[ok] validacion completa`.
Los números deben coincidir con los ya verificados en el spec
(`docs/superpowers/specs/2026-07-11-validacion-clustering-design.md`):
silhouette medio por cluster ≈ 0.498 / 0.249 / 0.219, ARI de semillas = 1.0
en las 10, ARI vs. terciles ≈ 0.031.

- [ ] **Step 3: Correr toda la suite de tests para verificar que nada se rompió**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: todos los tests pasan (los de #1-#12, #26, #27 y los nuevos de #28).

- [ ] **Step 4: Commit**

```bash
git add models/clustering/validate.py
git commit -m "feat(clustering): agrega script orquestador validate.py (issue #28)"
```

---

### Task 7: Documentar el reporte en `docs/data-dictionaries/validacion_clustering.md`

**Files:**
- Create: `docs/data-dictionaries/validacion_clustering.md`

**Interfaces:**
- Consumes: la salida de consola de `models/clustering/validate.py` (Task 6).
- Produces: documento final que cierra los 3 criterios de aceptación de #28.

- [ ] **Step 1: Escribir el documento**

Crea `docs/data-dictionaries/validacion_clustering.md` con este contenido
(los números ya están verificados en el spec; si al correr `validate.py` en
Task 6 salieron distintos por cualquier cambio previo en el pipeline,
actualízalos aquí con los reales):

```markdown
# Validación interna del clustering — K-Means (Issue #28)

**Responsable:** Integrante 3 (Clustering) · **Estado:** validado contra el
modelo final de #27 · **Fecha:** 2026-07-11

Este documento valida que la segmentación de #27 (`k=3`, `n_init=10,
random_state=42`) es estable y no arbitraria. Generado corriendo
`python models/clustering/validate.py` contra `clusters.joblib` y
`features_zona.parquet` (#27) y `data/03_primary/dataset_analitico.parquet`
(#9). Los artefactos serializados no se versionan en git (regla global
`*.parquet`/`*.joblib` de `.gitignore`) — los números de este documento se
regeneran corriendo el script.

---

## 1. Silhouette por cluster

| Cluster | n | Nombre | silhouette medio | silhouette mín |
|---|---|---|---|---|
| 0 | 12 | Perfil de bajo incidente relativo | **0.498** | 0.387 |
| 1 | 2  | Perfil de alto impacto generalizado | 0.249 | 0.219 |
| 2 | 6  | Perfil hurto de bienes / ingreso alto | 0.219 | 0.037 |

El cluster grande (bajo incidente, 12 zonas) es el más cohesivo. Los otros
dos son más débiles — esperable con clusters pequeños (2 y 6 zonas) sobre 13
features: una zona del cluster "hurto de bienes" tiene silhouette casi cero
(0.037), en el límite de estar mal clasificada. Se documenta tal cual, sin
suavizar el resultado: el silhouette global de #27 (0.389) resume estos tres
valores, pero esconde que no todos los clusters son igual de sólidos.

## 2. Estabilidad ante semillas

10 semillas (`0..9`) reentrenadas y comparadas contra el modelo de
referencia (`random_state=42`) con Adjusted Rand Index (ARI: 1.0 =
partición idéntica, 0.0 = tan parecida como al azar):

| semilla | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| ARI | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

**ARI = 1.0 en las 10 semillas.** La partición es completamente estable: no
depende de la inicialización aleatoria de K-Means. Resultado fuerte a favor
de que la segmentación no es un artefacto de la semilla `random_state=42`
elegida en #27.

## 3. Por qué la tipología aporta más que ordenar zonas por conteo

Baseline trivial: cortar las 20 zonas en 3 terciles (`pd.qcut`) por el
conteo total de `conteo_siedco` (solo train, sin fuga — suma de todos los
tipos de delito y años), y comparar contra los clusters reales de K-Means
con ARI.

**ARI (K-Means real vs. terciles por conteo total) = 0.031** — prácticamente
sin relación entre las dos particiones. El crosstab lo confirma:

| perfil K-Means \ tercil conteo | bajo (0) | medio (1) | alto (2) |
|---|---|---|---|
| Alto impacto generalizado | 1 | 1 | 0 |
| Bajo incidente relativo | 4 | 2 | 6 |
| Hurto de bienes / ingreso alto | 2 | 3 | 1 |

**Ejemplo concreto: Candelaria** (perfil "alto impacto generalizado" en
K-Means) cae en el tercil **bajo** de conteo total. Es una localidad
pequeña en población con tasas por 100k habitantes muy altas, pero pocos
incidentes en términos absolutos — ordenar solo por conteo total la
escondería junto a zonas de bajo riesgo real, exactamente el error que la
tipología evita.

**Argumento:** el conteo total es una sola cifra cruda que mezcla volumen
delictivo con tamaño poblacional y no distingue tipo de delito. La
tipología de K-Means usa 13 features (11 tasas de delito por 100k, tasa de
llamadas NUSE, `ipm_nbi`), todas normalizadas por población y estandarizadas
— por eso separa, por ejemplo, "alto impacto generalizado" (alto en *todo*)
de "hurto de bienes / ingreso alto" (alto solo en delitos patrimoniales,
bajo en violencia), una distinción que un ranking de una sola dimensión no
puede capturar. Ver `clustering_perfiles.md` para la lectura completa de
cada perfil.

## 4. Conclusión

Los 3 criterios de aceptación de #28 quedan cubiertos: silhouette por
cluster reportado (con sus debilidades documentadas, no ocultas),
estabilidad perfecta ante 10 semillas distintas, y un argumento cuantitativo
(ARI=0.031) + cualitativo (Candelaria) de por qué la tipología no es
equivalente a ordenar zonas por volumen. No se encontraron motivos para
reentrenar o ajustar el modelo final de #27.
```

- [ ] **Step 2: Commit**

```bash
git add docs/data-dictionaries/validacion_clustering.md
git commit -m "docs(clustering): agrega reporte de validacion interna (issue #28)"
```

---

## Final Checklist

- [ ] Los 3 criterios de aceptación del Issue #28 (silhouette por cluster,
  estabilidad, argumento contra el conteo total) están cubiertos por
  `validacion_clustering.md`.
- [ ] `pytest tests/ -v` pasa completo (incluye #1-#12, #26, #27 y los tests
  nuevos de #28).
- [ ] `python -m compileall src pipelines tests` (lo que corre CI) no falla.
- [ ] `models/clustering/validate.py` corre de punta a punta sin errores.
- [ ] Actualizar `BACKLOG.md`: marcar el Issue #28 como completo (checkbox o
  nota de estado, según el formato usado para #26/#27 en ese archivo).
