# Diseño — Validación interna del clustering (Issue [CLUST] #28)

**Fecha:** 2026-07-11 · **Pista:** 3 — Clustering + Dashboard (Integrante 3) · **Fase CRISP-ML:** 3

## Contexto

Issue #28 depende de #27 (K-Means final, `k=3`, `clusters.joblib` +
`zona_cluster.parquet`, completo) y bloquea a #39 (QA cruzada / informe).
Objetivo: demostrar que la segmentación de #27 es **estable y no arbitraria**,
no solo reportar la curva de codo + silhouette global ya hecha en #27.

**Criterios de aceptación (del backlog):**
1. Silhouette global y por cluster reportado.
2. Prueba de estabilidad (varias semillas / submuestreo) documentada.
3. Argumento de por qué la tipología aporta más que ordenar zonas por conteo.

## Hallazgos reales durante el diseño (verificados corriendo las 3 validaciones)

Antes de fijar el diseño se corrieron las 3 validaciones contra el modelo real
de #27 (`clusters.joblib`, `features_zona.parquet`, `k=3, n_init=10,
random_state=42`):

### 1. Silhouette por cluster

| Cluster | n | Nombre | silhouette medio | silhouette mín |
|---|---|---|---|---|
| 0 | 12 | Perfil de bajo incidente relativo | **0.498** | 0.387 |
| 1 | 2  | Perfil de alto impacto generalizado | 0.249 | 0.247 |
| 2 | 6  | Perfil hurto de bienes / ingreso alto | 0.219 | 0.037 |

El cluster grande (bajo incidente) es el más cohesivo. Los otros dos son más
débiles — esperable con clusters pequeños (2 y 6 zonas) y features de alta
dimensión (13 columnas); una zona del cluster "hurto de bienes" tiene
silhouette casi cero (0.037, límite de mal clasificada). Se documenta tal
cual, sin suavizar el resultado.

### 2. Estabilidad ante semillas

10 semillas (`0..9`) reentrenadas contra el modelo de referencia
(`random_state=42`), comparadas con **Adjusted Rand Index** (ARI: 1.0 =
partición idéntica, 0.0 = tan parecida como al azar):

| semilla | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| ARI | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

**ARI = 1.0 en las 10 semillas**: la partición es completamente estable, no
depende de la semilla — resultado fuerte a favor de que la segmentación no es
arbitraria.

### 3. Comparación contra ordenar zonas por conteo total

Terciles (`k=3`, `pd.qcut`) del conteo total de `conteo_siedco` (solo train,
sin fuga) vs. las etiquetas reales de K-Means:

**ARI (K-Means real vs. terciles por conteo total) = 0.031** — prácticamente
sin relación, muy por debajo del 1.0 de la prueba de estabilidad. El conteo
total ordena las zonas en una sola dimensión (volumen); el crosstab lo
confirma:

| perfil K-Means \ tercil conteo | bajo (0) | medio (1) | alto (2) |
|---|---|---|---|
| Alto impacto generalizado | 1 | 1 | 0 |
| Bajo incidente relativo | 4 | 2 | 6 |
| Hurto de bienes / ingreso alto | 2 | 3 | 1 |

Ejemplo concreto: **Candelaria** (perfil "alto impacto") cae en el tercil
**bajo** de conteo total — es una localidad pequeña en habitantes con tasas
por 100k muy altas, pero pocos incidentes absolutos; ordenar solo por conteo
la escondería junto a zonas de bajo riesgo real. Este es el argumento central:
la tipología usa 13 features (11 tasas de delito + NUSE + `ipm_nbi`) y
normaliza por población, mientras que el conteo total es una sola cifra cruda
que mezcla volumen con tamaño poblacional.

## Dónde vive el código

- **`src/feature_engineering.py`** (edita): nueva función
  `conteo_total_por_zona(df, split_col="split", train_value="train") ->
  pd.Series` — agrega `conteo_siedco` por `cod_localidad`, solo `train` (mismo
  patrón sin fuga que `construir_features_zona` / `calcular_linea_base`, ya
  existentes en este módulo). Indexada por `cod_localidad`, mismo índice que
  `features_zona.parquet`.
- **`models/clustering/clustering.py`** (edita, funciones puras, sin I/O,
  testeables con sintéticos — mismo patrón que el resto del módulo):
  - `silhouette_por_cluster(features, modelo) -> pd.DataFrame` (columnas
    `cluster, n, silhouette_medio, silhouette_min`), vía
    `sklearn.metrics.silhouette_samples`.
  - `comparar_particiones(etiquetas_a, etiquetas_b) -> float` — wrapper sobre
    `adjusted_rand_score`; genérico, reutilizado tanto para estabilidad de
    semillas como para la comparación con terciles.
  - `evaluar_estabilidad_semillas(features, etiquetas_referencia, k, semillas,
    n_init=10) -> pd.DataFrame` (columnas `semilla, ari`) — reentrena K-Means
    por cada semilla y compara contra `etiquetas_referencia` con
    `comparar_particiones`.
  - `terciles_por_conteo(conteo_total, k) -> pd.Series` — `pd.qcut(conteo_total,
    q=k, labels=False, duplicates="drop")`, mismo índice que la entrada.
- **`models/clustering/validate.py`** (nuevo, orquestador — mismo patrón que
  `train.py`/`build_features.py`): carga `clusters.joblib`,
  `features_zona.parquet` y `data/03_primary/dataset_analitico.parquet`;
  corre las 3 validaciones con los parámetros fijos de abajo; imprime el
  resumen a consola (igual que `train.py`) y expone los DataFrames/valores
  para que el doc se complete a mano con los resultados (no genera el `.md`
  automáticamente — sigue el patrón de `train.py`, cuyo `clustering_perfiles.md`
  se escribió a partir de la salida de consola, no generado por el script).
- **`tests/test_validacion_clustering.py`** (nuevo, datos sintéticos, sin leer
  disco — mismo patrón que `test_clustering.py`):
  - `silhouette_por_cluster`: matriz sintética con 2 grupos muy separados y
    verifica silhouette alto para ambos.
  - `comparar_particiones`: dos etiquetas idénticas → ARI 1.0; etiquetas con
    las mismas particiones pero números de cluster permutados → ARI 1.0
    (invariante a la etiqueta); etiquetas aleatorias sin relación → ARI bajo.
  - `evaluar_estabilidad_semillas`: datos sintéticos muy separables → ARI 1.0
    para todas las semillas.
  - `terciles_por_conteo`: serie sintética de 6 valores → 3 terciles de 2
    elementos cada uno, con los valores correctos en cada grupo.
- **`docs/data-dictionaries/validacion_clustering.md`** (nuevo): las 3 tablas
  de arriba (ya verificadas) + 1 párrafo de interpretación por cada una
  (cohesión por cluster, estabilidad perfecta, argumento tipología > conteo
  con el ejemplo de Candelaria) — mismo estilo que `clustering_perfiles.md`.

## Parámetros fijos (reproducibilidad)

Semilla de referencia `random_state=42` (la del modelo final de #27),
`semillas_estabilidad = range(0, 10)`, `n_init=10` (igual que el
entrenamiento), `k=3` (igual que el modelo final, tanto para K-Means como para
los terciles del baseline).

## Fuera de alcance

Submuestreo (leave-k-out) queda fuera: la prueba de semillas ya deja ARI=1.0
perfecto, así que una segunda prueba de estabilidad no cambiaría la
conclusión y no está en los criterios de aceptación como obligatoria (el
backlog pide "semillas **o** submuestreo"). No se genera ninguna figura nueva
— las 3 tablas son suficientes para los criterios de aceptación. No se
reentrena ni se cambia el modelo final de #27.
