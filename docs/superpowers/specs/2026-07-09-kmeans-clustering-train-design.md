# Diseño — Entrenar K-Means + tipología + `clusters.joblib` (Issue [CLUST] #27)

**Fecha:** 2026-07-09 · **Pista:** 3 — Clustering + Dashboard (Integrante 3) · **Fase CRISP-ML:** 3

## Contexto

Issue #27 depende de #26 (features de zona ya estandarizadas y línea base
z-score, completo) y bloquea a #20/#23 (QA cruzada, Integrante 2), #28
(validación interna) y #37 (app móvil). Es el modelo de clustering formal del
proyecto: agrupa las 20 localidades de Bogotá en una tipología accionable
(perfil delictivo), que alimenta el mapa coroplético del dashboard y el
contrato `GET /zonas-riesgo` de la API.

**Criterios de aceptación (del backlog):**
1. Curva de codo + silhouette para un rango de k; k final justificado.
2. Cada zona asignada a un cluster; parámetros (k, n_init, random_state)
   reproducibles.
3. Tabla de perfiles por cluster con nombre interpretable + lectura accionable
   (1 párrafo por perfil).
4. `models/clustering/clusters.joblib` + `models/clustering/zona_cluster.parquet`
   (zona, cluster, nombre_perfil) para la API y el dashboard.

## Hallazgos reales durante el diseño (verificados corriendo K-Means de verdad)

