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
