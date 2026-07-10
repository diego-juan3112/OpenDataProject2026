# Diseño — Features de perfil de zona + línea base z-score (Issue [CLUST] #26)

**Fecha:** 2026-07-09 · **Pista:** 3 — Clustering + Dashboard (Integrante 3) · **Fase CRISP-ML:** 3

## Contexto

Issue #26 depende de #9 (dataset analítico, ya completo) y bloquea a #27 (entrenar
K-Means) y #36 (flag z-score del reporte ciudadano). Tiene dos entregables
independientes que comparten la misma fuente (`dataset_analitico.parquet`) y la
misma restricción de no-fuga:

1. Una **matriz de features por localidad, estandarizada**, lista para alimentar
   K-Means en #27.
2. Una **línea base histórica (media + desviación) por localidad–tipo de delito**,
   que #36 usará para calcular el z-score de un reporte ciudadano nuevo.

**Criterios de aceptación (del backlog):**
1. Matriz localidad × features estandarizada y documentada.
2. Línea base (media + desviación) por localidad–tipo de delito, calculada con los
   conteos anuales del histórico, y guardada.
3. Sin fuga: la línea base solo usa histórico, no el reporte que se evaluará.

## Restricción de CI descubierta durante el diseño

`data/` está en `.gitignore` y el pipeline de ingesta (descarga SIEDCO/NUSE/DANE)
no corre en `.github/workflows/ci.yml` — el CI no tiene acceso a
`dataset_analitico.parquet`. Por eso las funciones nuevas deben recibir un
`DataFrame` como parámetro (igual que `add_target_riesgo_alto(df)` ya existente),
nunca leer un archivo directamente — así los tests corren con un DataFrame
sintético pequeño, sin depender de datos reales ni de red.

## Dónde vive el código

- **`src/feature_engineering.py`** (ya existe, con placeholder explícito para
  esto): se agregan dos funciones nuevas, `construir_features_zona(df)` y
  `calcular_linea_base(df)`. Funciones puras, reciben DataFrame y devuelven
  DataFrame — mismo patrón que `add_target_riesgo_alto`.
- **`models/clustering/build_features.py`** (nuevo, primer archivo de
  `models/clustering/`): orquestador. Carga `data/03_primary/dataset_analitico.parquet`,
  llama a las dos funciones, escribe los dos parquet de salida y imprime un
  resumen de verificación (estilo `pipelines/pipeline_ml.py`). Estos parquet
  quedan gitignored (regla `*.parquet` global) — se regeneran corriendo el script,
  igual que `dataset_analitico.parquet`.