Antes de fijar el diseño se instaló `scikit-learn` y se corrió K-Means real
contra `models/clustering/features_zona.parquet` (20×13, ya estandarizado por
#26), con `n_init=10, random_state=42`, para k=2..7:

| k | inercia | silhouette | tamaños de cluster |
|---|---|---|---|
| 2 | 145.23 | **0.492** | 17, 3 |
| 3 | 89.34  | 0.389 | 12, 6, 2 |
| 4 | 72.47  | 0.381 | 12, 4, 2, 2 |
| 5 | 57.63  | 0.380 | 12, 3, 2, 2, 1 |
| 6 | 42.83  | 0.373 | 12, 3, 2, 1, 1, 1 |
| 7 | 30.09  | 0.287 | 7, 5, 3, 2, 1, 1, 1 |

**Dos hallazgos que corrigen supuestos previos:**

1. **Sumapaz NO se aísla en K-Means** (a diferencia del clustering jerárquico
   del EDA de #25, donde sí quedaba sola en todos los k probados). Aquí cae
   dentro del cluster grande de 12 localidades (junto con Rafael Uribe, San
   Cristóbal, Usme, Bosa, Ciudad Bolívar, etc. — zonas con tasas por debajo del
   promedio en casi todo). Es un resultado distinto pero legítimo: algoritmo
   (K-Means vs. Ward jerárquico) y espacio de features distintos. Se documenta
   tal cual sale, sin forzar una separación artificial.
2. **Maximizar silhouette a ciegas da k=2** (0.492), un corte binario poco útil
   como "tipología" de varios perfiles. El **codo real de la inercia está en
   k=3**: la segunda derivada de la curva de inercia cae de forma abrupta ahí
   (−39.0, contra −2.0/−0.04/−2.1 en los saltos siguientes, que son planos).
   Además, **k=3 produce 3 perfiles genuinamente distintos e interpretables**
   al mirar los centroides reales (ver tabla abajo). **Se justifica k=3 por
   codo + interpretabilidad**, documentando honestamente que el silhouette de
   k=2 es mayor pero produce un resultado menos accionable.

### Centroides reales en k=3 (z-score) y perfiles resultantes

| Cluster | n | Centroide (resumen) | Miembros | Nombre |
|---|---|---|---|---|
| A | 12 | todas las tasas por debajo del promedio | Bosa, Ciudad Bolívar, Engativá, Fontibón, Kennedy, Rafael Uribe Uribe, San Cristóbal, Suba, **Sumapaz**, Tunjuelito, Usaquén, Usme | Perfil de bajo incidente relativo |
| B | 2  | extremo en TODOS los tipos de delito + NUSE (score general z≈+1.97, el más alto) | Candelaria, Los Mártires | Perfil de alto impacto generalizado |
| C | 6  | alto en hurtos patrimoniales (autos, bicis, comercio, celulares, residencias), bajo en violencia interpersonal, `ipm_nbi` bajo (más ricas) | Antonio Nariño, Barrios Unidos, Chapinero, Puente Aranda, Santa Fe, Teusaquillo | Perfil hurto de bienes / ingreso alto |

## Dónde vive el código

- **`models/clustering/clustering.py`** (nuevo): funciones puras y testeables,
  reciben la matriz de features como parámetro (mismo patrón que
  `src/feature_engineering.py` en #26 — testeable sin datos reales):
  - `evaluar_k(features, k_range, n_init, random_state) -> pd.DataFrame`
    (columnas `k, inercia, silhouette`).
  - `entrenar_kmeans_final(features, k, n_init, random_state) -> KMeans`.
  - `nombrar_clusters(features, modelo) -> dict[int, str]` — nombra cada
    cluster **por regla sobre sus centroides reales** (no por índice
    hardcodeado, para no depender de que sklearn asigne siempre la misma
    etiqueta numérica al mismo grupo):
    1. El cluster cuyo promedio de los 11 `tasa_<tipo>` sea el máximo entre
       todos los clusters **y** supere 1.0 (claramente por encima del
       promedio) → `"Perfil de alto impacto generalizado"`.
    2. Si no aplica lo anterior y (promedio patrimonial − promedio violento)
       > 0.3 → `"Perfil hurto de bienes / ingreso alto"` (patrimonial =
       promedio de `tasa_HA, tasa_HB, tasa_HC, tasa_HCE, tasa_HM, tasa_HR,
       tasa_HP`; violento = promedio de `tasa_H, tasa_DS, tasa_VI, tasa_LP`).
    3. En cualquier otro caso → `"Perfil de bajo incidente relativo"`.
  - `construir_zona_cluster(features, modelo, nombres) -> pd.DataFrame`
    (columnas `cod_localidad, cluster, nombre_perfil`).
- **`models/clustering/train.py`** (nuevo): orquestador. Carga
  `features_zona.parquet`, llama `evaluar_k` para k=2..7, guarda la figura de
  codo+silhouette en `reports/figures/clustering_elbow_silhouette.png`,
  entrena el k final (**`K_FINAL = 3`**, constante documentada como
  `PERCENTIL_RIESGO_ALTO` en `feature_engineering.py`), guarda
  `models/clustering/clusters.joblib` (dict con el modelo, `k`, `n_init`,
  `random_state`, columnas de features y el mapeo de nombres) y
  `models/clustering/zona_cluster.parquet` (agrega `localidad_nombre` uniendo
  contra el dataset analítico, para lectura humana).
- **`tests/test_clustering.py`** (nuevo): usa una matriz de features sintética
  pequeña con grupos claramente separables (no el parquet real) para verificar
  `evaluar_k`, `entrenar_kmeans_final` y `nombrar_clusters`.
- **`docs/data-dictionaries/clustering_perfiles.md`** (nuevo): metodología
  (rango de k, n_init, random_state), la tabla de arriba ya verificada, la
  figura de codo+silhouette referenciada, y **1 párrafo de lectura accionable
  por cada uno de los 3 perfiles**.
- **`requirements.txt`**: agrega `scikit-learn` y `joblib` (dependencias
  reales del entrenamiento).

## Parámetros fijos (reproducibilidad)

`k=3` (justificado arriba), `n_init=10`, `random_state=42`, rango explorado
`k=2..7`. Todos guardados dentro de `clusters.joblib`, no solo impresos en
consola.

## Fuera de alcance

Validación interna formal más profunda (más allá de la curva de codo +
silhouette ya calculada) es #28. La decisión de si Sumapaz debería tratarse
distinto (excluirla, forzar cluster propio) sigue documentada como posible
ajuste futuro, no se fuerza aquí — se reporta el resultado real de K-Means tal
como sale.
