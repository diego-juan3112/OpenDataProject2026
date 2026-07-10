# Entrenar K-Means + tipología + clusters.joblib (Issue #27) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entrenar el K-Means final (k=3, justificado por codo + interpretabilidad) sobre `models/clustering/features_zona.parquet`, nombrar cada cluster por una regla sobre sus centroides reales, y serializar `models/clustering/clusters.joblib` + `models/clustering/zona_cluster.parquet` para la API y el dashboard.

**Architecture:** Funciones puras y testeables en `models/clustering/clustering.py` (reciben la matriz de features como parámetro, nunca leen archivos — mismo patrón que `src/feature_engineering.py` en #26, para poder testear con datos sintéticos sin depender de `data/`, que no existe en CI) más un orquestador `models/clustering/train.py` que corre todo contra el dataset real, guarda la figura de codo+silhouette y los dos artefactos finales.

**Tech Stack:** Python 3.14 (`.venv` del repo), pandas, scikit-learn, joblib, matplotlib, pytest.

## Global Constraints

- **Parámetros fijos y reproducibles:** `k=3`, `n_init=10`, `random_state=42`, guardados dentro de `clusters.joblib` (no solo impresos en consola).
- **k=3 está justificado por codo + interpretabilidad, no por silhouette máximo.** El silhouette más alto real es k=2 (0.492) pero da un corte binario poco útil; el codo real de la inercia está en k=3 (caída de la 2da derivada de −39.0, luego plano) y produce 3 perfiles genuinamente distintos. Esto debe quedar documentado explícitamente, no solo elegido en silencio.
- **Nombrado de clusters por regla sobre centroides, no por índice hardcodeado:** sklearn no garantiza que la etiqueta numérica de un cluster sea estable entre corridas/versiones; la regla de `nombrar_clusters` debe mirar los centroides del modelo ya entrenado, nunca asumir "el cluster 0 siempre es X".
- **Sumapaz no se fuerza a ningún resultado:** en K-Means real (a diferencia del jerárquico de #25) cae dentro del cluster grande de bajo incidente. Se documenta tal cual sale.
- **Funciones puras y testeables:** `evaluar_k`, `entrenar_kmeans_final`, `nombrar_clusters`, `construir_zona_cluster` reciben un DataFrame de features como parámetro y no leen archivos — los tests usan una matriz sintética, no `data/` ni `models/clustering/features_zona.parquet` (no existen en CI).
- **Idioma:** docstrings, mensajes y documentación en español.

---

### Task 1: Dependencias `scikit-learn` + `joblib`

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `scikit-learn` y `joblib` instalados y pineados en `requirements.txt`, usados por las Tareas 2-3.

- [ ] **Step 1: Agregar las dependencias**

Editar el final de `requirements.txt`:

Antes:
```
scipy==1.18.0          # EDA/#25 — regresión de tendencia (linregress) + dendrograma jerárquico
```

Después:
```
scipy==1.18.0          # EDA/#25 — regresión de tendencia (linregress) + dendrograma jerárquico
scikit-learn==1.9.0    # #27 — K-Means + silhouette para el clustering de perfiles de zona
joblib==1.5.3          # #27 — serializar clusters.joblib
```

- [ ] **Step 2: Instalar**

Run: `.venv/Scripts/pip.exe install -r requirements.txt`
Expected: termina sin errores; `scikit-learn` y `joblib` aparecen instalados (o ya satisfechos).

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore(deps): agrega scikit-learn y joblib para el clustering K-Means (issue #27)"
```

---

### Task 2: Funciones de clustering + tests (TDD)

**Files:**
- Create: `models/clustering/clustering.py`
- Create: `tests/test_clustering.py`

**Interfaces:**
- Produces: `evaluar_k(features, k_range, n_init=10, random_state=42) -> pd.DataFrame` (columnas `k, inercia, silhouette`), `entrenar_kmeans_final(features, k, n_init=10, random_state=42) -> KMeans`, `nombrar_clusters(features, modelo) -> dict[int, str]`, `construir_zona_cluster(features, modelo, nombres) -> pd.DataFrame` (columnas `cod_localidad, cluster, nombre_perfil`). Todas consumidas por la Tarea 3.

- [ ] **Step 1: Escribir el test que falla primero**

Crear `tests/test_clustering.py`:

```python
"""Tests para el clustering K-Means de perfiles de zona (Issue #27).

Usan una matriz de features sintetica (no el parquet real): data/ y
models/clustering/features_zona.parquet no existen en CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "models" / "clustering"))

from clustering import evaluar_k, entrenar_kmeans_final, nombrar_clusters, construir_zona_cluster

COLS_VIOLENTO = ["tasa_H", "tasa_DS", "tasa_VI", "tasa_LP"]
COLS_PATRIMONIAL = ["tasa_HA", "tasa_HB", "tasa_HC", "tasa_HCE", "tasa_HM", "tasa_HR", "tasa_HP"]
COLS_TIPO_DELITO = ["tasa_DS", "tasa_H", "tasa_HA", "tasa_HB", "tasa_HC", "tasa_HCE",
                     "tasa_HM", "tasa_HP", "tasa_HR", "tasa_LP", "tasa_VI"]
TODAS_COLS = COLS_TIPO_DELITO + ["tasa_nuse", "ipm_nbi"]


def _features_sinteticas() -> pd.DataFrame:
    """6 zonas sinteticas en 3 pares claramente separables (ya estandarizadas):
    Z1/Z2 = alto impacto en todo; Z3/Z4 = alto solo en patrimonial (bajo en
    violento, ipm bajo); Z5/Z6 = bajo en todo.
    """
    filas = {
        "Z1": {c: 2.0 for c in TODAS_COLS},
        "Z2": {c: 2.1 for c in TODAS_COLS},
        "Z3": {**{c: 1.5 for c in COLS_PATRIMONIAL}, **{c: -0.5 for c in COLS_VIOLENTO},
               "tasa_nuse": 0.5, "ipm_nbi": -1.0},
        "Z4": {**{c: 1.6 for c in COLS_PATRIMONIAL}, **{c: -0.4 for c in COLS_VIOLENTO},
               "tasa_nuse": 0.4, "ipm_nbi": -0.9},
        "Z5": {c: -0.8 for c in TODAS_COLS},
        "Z6": {c: -0.7 for c in TODAS_COLS},
    }
    synth = pd.DataFrame(filas).T
    synth.index.name = "cod_localidad"
    return synth[TODAS_COLS]


def test_evaluar_k_detecta_la_separacion_clara_en_k3():
    features = _features_sinteticas()
    tabla = evaluar_k(features, range(2, 5))

    assert list(tabla["k"]) == [2, 3, 4]
    fila_k3 = tabla[tabla["k"] == 3].iloc[0]
    assert fila_k3["silhouette"] == pytest.approx(0.9416, abs=0.01)
    assert fila_k3["silhouette"] == tabla["silhouette"].max()


def test_entrenar_kmeans_final_agrupa_los_3_pares_correctamente():
    features = _features_sinteticas()
    modelo = entrenar_kmeans_final(features, k=3)
    etiquetas = dict(zip(features.index, modelo.predict(features.values)))

    assert etiquetas["Z1"] == etiquetas["Z2"]
    assert etiquetas["Z3"] == etiquetas["Z4"]
    assert etiquetas["Z5"] == etiquetas["Z6"]
    assert len({etiquetas["Z1"], etiquetas["Z3"], etiquetas["Z5"]}) == 3


def test_nombrar_clusters_asigna_los_3_perfiles_esperados():
    features = _features_sinteticas()
    modelo = entrenar_kmeans_final(features, k=3)
    nombres = nombrar_clusters(features, modelo)
    etiquetas = dict(zip(features.index, modelo.predict(features.values)))

    assert nombres[etiquetas["Z1"]] == "Perfil de alto impacto generalizado"
    assert nombres[etiquetas["Z3"]] == "Perfil hurto de bienes / ingreso alto"
    assert nombres[etiquetas["Z5"]] == "Perfil de bajo incidente relativo"


def test_construir_zona_cluster_forma_y_columnas():
    features = _features_sinteticas()
    modelo = entrenar_kmeans_final(features, k=3)
    nombres = nombrar_clusters(features, modelo)
    zona_cluster = construir_zona_cluster(features, modelo, nombres)

    assert list(zona_cluster.columns) == ["cod_localidad", "cluster", "nombre_perfil"]
    assert zona_cluster.shape == (6, 3)
    fila_z1 = zona_cluster[zona_cluster["cod_localidad"] == "Z1"].iloc[0]
    assert fila_z1["nombre_perfil"] == "Perfil de alto impacto generalizado"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clustering.py -v`
Expected: `ModuleNotFoundError: No module named 'clustering'` — el módulo no existe todavía (todos los tests fallan en el import).

- [ ] **Step 3: Implementar `models/clustering/clustering.py`**

Crear `models/clustering/clustering.py`:

```python
"""
clustering.py — Issue #27

Funciones puras para el clustering K-Means de perfiles de zona. Reciben la
matriz de features (ya estandarizada por #26) como parametro; no leen
archivos, para poder testear con datos sinteticos (data/ no existe en CI).
"""
from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# Las 11 tasas de tipo de delito (excluye tasa_nuse e ipm_nbi, que tambien
# viven en la matriz de features pero no son "tipo de delito").
COLS_TIPO_DELITO = ["tasa_DS", "tasa_H", "tasa_HA", "tasa_HB", "tasa_HC", "tasa_HCE",
                     "tasa_HM", "tasa_HP", "tasa_HR", "tasa_LP", "tasa_VI"]
COLS_VIOLENTO = ["tasa_H", "tasa_DS", "tasa_VI", "tasa_LP"]
COLS_PATRIMONIAL = ["tasa_HA", "tasa_HB", "tasa_HC", "tasa_HCE", "tasa_HM", "tasa_HR", "tasa_HP"]


def evaluar_k(
    features: pd.DataFrame,
    k_range: range,
    n_init: int = 10,
    random_state: int = 42,
) -> pd.DataFrame:
    """Inercia y silhouette de K-Means para cada k en k_range (Issue #27).

    No decide el k final por si sola: es el insumo para graficar la curva de
    codo + silhouette y justificar la eleccion de k (ver
    docs/data-dictionaries/clustering_perfiles.md). Maximizar silhouette a
    ciegas puede dar un k poco util (ver la nota en ese documento sobre por
    que k=3 se justifica por codo + interpretabilidad, no por silhouette
    maximo).
    """
    filas = []
    for k in k_range:
        modelo = KMeans(n_clusters=k, n_init=n_init, random_state=random_state)
        etiquetas = modelo.fit_predict(features.values)
        filas.append({
            "k": k,
            "inercia": modelo.inertia_,
            "silhouette": silhouette_score(features.values, etiquetas),
        })
    return pd.DataFrame(filas)


def entrenar_kmeans_final(
    features: pd.DataFrame,
    k: int,
    n_init: int = 10,
    random_state: int = 42,
) -> KMeans:
    """Entrena el K-Means final con los parametros ya decididos (Issue #27)."""
    modelo = KMeans(n_clusters=k, n_init=n_init, random_state=random_state)
    modelo.fit(features.values)
    return modelo


def nombrar_clusters(features: pd.DataFrame, modelo: KMeans) -> dict[int, str]:
    """Nombra cada cluster por regla sobre sus centroides reales (Issue #27).

    No asume que una etiqueta numerica de sklearn siempre corresponde al mismo
    grupo entre corridas o versiones: la regla mira los centroides del modelo
    ya entrenado, cluster por cluster.

    1. El cluster cuyo promedio de las 11 tasas de tipo de delito
       (COLS_TIPO_DELITO) sea el MAXIMO entre todos los clusters, y ademas
       supere 1.0 (claramente por encima del promedio) -> "Perfil de alto
       impacto generalizado".
    2. Si no aplica lo anterior y (promedio patrimonial - promedio violento)
       > 0.3 -> "Perfil hurto de bienes / ingreso alto".
    3. En cualquier otro caso -> "Perfil de bajo incidente relativo".
    """
    centroides = pd.DataFrame(modelo.cluster_centers_, columns=features.columns)
    intensidad_general = centroides[COLS_TIPO_DELITO].mean(axis=1)
    intensidad_violento = centroides[COLS_VIOLENTO].mean(axis=1)
    intensidad_patrimonial = centroides[COLS_PATRIMONIAL].mean(axis=1)

    idx_alto_impacto = intensidad_general.idxmax()

    nombres = {}
    for i in centroides.index:
        if i == idx_alto_impacto and intensidad_general[i] > 1.0:
            nombres[i] = "Perfil de alto impacto generalizado"
        elif (intensidad_patrimonial[i] - intensidad_violento[i]) > 0.3:
            nombres[i] = "Perfil hurto de bienes / ingreso alto"
        else:
            nombres[i] = "Perfil de bajo incidente relativo"
    return nombres


def construir_zona_cluster(
    features: pd.DataFrame,
    modelo: KMeans,
    nombres: dict[int, str],
) -> pd.DataFrame:
    """Tabla zona-cluster-nombre_perfil (Issue #27), lista para servir/dashboard."""
    etiquetas = modelo.predict(features.values)
    return pd.DataFrame({
        "cod_localidad": features.index,
        "cluster": etiquetas,
        "nombre_perfil": [nombres[c] for c in etiquetas],
    })
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clustering.py -v`
Expected: `4 passed` (`test_evaluar_k_detecta_la_separacion_clara_en_k3`,
`test_entrenar_kmeans_final_agrupa_los_3_pares_correctamente`,
`test_nombrar_clusters_asigna_los_3_perfiles_esperados`,
`test_construir_zona_cluster_forma_y_columnas`).

- [ ] **Step 5: Commit**

```bash
git add models/clustering/clustering.py tests/test_clustering.py
git commit -m "feat(clustering): agrega funciones de K-Means + nombrado de perfiles + tests (issue #27)"
```

---

### Task 3: Script orquestador `models/clustering/train.py`

**Files:**
- Create: `models/clustering/train.py`

**Interfaces:**
- Consumes: `clustering.evaluar_k`, `clustering.entrenar_kmeans_final`, `clustering.nombrar_clusters`, `clustering.construir_zona_cluster` (Tarea 2); `models/clustering/features_zona.parquet` (de #26); `config.DATASET_ANALITICO` (para agregar `localidad_nombre` legible).
- Produces: `models/clustering/clusters.joblib`, `models/clustering/zona_cluster.parquet`, `reports/figures/clustering_elbow_silhouette.png` (gitignored los dos primeros — regla global `*.parquet`/`*.joblib`; la figura SÍ se versiona, `reports/` no está en `.gitignore`).

- [ ] **Step 1: Crear el script**

Crear `models/clustering/train.py`:

```python
"""
train.py — Issue #27

Orquestador: entrena el K-Means final sobre models/clustering/features_zona.parquet
(#26), justifica k con la curva de codo + silhouette, nombra cada cluster por
sus centroides reales, y serializa los dos entregables que consumen la API y
el dashboard (Integrante 2/3) y la app movil (Integrante 4, #37).

Uso:
    python models/clustering/train.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
import clustering
import config

# Parametros fijos y reproducibles (Issue #27). k=3 se justifica por el codo
# real de la inercia + interpretabilidad de los 3 perfiles resultantes, NO por
# silhouette maximo (silhouette es mayor en k=2, pero da un corte binario poco
# util). Ver docs/data-dictionaries/clustering_perfiles.md para el detalle.
K_FINAL = 3
N_INIT = 10
RANDOM_STATE = 42
RANGO_K_EXPLORADO = range(2, 8)

OUT_DIR = Path(__file__).resolve().parent
CLUSTERS_JOBLIB = OUT_DIR / "clusters.joblib"
ZONA_CLUSTER_PATH = OUT_DIR / "zona_cluster.parquet"
FIGURA_PATH = Path(__file__).resolve().parent.parent.parent / "reports" / "figures" / "clustering_elbow_silhouette.png"


def run() -> None:
    print("== #27 Entrenar K-Means + tipologia + clusters.joblib ==")
    features = pd.read_parquet(Path(__file__).resolve().parent / "features_zona.parquet")

    tabla_k = clustering.evaluar_k(features, RANGO_K_EXPLORADO, N_INIT, RANDOM_STATE)
    _graficar_codo_silhouette(tabla_k)

    modelo = clustering.entrenar_kmeans_final(features, K_FINAL, N_INIT, RANDOM_STATE)
    nombres = clustering.nombrar_clusters(features, modelo)
    zona_cluster = clustering.construir_zona_cluster(features, modelo, nombres)

    df = pd.read_parquet(config.DATASET_ANALITICO)
    nombres_loc = df.drop_duplicates("cod_localidad")[["cod_localidad", "localidad_nombre"]]
    zona_cluster = zona_cluster.merge(nombres_loc, on="cod_localidad", how="left")
    zona_cluster = zona_cluster[["cod_localidad", "localidad_nombre", "cluster", "nombre_perfil"]]

    joblib.dump({
        "modelo": modelo,
        "k": K_FINAL,
        "n_init": N_INIT,
        "random_state": RANDOM_STATE,
        "columnas_features": list(features.columns),
        "nombre_perfil": nombres,
    }, CLUSTERS_JOBLIB)
    zona_cluster.to_parquet(ZONA_CLUSTER_PATH, index=False)

    _verificar(tabla_k, zona_cluster)


def _graficar_codo_silhouette(tabla_k: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].plot(tabla_k["k"], tabla_k["inercia"], marker="o")
    axes[0].axvline(K_FINAL, color="red", ls="--", label=f"k={K_FINAL} elegido")
    axes[0].set_title("Curva de codo (inercia)")
    axes[0].set_xlabel("k")
    axes[0].legend()
    axes[1].plot(tabla_k["k"], tabla_k["silhouette"], marker="o", color="orange")
    axes[1].axvline(K_FINAL, color="red", ls="--")
    axes[1].set_title("Silhouette score")
    axes[1].set_xlabel("k")
    plt.tight_layout()
    FIGURA_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURA_PATH, dpi=110)
    plt.close(fig)


def _verificar(tabla_k: pd.DataFrame, zona_cluster: pd.DataFrame) -> None:
    print("\n-- Curva de codo + silhouette (k=2..7) --")
    print(tabla_k.round(3).to_string(index=False))
    print(f"\n  k elegido: {K_FINAL} (n_init={N_INIT}, random_state={RANDOM_STATE})")

    assert zona_cluster.shape[0] == 20, "deben quedar exactamente 20 localidades asignadas"
    print(f"\n  zona_cluster: {zona_cluster.shape[0]} localidades")
    print(zona_cluster["nombre_perfil"].value_counts().to_string())
    print(f"\n  Sumapaz (cod 20): {zona_cluster.loc[zona_cluster.cod_localidad=='20', 'nombre_perfil'].values[0]}")

    print(f"\n  [ok] {CLUSTERS_JOBLIB}")
    print(f"  [ok] {ZONA_CLUSTER_PATH}")
    print(f"  [ok] {FIGURA_PATH}")


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Correr el script contra el dataset real y verificar**

Run: `.venv/Scripts/python.exe models/clustering/train.py`
Expected (entre otras líneas):
```
-- Curva de codo + silhouette (k=2..7) --
 k  inercia  silhouette
 2  145.225       0.492
 3   89.341       0.389
 4   72.467       0.381
 5   57.625       0.380
 6   42.827       0.373
 7   30.092       0.287

  k elegido: 3 (n_init=10, random_state=42)

  zona_cluster: 20 localidades
nombre_perfil
Perfil de bajo incidente relativo        12
Perfil hurto de bienes / ingreso alto     6
Perfil de alto impacto generalizado       2

  Sumapaz (cod 20): Perfil de bajo incidente relativo

  [ok] ...\models\clustering\clusters.joblib
  [ok] ...\models\clustering\zona_cluster.parquet
  [ok] ...\reports\figures\clustering_elbow_silhouette.png
```

- [ ] **Step 3: Verificar que `clusters.joblib` y `zona_cluster.parquet` quedan fuera de git, y que la figura SÍ queda dentro**

Run: `git status --short --ignored=matching models/clustering/ reports/figures/`
Expected: `!!` (ignorado) para `models/clustering/clusters.joblib` y `models/clustering/zona_cluster.parquet`; `??` (nuevo, sin trackear — se commitea en el Step 4) para `reports/figures/clustering_elbow_silhouette.png`, ya que `reports/` no está en `.gitignore`.

- [ ] **Step 4: Commit**

```bash
git add models/clustering/train.py reports/figures/clustering_elbow_silhouette.png
git commit -m "feat(clustering): agrega script orquestador train.py + figura de codo/silhouette (issue #27)"
```

---

### Task 4: Diccionario de datos / documento de perfiles

**Files:**
- Create: `docs/data-dictionaries/clustering_perfiles.md`
- Modify: `docs/data_dictionary.md`

**Interfaces:**
- Consumes: los artefactos producidos por la Tarea 3 (números ya verificados en este plan).
- Produces: nada consumido por código; es el entregable del criterio de aceptación 3 ("tabla de perfiles... + lectura accionable").

- [ ] **Step 1: Crear el documento**

Crear `docs/data-dictionaries/clustering_perfiles.md`:

```markdown
# Tipología de perfiles de zona — K-Means (Issue #27)

**Responsable:** Integrante 3 (Clustering) · **Estado:** entrenado, insumo directo
de la API (`GET /zonas-riesgo`) y el dashboard · **Fecha:** 2026-07-09

Este documento justifica el `k` elegido para el K-Means de perfiles de zona y
documenta la tipología resultante. Generado por
`python models/clustering/train.py` a partir de
`models/clustering/features_zona.parquet` (#26). Los artefactos serializados
(`clusters.joblib`, `zona_cluster.parquet`) no se versionan en git (regla
global `*.parquet`/`*.joblib` de `.gitignore`) — se regeneran corriendo el
script. La figura de codo + silhouette sí se versiona en
`reports/figures/clustering_elbow_silhouette.png`.

---

## 1. Curva de codo + silhouette

![Codo y silhouette](../../reports/figures/clustering_elbow_silhouette.png)

| k | inercia | silhouette | tamaños de cluster |
|---|---|---|---|
| 2 | 145.23 | **0.492** | 17, 3 |
| 3 | 89.34  | 0.389 | 12, 6, 2 |
| 4 | 72.47  | 0.381 | 12, 4, 2, 2 |
| 5 | 57.63  | 0.380 | 12, 3, 2, 2, 1 |
| 6 | 42.83  | 0.373 | 12, 3, 2, 1, 1, 1 |
| 7 | 30.09  | 0.287 | 7, 5, 3, 2, 1, 1, 1 |

## 2. Por qué k=3 (y no el silhouette máximo, k=2)

El silhouette más alto es k=2 (0.492), pero produce un corte binario (17 vs 3
localidades) que no distingue más que "alto impacto vs. resto" — poco útil
como *tipología* con varios perfiles nombrables.

El **codo real de la curva de inercia está en k=3**: la caída entre k=2→3 es
de 55.9 puntos, y a partir de ahí la curva se aplana (16.9, 14.8, 14.8, 12.7
puntos por paso siguiente) — la segunda derivada cae de forma abrupta
(−39.0) justo en k=3 y se mantiene casi plana después (−2.0, −0.04, −2.1).

Además, **k=3 produce 3 perfiles genuinamente distintos e interpretables**
al mirar los centroides (Sección 3) — a diferencia de k=4/5/6, donde los
clusters adicionales son fragmentos de 1-2 localidades sin una lectura clara
propia. Se justifica **k=3 por codo + interpretabilidad**, documentando
honestamente que el silhouette de k=2 es mayor.

**Parámetros reproducibles:** `k=3, n_init=10, random_state=42`, rango
explorado `k=2..7`. Guardados dentro de `clusters.joblib`.

## 3. Tabla de perfiles

| Cluster | n zonas | Nombre | Localidades |
|---|---|---|---|
| Alto impacto | 2 | **Perfil de alto impacto generalizado** | Candelaria, Los Mártires |
| Hurto de bienes | 6 | **Perfil hurto de bienes / ingreso alto** | Antonio Nariño, Barrios Unidos, Chapinero, Puente Aranda, Santa Fe, Teusaquillo |
| Bajo incidente | 12 | **Perfil de bajo incidente relativo** | Bosa, Ciudad Bolívar, Engativá, Fontibón, Kennedy, Rafael Uribe Uribe, San Cristóbal, Suba, **Sumapaz**, Tunjuelito, Usaquén, Usme |

### Regla de nombrado (por centroides, no por índice)

1. El cluster con mayor intensidad promedio en las 11 tasas de tipo de delito
   (y > 1.0, claramente sobre el promedio) → "Perfil de alto impacto
   generalizado".
2. Si no aplica lo anterior y (promedio patrimonial − promedio violento) >
   0.3 → "Perfil hurto de bienes / ingreso alto".
3. En cualquier otro caso → "Perfil de bajo incidente relativo".

Implementación en `models/clustering/clustering.py::nombrar_clusters`.

## 4. Lectura accionable por perfil

**Perfil de alto impacto generalizado (Candelaria, Los Mártires).** Estas dos
localidades del centro histórico y comercial de Bogotá concentran tasas por
100k habitantes muy por encima del resto en **todos** los tipos de delito
medidos, sin excepción, además de un volumen de llamadas al 123 igualmente
alto. No es un perfil de un solo tipo de delito: es alta incidencia
generalizada, consistente con ser zonas de altísima afluencia diurna/nocturna
y baja población residente (denominador pequeño inflando las tasas por 100k).
Lectura para planeación: son las dos únicas zonas que requieren atención
transversal a casi todos los tipos de delito a la vez, no una intervención
focalizada en un solo tipo.

**Perfil hurto de bienes / ingreso alto (Antonio Nariño, Barrios Unidos,
Chapinero, Puente Aranda, Santa Fe, Teusaquillo).** Estas seis localidades
tienen tasas elevadas específicamente en delitos patrimoniales (hurto de
autos, bicicletas, comercio, celulares, residencias) pero **no** en violencia
interpersonal (homicidios, violencia intrafamiliar, lesiones), y un `ipm_nbi`
consistentemente bajo (zonas de mayor ingreso relativo). Lectura para
planeación: el foco aquí es prevención situacional del hurto de bienes
(vigilancia comercial, seguridad vehicular/residencial), no un problema de
violencia social — mezclar ambos en una sola estrategia sería impreciso.

**Perfil de bajo incidente relativo (Bosa, Ciudad Bolívar, Engativá,
Fontibón, Kennedy, Rafael Uribe Uribe, San Cristóbal, Suba, Sumapaz,
Tunjuelito, Usaquén, Usme).** El grupo más numeroso (12 de 20 localidades):
tasas por debajo del promedio en casi todos los tipos de delito. Incluye
localidades de perfil socioeconómico muy distinto entre sí (desde Usaquén
hasta Ciudad Bolívar y la rural Sumapaz) — el clustering las agrupa por tener
tasas *relativamente* bajas frente al resto de la ciudad, no porque sean
homogéneas en otros aspectos. **Nota sobre Sumapaz:** a diferencia del
clustering jerárquico exploratorio de #25 (donde Sumapaz quedaba aislada en
su propio grupo en todos los k probados), en este K-Means real cae dentro de
este cluster grande — es un resultado distinto pero legítimo (algoritmo y
espacio de features distintos); no se fuerza a un resultado distinto.

## 5. Reproducibilidad

`clusters.joblib` guarda un diccionario con `modelo` (el `KMeans` entrenado),
`k`, `n_init`, `random_state`, `columnas_features` (orden exacto de columnas
de `features_zona.parquet` usado para entrenar) y `nombre_perfil` (mapeo
`cluster -> nombre`). Cualquier nuevo cálculo de cluster para una zona debe
usar exactamente esas mismas columnas en el mismo orden.
```

- [ ] **Step 2: Agregar la entrada al índice `docs/data_dictionary.md`**

Editar la tabla "Diccionarios por fuente de origen" en `docs/data_dictionary.md`:

Antes:
```
| Features de zona + línea base z-score (#26) | [`data-dictionaries/features_clustering.md`](data-dictionaries/features_clustering.md) |
| Reporte de calidad (Issue #7) | [`data-dictionaries/reporte_calidad.md`](data-dictionaries/reporte_calidad.md) |
```

Después:
```
| Features de zona + línea base z-score (#26) | [`data-dictionaries/features_clustering.md`](data-dictionaries/features_clustering.md) |
| Tipología de perfiles de zona — K-Means (#27) | [`data-dictionaries/clustering_perfiles.md`](data-dictionaries/clustering_perfiles.md) |
| Reporte de calidad (Issue #7) | [`data-dictionaries/reporte_calidad.md`](data-dictionaries/reporte_calidad.md) |
```

- [ ] **Step 3: Commit**

```bash
git add docs/data-dictionaries/clustering_perfiles.md docs/data_dictionary.md
git commit -m "docs(clustering): agrega diccionario de tipologia K-Means (issue #27)"
```

---

### Task 5: Marcar la Issue #27 como completa en `BACKLOG.md`

**Files:**
- Modify: `BACKLOG.md`

**Interfaces:**
- Consumes: el estado de las Tareas 1-4 (todas completas y revisadas).
- Produces: nada consumido por código.

- [ ] **Step 1: Marcar los 4 checkboxes**

En `BACKLOG.md`, dentro del bloque `### [CLUST] #27 — Entrenar K-Means + tipología + clusters.joblib 🎯`:

Antes:
```
- [ ] Curva de codo + silhouette para un rango de k; k final justificado.
- [ ] Cada zona asignada a un cluster; parámetros (k, n_init, random_state) reproducibles.
- [ ] Tabla de perfiles por cluster con **nombre interpretable** ("perfil hurto-alto", "perfil violencia-intrafamiliar", etc.) + lectura accionable (1 párrafo por perfil).
- [ ] `models/clustering/clusters.joblib` + `models/clustering/zona_cluster.parquet` (zona, cluster, nombre_perfil) para la API y el dashboard.
```

Después:
```
- [x] Curva de codo + silhouette para un rango de k; k final justificado.
- [x] Cada zona asignada a un cluster; parámetros (k, n_init, random_state) reproducibles.
- [x] Tabla de perfiles por cluster con **nombre interpretable** ("perfil hurto-alto", "perfil violencia-intrafamiliar", etc.) + lectura accionable (1 párrafo por perfil).
- [x] `models/clustering/clusters.joblib` + `models/clustering/zona_cluster.parquet` (zona, cluster, nombre_perfil) para la API y el dashboard.
```

- [ ] **Step 2: Verificación final — correr toda la suite de tests**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: `8 passed` (4 de `test_feature_engineering.py` + 4 de `test_clustering.py`).

- [ ] **Step 3: Commit**

```bash
git add BACKLOG.md
git commit -m "docs(backlog): marca issue #27 (K-Means + tipologia + clusters.joblib) como completa"
```

---

## Notas para quien retome este trabajo (Issue #28 y #37)

- `models/clustering/clusters.joblib` trae `columnas_features` guardado
  explícitamente — cualquier reentrenamiento o predicción nueva debe usar
  exactamente esas columnas en ese orden.
- #28 (validación interna) puede partir directo de la tabla de codo+silhouette
  ya calculada (`docs/data-dictionaries/clustering_perfiles.md`, Sección 1) en
  vez de recalcularla.
- El resultado real de Sumapaz (cae en el cluster grande, no aislada) es
  distinto al del EDA jerárquico de #25 — está documentado en la Sección 4;
  si #28/#31 (auditoría de sesgo) quieren revisar ese cambio de resultado,
  ambos análisis (jerárquico vs. K-Means) están documentados por separado.