- **`docs/data-dictionaries/features_clustering.md`** (nuevo): documenta ambos
  artefactos siguiendo el estilo de `docs/data-dictionaries/variable_objetivo.md`
  (definición, por qué esas features, decisión de Sumapaz, sensibilidad, qué
  queda abierto para #27/#36).
- **`tests/test_feature_engineering.py`** (nuevo): primeros tests reales del
  repositorio. Arreglan además que `pytest tests/ -v` en CI deje de fallar por
  "no tests collected".

## `construir_features_zona(df)`

Entrada: el DataFrame de `dataset_analitico.parquet` (columnas
`cod_localidad, localidad_nombre, anio, tipo_delito, tipo_delito_nombre,
conteo_siedco, conteo_nuse, poblacion, ipm_nbi, split, riesgo_alto`). Filtra
`split == "train"` como primer paso (sin fuga: 2025 nunca entra).

Construye una matriz de **20 localidades × 13 columnas**, todas estandarizadas
(z-score, media 0 / desviación 1 por columna) al final:

- **11 columnas `tasa_<tipo_delito>`**: tasa anual promedio por 100.000
  habitantes. Para cada localidad y tipo, se calcula
  `conteo_siedco / poblacion * 100000` por año (2018–2024) y se promedia sobre
  los 7 años — así se pondera correctamente la población de cada año, en vez de
  usar solo la población de un año fijo.
- **1 columna `tasa_nuse`**: mismo cálculo con `conteo_nuse`, deduplicando antes
  el valor (que en el dataset viene repetido idéntico en las 11 filas de tipo
  de una misma localidad-año — es una señal de zona-año, no de zona-tipo).
- **1 columna `ipm_nbi`**: valor estático por localidad (ya es el mismo en todas
  las filas de esa localidad). **Sumapaz (única localidad con `ipm_nbi` nulo,
  sin Encuesta Multipropósito) se imputa con la mediana de las otras 19** —
  imputación documentada explícitamente, no en silencio. La decisión de cómo
  tratar a Sumapaz en el clustering final (incluir con este valor imputado,
  excluirlo, o dejarlo como cluster propio) se deja abierta y documentada para
  #27 — esta issue solo evita que un `NaN` rompa el z-score de toda la matriz.

La función devuelve el DataFrame ya estandarizado, indexado por `cod_localidad`
(o con esa columna incluida), listo para pasarse directo a `KMeans.fit(...)` en
#27 sin transformación adicional.

## `calcular_linea_base(df)`

Misma entrada, mismo filtro `split == "train"` como primer paso. Agrupa por
`(cod_localidad, tipo_delito)` (220 combinaciones = 20 × 11) y calcula, sobre
los 7 conteos anuales (`conteo_siedco`, 2018–2024) de cada grupo:

- `media`: promedio de los 7 conteos anuales.
- `desviacion`: desviación estándar muestral (`ddof=1`) de los 7 conteos.

Devuelve un DataFrame de 220 filas (`cod_localidad, tipo_delito, media,
desviacion`). Este es el insumo directo de `flag_zscore` (#36): dado un conteo
reciente para `(localidad, tipo)`, #36 calculará
`z = (conteo_reciente - media) / desviacion`. Esta issue **no** implementa
`flag_zscore` — solo produce y guarda la línea base que esa función consumirá.

**Caso de desviación cero:** si una combinación localidad-tipo tiene los 7
conteos anuales idénticos (posible en Sumapaz, con conteos casi nulos en varios
tipos), `desviacion` puede salir en `0.0`. La función no falla en ese caso (no
divide por nada); se documenta la existencia de esas filas en el diccionario de
datos para que #36 decida cómo evitar una división por cero al calcular el
z-score.

## `models/clustering/build_features.py`

Script orquestador, primer archivo de `models/clustering/`:

1. Carga `data/03_primary/dataset_analitico.parquet`.
2. Llama a `construir_features_zona(df)` → escribe
   `models/clustering/features_zona.parquet`.
3. Llama a `calcular_linea_base(df)` → escribe
   `models/clustering/linea_base_zscore.parquet`.
4. Imprime un resumen de verificación: forma de cada salida, confirmación de
   que se usó solo `split == "train"`, confirmación de la imputación de Sumapaz,
   conteo de filas con `desviacion == 0`.

Ambos `.parquet` quedan fuera de git (regla global `*.parquet` en
`.gitignore`) — se regeneran corriendo `python models/clustering/build_features.py`,
igual que `dataset_analitico.parquet` se regenera con
`python pipelines/pipeline_ml.py`.

## `docs/data-dictionaries/features_clustering.md`

Documento de decisión, estilo `variable_objetivo.md`:
- Definición de cada columna de la matriz de features y de la línea base.
- Por qué tasas por 100k (no conteos crudos): comparabilidad entre localidades
  de población muy distinta (mismo razonamiento que ya usa el EDA de #25 para
  evitar comparar volúmenes crudos).
- Decisión de imputación de Sumapaz (mediana) y qué queda abierto para #27.
- Nota sobre las filas con `desviacion == 0` en la línea base, para #36.

## Tests (`tests/test_feature_engineering.py`)

Usan un DataFrame sintético construido en el propio test (pocas localidades,
2-3 tipos de delito, 7 años train + 1 año test) — nunca leen el parquet real.

1. **`test_features_zona_estandarizada_media_cero`**: sobre el DataFrame
   sintético, `construir_features_zona` devuelve columnas con media ≈ 0 y
   desviación ≈ 1.
2. **`test_linea_base_media_std_correctos`**: sobre un caso conocido (valores
   fijos a mano para una localidad-tipo), `calcular_linea_base` devuelve
   exactamente la media y desviación esperadas.
3. **`test_sin_fuga_solo_usa_train`**: se agrega una fila `split == "test"` con
   un valor atípico (p. ej. un conteo absurdamente alto) al DataFrame sintético
   y se verifica que ni la matriz de features ni la línea base cambian frente
   al mismo DataFrame sin esa fila — confirma que el filtro de split realmente
   excluye test.

## Fuera de alcance

`flag_zscore` (función que compara un reporte nuevo contra la línea base) es
#36, no esta issue. La elección final de `k`, el entrenamiento de K-Means y
`clusters.joblib` son #27. La decisión final de tratamiento de Sumapaz en el
clustering (incluir/excluir/cluster propio) se documenta como abierta, no se
cierra aquí.
